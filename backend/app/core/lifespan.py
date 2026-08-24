"""应用生命周期管理 (从 main.py 抽出)。

职责:
  1. 数据库种子 (默认角色/管理员/知识库/排班/演练风险巡检/外部设备) — 幂等, DB 不可用时静默跳过
  2. 启动 Kafka 消费协程 / Mock 采集器
  3. 注册告警落库处理器
  4. 启动 KPI 定时广播循环 (驾驶舱快照 → WS)
  5. 关闭时取消全部后台任务
"""
import asyncio
import json
import logging

from app.db.session import SessionLocal
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.collectors.kafka_consumer import maybe_start_consumer
from app.collectors.mock_collector import maybe_start_mock_collector
from app.crud import external as ext_crud

logger = logging.getLogger("lifespan")


# ======================================================================
#  缺失列自愈 (create_all 不修改已存在表, 老库需补齐新增列)
# ======================================================================
def _ensure_missing_columns(db):
    """对已存在的旧表, 幂等补齐批次新增的列 (避免 SELECT 时报 column missing)。

    策略: 逐列执行 ALTER TABLE ADD COLUMN, 若列已存在则忽略异常。
    兼容 PostgreSQL 与 SQLite。
    """
    from sqlalchemy import text
    from sqlalchemy.types import String, Integer, Numeric, Boolean

    # 表名 -> [(列名, 类型SQL, 默认值SQL)]
    specs: dict[str, list[tuple[str, str, str]]] = {
        "knowledge_items": [
            ("review_status", "VARCHAR(16)", "DEFAULT 'approved'"),
            ("reviewer", "VARCHAR(64)", "DEFAULT ''"),
            ("reviewed_at", "VARCHAR(32)", "DEFAULT ''"),
            ("review_note", "TEXT", "DEFAULT ''"),
        ],
    }

    # 按模型元数据自动补齐缺失列 (兼容老库缺列) 的表清单
    auto_tables = {}
    try:
        from app.models.idc import IDC
        auto_tables["idc"] = IDC
    except Exception:  # noqa: BLE001
        pass
    try:
        from app.models.external import ExternalDevice
        auto_tables["external_devices"] = ExternalDevice
    except Exception:  # noqa: BLE001
        pass

    for table_name, model in auto_tables.items():
        cols: list[tuple[str, str, str]] = []
        for col in model.__table__.columns:
            if col.name in ("id",):
                continue
            ctype = col.type
            if isinstance(ctype, String):
                sql = f"VARCHAR({getattr(ctype, 'length', 255) or 255})"
            elif isinstance(ctype, Numeric):
                sql = f"NUMERIC({getattr(ctype, 'precision', 12) or 12},{getattr(ctype, 'scale', 2) or 2})"
            elif isinstance(ctype, Integer):
                sql = "INTEGER"
            elif isinstance(ctype, Boolean):
                sql = "BOOLEAN"
            else:
                sql = "TEXT"
            if isinstance(ctype, Boolean):
                default = "DEFAULT FALSE"
            elif isinstance(ctype, (Integer, Numeric)):
                default = "DEFAULT 0"
            else:
                default = "DEFAULT ''"
            cols.append((col.name, sql, default))
        specs[table_name] = cols
    for table, cols in specs.items():
        for col, col_type, col_default in cols:
            try:
                db.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type} {col_default}")  # sql-guard-ignore
                )
                db.commit()
                logger.info("补齐列 %s.%s", table, col)
            except Exception as e:  # 列已存在 / 不支持等
                db.rollback()
                msg = str(e).lower()
                if "already exists" in msg or "42701" in msg or "duplicate column" in msg:
                    continue
                logger.warning("补齐列 %s.%s 失败(可忽略): %s", table, col, e)


# ======================================================================
#  KPI 定时广播
# ======================================================================
async def kpi_broadcast_loop():
    """每 5 秒向所有 WS 客户端推送驾驶舱 KPI 快照。"""
    from app.services import dc_aggregator as agg
    from app.services import ws_broadcaster
    from app.core.monitoring import (
        kpi_pue, kpi_wue, kpi_it_load_mw, kpi_total_load_mw,
        kpi_online_rate, ws_connections_active, alarms_active,
    )
    while True:
        try:
            overview = agg.dashboard_overview()
            telemetry = {
                "pue": overview.get("pue", 0),
                "wue": overview.get("wue", 0),
                "it_load_mw": overview.get("it_load_mw", 0),
                "total_load_mw": overview.get("total_load_mw", 0),
                "cool_load_mw": overview.get("cool_load_mw", 0),
                "online_rate": overview.get("online_rate", 0),
                "total_devices": overview.get("total_devices", 0),
                "online_devices": overview.get("online_devices", 0),
                "today_alarms": overview.get("today_alarms", 0),
                "alarms": overview.get("alarms", {}),
                "_source": overview.get("_source", ""),
            }
            await ws_broadcaster.broadcast_telemetry(telemetry)

            # 同步 KPI 到 Prometheus Gauge
            kpi_pue.set(float(overview.get("pue", 0)))
            kpi_wue.set(float(overview.get("wue", 0)))
            kpi_it_load_mw.set(float(overview.get("it_load_mw", 0)))
            kpi_total_load_mw.set(float(overview.get("total_load_mw", 0)))
            kpi_online_rate.set(float(overview.get("online_rate", 0)))
            ws_connections_active.set(len(ws_broadcaster._connections))

            # [P2-8] 活跃告警数 (按 severity 分维度) 同步到 Prometheus Gauge
            try:
                from app.services import alarm_engine as _ae

                sev_counts: dict[str, int] = {}
                for a in _ae.get_active_alarms():
                    lv = (a.get("level") or "warn").lower()
                    sev_counts[lv] = sev_counts.get(lv, 0) + 1
                for lv in ("crit", "warn", "info"):
                    alarms_active.labels(severity=lv).set(sev_counts.get(lv, 0))
            except Exception:  # noqa: BLE001
                pass

        except Exception:
            pass
        await asyncio.sleep(5)


# ======================================================================
#  告警周期兜底扫描 — 基于 metric_raws 的服务端统一判定
#  (WS 断连 / 上传路径漏评估 / 多客户端不共享状态 等问题的根治手段:
#   规则判定完全在后端执行, 前端只做展示与启停)
# ======================================================================
ALARM_SWEEP_INTERVAL_SEC = 30


async def alarm_sweep_loop():
    """每 30 秒: ① 扫描 metric_raws 最新值做越限判定 ② 检查 warn 升级。"""
    from app.db.session import SessionLocal
    from app.services import alarm_engine

    while True:
        await asyncio.sleep(ALARM_SWEEP_INTERVAL_SEC)
        db = None
        try:
            db = SessionLocal()
            # 兜底判定: 与上传路径共用 evaluate(), 收敛窗口天然去重
            await asyncio.to_thread(alarm_engine.sweep_recent_metrics, db)
        except Exception as e:
            logger.debug("告警兜底扫描跳过 (DB 不可用?): %s", e)
        finally:
            if db is not None:
                db.close()
        try:
            # 升级检查不依赖 DB (纯内存活跃告警)
            alarm_engine.check_escalations()
        except Exception as e:
            logger.warning("告警升级检查异常: %s", e)


# ======================================================================
#  测点保留循环 (与 alarm_sweep_loop 同构)
#  原始测点表 metric_raws 若不加 TTL 会无限膨胀, 影响历史查询与告警扫描性能。
#  P0-1: 清理按存储引擎分层 —— TimescaleDB 走 drop_chunks; 普通物化视图分批 DELETE
#  每批提交后 refresh_views, 使聚合与保留窗口重新对齐 (见 crud.external.delete_old_metrics)。
# ======================================================================
METRIC_RETENTION_INTERVAL_SEC = settings.EXTERNAL_METRIC_RETENTION_INTERVAL_SEC
METRIC_RETENTION_DAYS = settings.EXTERNAL_METRIC_RETENTION_DAYS
METRIC_RETENTION_BATCH_SIZE = settings.EXTERNAL_METRIC_RETENTION_BATCH_SIZE


async def metric_retention_loop():
    from datetime import datetime, timedelta, timezone

    while True:
        await asyncio.sleep(METRIC_RETENTION_INTERVAL_SEC)
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=METRIC_RETENTION_DAYS)
            db = SessionLocal()
            try:
                deleted = ext_crud.delete_old_metrics(
                    db, cutoff, batch_size=METRIC_RETENTION_BATCH_SIZE
                )
                db.commit()  # P0-1: delete_old_metrics 内已按批提交, 此处为幂等收尾
                if deleted:
                    logger.info(
                        "[metric_retention] 清理 %d 条过期测点 (早于 %s, 保留 %d 天)",
                        deleted, cutoff.isoformat(), METRIC_RETENTION_DAYS,
                    )
                # [B4] 容量/能耗分析型长期时序: 在 retention 清理后做每日 rollup,
                # 写入独立的 capacity_energy_history (retention 不清它), 形成真实长期趋势。
                try:
                    from app.services import capacity_energy as ce

                    ce.rollup_recent(db, days=1)
                    db.commit()
                except Exception as e:  # noqa: BLE001
                    logger.debug("[metric_retention] 容量/能耗 rollup 跳过: %s", e)
            finally:
                db.close()
        except Exception as e:  # noqa: BLE001
            logger.warning("[metric_retention] 保留清理跳过 (DB 不可用?): %s", e)


# ======================================================================
#  种子数据 (幂等)
# ======================================================================
def _seed_default_users():
    """首次启动时自动创建默认角色与管理员 (admin/admin123)。"""
    import logging
    logger = logging.getLogger("seed")
    from app.core.security import hash_password
    from app.db.session import SessionLocal, engine
    from app.models.user import Role, User

    db = None
    try:
        db = SessionLocal()
        from sqlalchemy import text
        db.execute(text("select 1"))
    except Exception:
        if db is not None:
            db.close()
        return  # 数据库不可用，静默跳过

    try:
        from app.models import Base  # 触发 metadata 收集
        Base.metadata.create_all(bind=engine)
        logger.info("已确保 ORM 表结构就绪")
        # 兜底: 对已存在但缺列的旧表补齐 (create_all 不改已有表结构)
        _ensure_missing_columns(db)

        default_roles = [
            ("admin", "超级管理员", ["*"]),
            ("operator", "运维操作员", [
                "dashboard:read", "equipment:read", "equipment:write",
                "alarm:read", "alarm:write", "hvac:read", "power:read",
                "security:read", "ops:read", "ops:write",
            ]),
            ("viewer", "只读用户", [
                "dashboard:read", "equipment:read", "alarm:read",
                "hvac:read", "power:read", "security:read", "ops:read",
            ]),
        ]
        for name, label, perms in default_roles:
            existing = db.query(Role).filter(Role.name == name).first()
            if existing is None:
                db.add(Role(name=name, label=label, permissions=json.dumps(perms)))

        db.flush()

        admin = db.query(User).filter(User.username == "admin").first()
        if admin is None:
            admin = User(
                username="admin",
                password_hash=hash_password("admin123"),
                display_name="系统管理员",
                is_superuser=True,
                is_active=True,
            )
            db.add(admin)
            db.flush()
            admin_role = db.query(Role).filter(Role.name == "admin").first()
            if admin_role:
                admin.roles = [admin_role]

        demo_users = [
            ("operator", "Op@123456", "运维操作员", "operator"),
            ("viewer", "View@123456", "只读访客", "viewer"),
        ]
        for uname, pwd, disp, rname in demo_users:
            if db.query(User).filter(User.username == uname).first() is None:
                u = User(username=uname, password_hash=hash_password(pwd), display_name=disp, is_active=True)
                r = db.query(Role).filter(Role.name == rname).first()
                if r:
                    u.roles = [r]
                db.add(u)

        db.commit()
        logger.info("种子数据已就绪: 默认角色(3) + 管理员(admin/admin123) + 演示账号(operator/viewer)")
    except Exception as e:
        db.rollback()
        logger.warning("种子数据初始化跳过 (表可能尚未迁移): %s", e)
    finally:
        db.close()


def _seed_knowledge_and_shift():
    """首次启动时填充知识库与值班排班的演示数据 (幂等)。"""
    import logging
    logger = logging.getLogger("seed")
    from datetime import datetime, timedelta

    from app.db.session import SessionLocal, engine
    from app.models import Base

    db = None
    try:
        db = SessionLocal()
        from sqlalchemy import text
        db.execute(text("select 1"))
    except Exception:
        if db is not None:
            db.close()
        return

    try:
        Base.metadata.create_all(bind=engine)
        from app.crud import knowledge as kb_crud
        from app.crud import shift as shift_crud

        samples = [
            {
                "code": "KB-0001", "title": "冷水机组喘振应急处置预案", "category": "暖通-冷源",
                "domain": "hvac_source", "type": "emergency",
                "relatedCategories": ["暖通-冷源"], "relatedDomains": ["hvac_source"],
                "relatedMetrics": ["supply_temp", "chw_supply", "cop"],
                "tags": ["冷机", "喘振", "紧急"], "summary": "冷机运行中出现喘振声与振动时的处置流程。",
                "content": "1) 立即降低冷机负载；2) 检查导叶开度与冷凝器结垢；3) 切换备用冷机；4) 通知暖通工程师到场。",
                "steps": ["降低负载至 50%", "确认导叶开度", "切换备用机组", "记录并上报"],
                "owner": "暖通班", "hot": True,
            },
            {
                "code": "KB-0002", "title": "柴发带载启动标准作业", "category": "电力-柴发",
                "domain": "power_genset", "type": "sop",
                "relatedCategories": ["电力-柴发"], "relatedDomains": ["power_genset"],
                "relatedMetrics": ["output_power", "oil_temp", "fuel_level"],
                "tags": ["柴发", "市电中断"], "summary": "市电中断后柴发自启与并机带载 SOP。",
                "content": "1) 确认市电失电；2) 检查柴发自启成功；3) 并机同步；4) 逐步带载关键负载。",
                "steps": ["确认失电", "检查自启", "并机同步", "带载"],
                "owner": "电气班", "hot": True,
            },
            {
                "code": "KB-0003", "title": "UPS 蓄电池内阻超标处理", "category": "电力-电池",
                "domain": "power_battery", "type": "case",
                "relatedCategories": ["电力-电池"], "relatedDomains": ["power_battery"],
                "relatedMetrics": ["voltage", "temperature", "soc"],
                "tags": ["UPS", "电池"], "summary": "蓄电池内阻超标预警的排查与更换案例。",
                "content": "1) 单体内阻测试；2) 均衡充电；3) 超差单体重换。",
                "steps": ["内阻测试", "均衡充电", "单体重换"],
                "owner": "电气班",
            },
            {
                "code": "KB-0004", "title": "机房温湿度超标巡检要点", "category": "暖通-末端",
                "domain": "hvac_terminal", "type": "manual",
                "relatedCategories": ["暖通-末端"], "relatedDomains": ["hvac_terminal"],
                "relatedMetrics": ["supply_temp", "return_temp", "humidity"],
                "tags": ["末端", "温湿度"], "summary": "CRAC 送风温度与机房湿度超标的巡检要点。",
                "content": "1) 检查 CRAC 运行台数与设定；2) 检查加湿罐；3) 排查冷热通道。",
                "steps": ["检查 CRAC", "检查加湿", "排查通道"],
                "owner": "暖通班",
            },
            {
                "code": "KB-0005", "title": "消防主机火警确认流程", "category": "消防",
                "domain": "security_fire", "type": "emergency",
                "relatedCategories": ["消防"], "relatedDomains": ["security_fire"],
                "relatedMetrics": ["smoke", "temp"],
                "tags": ["消防", "火警"], "summary": "消防主机告警确认与疏散联动流程。",
                "content": "1) 确认火警点位；2) 现场确认；3) 启动疏散广播；4) 通知消防。",
                "steps": ["确认点位", "现场确认", "启动疏散", "通知消防"],
                "owner": "安防班", "hot": True,
            },
            {
                "code": "SOP-0001", "title": "冷水机组月度维护标准作业", "category": "暖通-冷源",
                "domain": "hvac_source", "type": "sop",
                "relatedCategories": ["暖通-冷源"], "relatedDomains": ["hvac_source"],
                "relatedMetrics": ["supply_temp", "evap_temp", "cond_temp"],
                "tags": ["冷机", "月度维护", "SOP"],
                "summary": "冷水机组月度预防性维护的标准作业步骤。",
                "content": "1) 检查冷机运行参数、振动与噪声；2) 清洗冷凝器与蒸发器换热面；3) 校验导叶开度与加载曲线；4) 测试备用机组自动切换。",
                "steps": ["检查运行参数与振动", "清洗冷凝器/蒸发器", "校验导叶开度", "测试备用机组切换"],
                "owner": "暖通班",
            },
            {
                "code": "SOP-0002", "title": "冷却塔维护与填料清洗标准作业", "category": "暖通-冷源",
                "domain": "hvac_source", "type": "sop",
                "relatedCategories": ["暖通-冷源"], "relatedDomains": ["hvac_source"],
                "relatedMetrics": ["flow", "supply_temp"],
                "tags": ["冷却塔", "填料", "SOP"],
                "summary": "冷却塔布水、填料与风机的周期性维护作业。",
                "content": "1) 清理布水器与填料表面污堵；2) 检查风机皮带与减速箱油位；3) 校准飘水与补水液位；4) 记录出水温度趋势。",
                "steps": ["清理布水器/填料", "检查风机皮带", "校准飘水补水", "记录出水温度"],
                "owner": "暖通班",
            },
            {
                "code": "SOP-0003", "title": "精密空调滤网更换与加湿维护标准作业", "category": "暖通-末端",
                "domain": "hvac_terminal", "type": "sop",
                "relatedCategories": ["暖通-末端"], "relatedDomains": ["hvac_terminal"],
                "relatedMetrics": ["humidity", "return_temp"],
                "tags": ["精密空调", "滤网", "加湿", "SOP"],
                "summary": "末端精密空调滤网与加湿罐的维护作业。",
                "content": "1) 更换送风滤网并清洁机组；2) 清洗加湿罐与补水阀；3) 校准温湿度设定点；4) 检查冷凝水排放管路。",
                "steps": ["更换送风滤网", "清洗加湿罐", "校准温湿度", "检查冷凝水"],
                "owner": "暖通班",
            },
            {
                "code": "SOP-0004", "title": "配电柜停电检修与送电标准作业", "category": "电力-低压",
                "domain": "power_lv", "type": "sop",
                "relatedCategories": ["电力-低压"], "relatedDomains": ["power_lv"],
                "relatedMetrics": ["voltage", "current"],
                "tags": ["配电", "停电检修", "SOP"],
                "summary": "低压配电柜停电检修与复电的标准作业。",
                "content": "1) 申请工作票并验电；2) 悬挂标识牌并上锁；3) 执行检修作业；4) 撤牌复电并核相。",
                "steps": ["申请工作票/验电", "挂牌上锁", "执行检修", "撤牌复电核相"],
                "owner": "电气班",
            },
            {
                "code": "SOP-0005", "title": "视频监控摄像头巡检与存储排查标准作业", "category": "安防-安防",
                "domain": "sec_security", "type": "sop",
                "relatedCategories": ["安防-安防"], "relatedDomains": ["sec_security"],
                "relatedMetrics": ["power"],
                "tags": ["视频", "摄像头", "SOP"],
                "summary": "视频监控摄像头在线、画面与 NVR 存储的排查作业。",
                "content": "1) 检查摄像头在线状态与画面质量；2) 清理镜头与校正角度；3) 核查 NVR 存储与录像完整性；4) 处理离线告警。",
                "steps": ["检查在线/画面", "清理镜头角度", "核查存储录像", "处理离线"],
                "owner": "安防班",
            },
            {
                "code": "EOP-0001", "title": "冷机群控通讯中断应急", "category": "暖通-冷源",
                "domain": "hvac_source", "type": "emergency",
                "relatedCategories": ["暖通-冷源", "楼控-BA"], "relatedDomains": ["hvac_source", "bms"],
                "relatedMetrics": ["flow", "supply_temp"],
                "tags": ["群控", "通讯中断", "应急"],
                "summary": "冷机群控系统通讯中断时的现场应急处置。",
                "content": "1) 确认群控离线范围与受影响机组；2) 切换至本地手动控制；3) 现场监控冷机运行参数；4) 恢复通讯并复位群控。",
                "steps": ["确认离线范围", "切本地手动", "现场监控", "恢复通讯复位"],
                "owner": "暖通班", "hot": True,
            },
            {
                "code": "EOP-0002", "title": "机房漏水告警应急", "category": "给排水",
                "domain": "water", "type": "emergency",
                "relatedCategories": ["给排水", "暖通-末端"], "relatedDomains": ["water", "hvac_terminal"],
                "relatedMetrics": ["flow"],
                "tags": ["漏水", "应急"],
                "summary": "机房漏水告警的定位与应急处置。",
                "content": "1) 定位漏水点与受影响区域；2) 关闭对应阀门并组织排水；3) 切断受影响设备电源；4) 布防并上报。",
                "steps": ["定位漏水点", "关阀排水", "断电设备", "上报"],
                "owner": "运维班", "hot": True,
            },
            {
                "code": "EOP-0003", "title": "消防极早期告警现场确认应急", "category": "消防",
                "domain": "security_fire", "type": "emergency",
                "relatedCategories": ["消防"], "relatedDomains": ["security_fire"],
                "relatedMetrics": ["smoke", "temp"],
                "tags": ["消防", "极早期", "应急"],
                "summary": "吸气式极早期烟雾探测告警的现场确认流程。",
                "content": "1) 确认告警点位与极早期采样浓度；2) 双人现场确认；3) 启动疏散与声光报警；4) 通知消防并现场守候。",
                "steps": ["确认告警点位", "双人现场确认", "启动疏散", "通知消防"],
                "owner": "安防班", "hot": True,
            },
            {
                "code": "EOP-0004", "title": "门禁系统故障应急", "category": "安防-安防",
                "domain": "sec_security", "type": "emergency",
                "relatedCategories": ["安防-安防"], "relatedDomains": ["sec_security"],
                "relatedMetrics": ["power"],
                "tags": ["门禁", "故障", "应急"],
                "summary": "门禁系统故障导致受控区无法出入的应急处置。",
                "content": "1) 确认故障范围与受控区域；2) 启用机械钥匙与人工身份核验；3) 隔离故障控制器；4) 恢复并复盘。",
                "steps": ["确认故障范围", "启用机械钥匙", "隔离控制器", "恢复复盘"],
                "owner": "安防班",
            },
            {
                "code": "CAS-0001", "title": "冷却塔飘水致相邻设备结露案例", "category": "暖通-冷源",
                "domain": "hvac_source", "type": "case",
                "relatedCategories": ["暖通-冷源", "电力-低压"], "relatedDomains": ["hvac_source", "power_lv"],
                "relatedMetrics": ["flow", "humidity"],
                "tags": ["冷却塔", "飘水", "结露", "案例"],
                "summary": "冷却塔飘水使相邻配电/控制柜表面结露的案例与经验。",
                "content": "现象: 冷却塔飘水使相邻配电柜与控制柜表面结露。原因: 布水不均匀、挡水板失效。处置: 调整布水均匀性、加装/修复挡水板、加强通风除湿。经验: 飘水问题优先查布水均匀性与挡水板。",
                "steps": ["调整布水均匀性", "加装/修复挡水板", "加强通风除湿", "纳入季度巡检"],
                "owner": "暖通班",
            },
            {
                "code": "CAS-0002", "title": "UPS 逆变器过载跳闸案例", "category": "电力-UPS",
                "domain": "power_ups", "type": "case",
                "relatedCategories": ["电力-UPS"], "relatedDomains": ["power_ups"],
                "relatedMetrics": ["power", "current"],
                "tags": ["UPS", "过载", "跳闸", "案例"],
                "summary": "负载突增导致 UPS 逆变器过载跳闸的案例与经验。",
                "content": "现象: 负载突增致 UPS 逆变器过载跳闸。原因: 容量裕度不足、未按需分级带载。处置: 减载恢复供电、分级带载、核算容量裕度。经验: 关键负载应做容量仿真。",
                "steps": ["减载恢复供电", "分级带载", "核算容量裕度", "优化负载分配"],
                "owner": "电气班",
            },
            {
                "code": "CAS-0003", "title": "视频存储硬盘满导致录像丢失案例", "category": "安防-安防",
                "domain": "sec_security", "type": "case",
                "relatedCategories": ["安防-安防"], "relatedDomains": ["sec_security"],
                "relatedMetrics": ["power"],
                "tags": ["视频", "存储", "录像丢失", "案例"],
                "summary": "NVR 硬盘写满后新录像被覆盖或丢失的案例与经验。",
                "content": "现象: NVR 硬盘写满后新录像被覆盖或丢失。原因: 未设循环覆盖与容量预警。处置: 扩容存储、配置循环覆盖、加容量告警。经验: 存储需容量预警与定期抽检。",
                "steps": ["扩容存储", "配置循环覆盖", "加容量告警", "定期抽检录像"],
                "owner": "安防班",
            },
        ]
        for s in samples:
            kb_crud.upsert(db, data=s)
        logger.info("已同步/种子知识库 %d 条 (含 SOP/EOP/CAS 细粒度条目)", len(samples))

        if shift_crud.count(db) == 0:
            today = datetime.now()
            day_members = [
                {"name": "张伟", "role": "暖通工程师", "phone": "13800000001"},
                {"name": "李娜", "role": "电气工程师", "phone": "13800000002"},
                {"name": "王强", "role": "安防值班员", "phone": "13800000003"},
            ]
            night_members = [
                {"name": "赵敏", "role": "值守班长", "phone": "13800000004"},
                {"name": "陈晨", "role": "电气值班员", "phone": "13800000005"},
            ]
            for i in range(14):
                d = (today + timedelta(days=i)).strftime("%Y-%m-%d")
                shift_crud.create(db, data={"date": d, "shift": "day", "members": day_members, "leader": "张伟"})
                shift_crud.create(db, data={"date": d, "shift": "night", "members": night_members, "leader": "赵敏"})
            logger.info("已种子排班 14 天 x 2 班")
    except Exception as e:
        if db is not None:
            db.rollback()
        logger.warning("知识库/排班种子跳过: %s", e)
    finally:
        if db is not None:
            db.close()


def _seed_drill_risk_inspection():
    """首次启动时填充演练 / 风险 / 巡检演示数据 (幂等)。"""
    import logging
    logger = logging.getLogger("seed")
    from datetime import datetime, timedelta

    from app.db.session import SessionLocal, engine
    from app.models import Base

    db = None
    try:
        db = SessionLocal()
        from sqlalchemy import text
        db.execute(text("select 1"))
    except Exception:
        if db is not None:
            db.close()
        return

    try:
        Base.metadata.create_all(bind=engine)
        from app.crud import drill as drill_crud
        from app.crud import risk as risk_crud
        from app.crud import inspection as insp_crud

        if drill_crud.count(db) == 0:
            t = datetime.now()
            drills = [
                {"code": "DR-001", "name": "年度全站停电演练", "type": "电力",
                 "date": (t - timedelta(days=40)).strftime("%Y-%m-%d"), "state": "已完成", "result": "通过"},
                {"code": "DR-002", "name": "柴发并机带载演练", "type": "电力",
                 "date": (t - timedelta(days=20)).strftime("%Y-%m-%d"), "state": "已完成", "result": "通过"},
                {"code": "DR-003", "name": "冷水机组喘振处置演练", "type": "暖通",
                 "date": (t - timedelta(days=10)).strftime("%Y-%m-%d"), "state": "已完成", "result": "未通过"},
                {"code": "DR-004", "name": "消防疏散联动演练", "type": "消防",
                 "date": (t - timedelta(days=5)).strftime("%Y-%m-%d"), "state": "已完成", "result": "通过"},
                {"code": "DR-005", "name": "双路市电切换演练", "type": "电力",
                 "date": (t + timedelta(days=8)).strftime("%Y-%m-%d"), "state": "已编排", "result": "—"},
                {"code": "DR-006", "name": "蓄电池放电核容演练", "type": "电力",
                 "date": (t + timedelta(days=20)).strftime("%Y-%m-%d"), "state": "计划中", "result": "—"},
            ]
            for s in drills:
                drill_crud.create(db, data=s)
            logger.info("已种子演练计划 %d 条", len(drills))

        if risk_crud.count(db) == 0:
            risks = [
                {"code": "R-001", "risk": "市电中断后柴发启动失败", "cat": "电力",
                 "prob": 4, "impact": 4, "ctrl": "双柴发冗余 + 月度带载试机", "owner": "电气班"},
                {"code": "R-002", "risk": "冷水机组喘振导致供冷中断", "cat": "暖通",
                 "prob": 3, "impact": 4, "ctrl": "导叶保护 + 备用机组自动切换", "owner": "暖通班"},
                {"code": "R-003", "risk": "UPS 单点故障影响核心负载", "cat": "电力",
                 "prob": 2, "impact": 3, "ctrl": "2N 供电路由 + 进场巡检", "owner": "电气班"},
                {"code": "R-004", "risk": "空调失效形成局部热点", "cat": "暖通",
                 "prob": 3, "impact": 2, "ctrl": "冷热通道封闭 + 温感联动", "owner": "暖通班"},
                {"code": "R-005", "risk": "网络单链路中断", "cat": "网络",
                 "prob": 2, "impact": 2, "ctrl": "双上联冗余", "owner": "网络班"},
                {"code": "R-006", "risk": "旧照明回路改造临时风险", "cat": "其他",
                 "prob": 1, "impact": 2, "ctrl": "已纳入变更闭环", "owner": "运维", "closed": 1},
            ]
            for s in risks:
                risk_crud.create(db, data=s)
            logger.info("已种子风险项 %d 条", len(risks))

        if insp_crud.route_count(db) == 0:
            today = datetime.now()
            y = today.strftime("%Y-%m-%d")
            routes = [
                {"code": "RT-001", "freq": "每日", "items": 28, "last": (today - timedelta(days=1)).strftime("%Y-%m-%d"), "next": y, "state": "已完成"},
                {"code": "RT-002", "freq": "每日", "items": 26, "last": (today - timedelta(days=1)).strftime("%Y-%m-%d"), "next": y, "state": "已完成"},
                {"code": "RT-003", "freq": "每周", "items": 12, "last": (today - timedelta(days=3)).strftime("%Y-%m-%d"), "next": (today + timedelta(days=4)).strftime("%Y-%m-%d"), "state": "已完成"},
                {"code": "RT-004", "freq": "每日", "items": 8, "last": (today - timedelta(days=1)).strftime("%Y-%m-%d"), "next": y, "state": "已完成"},
                {"code": "RT-005", "freq": "每周", "items": 10, "last": (today - timedelta(days=5)).strftime("%Y-%m-%d"), "next": (today + timedelta(days=2)).strftime("%Y-%m-%d"), "state": "已完成"},
                {"code": "RT-006", "freq": "每日", "items": 6, "last": (today - timedelta(days=1)).strftime("%Y-%m-%d"), "next": y, "state": "已完成"},
            ]
            for r in routes:
                insp_crud.create_route(db, data=r)
            logger.info("已种子巡检路线 %d 条", len(routes))

        if insp_crud.finding_count(db) == 0:
            t = datetime.now()
            findings = [
                {"route": "RT-001", "item": "机柜 C12 出风温度偏高 (28.5℃)", "ts": t.strftime("%Y-%m-%d %H:%M"), "lv": "warn", "action": "已通知暖通班复核风量"},
                {"route": "RT-003", "item": "柴发机油位偏低", "ts": t.strftime("%Y-%m-%d %H:%M"), "lv": "info", "action": "已补加机油并复测"},
                {"route": "RT-005", "item": "冷却塔填料轻微结垢", "ts": t.strftime("%Y-%m-%d %H:%M"), "lv": "warn", "action": "计划本月清洗"},
            ]
            for f in findings:
                insp_crud.create_finding(db, data=f)
            logger.info("已种子巡检发现 %d 条", len(findings))
    except Exception as e:
        if db is not None:
            db.rollback()
        logger.warning("演练/风险/巡检种子跳过: %s", e)
    finally:
        if db is not None:
            db.close()


def _seed_tenants():
    """首次启动时填充租户演示数据 (幂等)。"""
    import logging
    logger = logging.getLogger("seed")
    from app.db.session import SessionLocal, engine
    from app.models import Base

    db = None
    try:
        db = SessionLocal()
        from sqlalchemy import text
        db.execute(text("select 1"))
    except Exception:
        if db is not None:
            db.close()
        return

    try:
        Base.metadata.create_all(bind=engine)
        from app.crud import tenant as tenant_crud

        if tenant_crud.count(db) == 0:
            seeds = [
                {"name": "云栖科技", "code": "TH-001", "contact": "王经理", "phone": "13800000001", "industry": "互联网", "contractNo": "HT-2023-001", "validFrom": "2023-01-01", "validTo": "2026-12-31", "status": "active", "rent": 120000, "cabinets": 8, "quotaCabinets": 10, "quotaDevices": 200, "quotaPowerKw": 160, "quotaBandwidthMbps": 2000, "usedDevices": 168, "usedPowerKw": 142.6, "usedBandwidthMbps": 1680, "uOccupied": 264, "note": "核心客户"},
                {"name": "智算网络", "code": "TH-002", "contact": "李总", "phone": "13800000002", "industry": "人工智能", "contractNo": "HT-2023-002", "validFrom": "2023-03-01", "validTo": "2025-09-30", "status": "expired", "rent": 200000, "cabinets": 12, "quotaCabinets": 12, "quotaDevices": 320, "quotaPowerKw": 300, "quotaBandwidthMbps": 4000, "usedDevices": 305, "usedPowerKw": 292.4, "usedBandwidthMbps": 3720, "uOccupied": 396, "note": "合同待续签"},
                {"name": "金信金融", "code": "TH-003", "contact": "赵主管", "phone": "13800000003", "industry": "金融", "contractNo": "HT-2023-003", "validFrom": "2023-06-01", "validTo": "2027-06-30", "status": "active", "rent": 150000, "cabinets": 6, "quotaCabinets": 10, "quotaDevices": 150, "quotaPowerKw": 120, "quotaBandwidthMbps": 1500, "usedDevices": 142, "usedPowerKw": 119.8, "usedBandwidthMbps": 980, "uOccupied": 198, "note": "等保三级"},
                {"name": "联创医疗", "code": "TH-004", "contact": "孙主任", "phone": "13800000004", "industry": "医疗", "contractNo": "HT-2024-001", "validFrom": "2024-01-15", "validTo": "2026-01-14", "status": "pending", "rent": 90000, "cabinets": 4, "quotaCabinets": 8, "quotaDevices": 100, "quotaPowerKw": 80, "quotaBandwidthMbps": 1000, "usedDevices": 61, "usedPowerKw": 52.3, "usedBandwidthMbps": 410, "uOccupied": 132, "note": "新签待启用"},
                {"name": "远图物流", "code": "TH-005", "contact": "周经理", "phone": "13800000005", "industry": "物流", "contractNo": "HT-2024-002", "validFrom": "2024-05-01", "validTo": "2026-04-30", "status": "active", "rent": 80000, "cabinets": 5, "quotaCabinets": 6, "quotaDevices": 90, "quotaPowerKw": 70, "quotaBandwidthMbps": 900, "usedDevices": 88, "usedPowerKw": 68.9, "usedBandwidthMbps": 870, "uOccupied": 165, "note": "机柜接近配额"},
            ]
            for s in seeds:
                tenant_crud.create(db, data=s)
            logger.info("已种子租户 %d 条", len(seeds))
    except Exception as e:
        if db is not None:
            db.rollback()
        logger.warning("租户种子跳过: %s", e)
    finally:
        if db is not None:
            db.close()


def _seed_external_devices():
    """首次启动时填充采集器接入(外部设备)演示数据 (幂等)。"""
    import logging
    import random
    logger = logging.getLogger("seed")
    from datetime import datetime, timedelta

    from app.db.session import SessionLocal, engine
    from app.models import Base

    db = None
    try:
        db = SessionLocal()
        from sqlalchemy import text
        db.execute(text("select 1"))
    except Exception:
        if db is not None:
            db.close()
        return

    try:
        Base.metadata.create_all(bind=engine)
        from sqlalchemy import select, func
        from app.crud import external as ext_crud
        from app.models.external import ExternalDevice, MetricRaw
        from app.schemas.external import DeviceRegisterRequest, MetricQuality
        from app.collectors.mock_collector import _CATEGORY_METRICS

        if (db.scalar(select(func.count()).select_from(ExternalDevice)) or 0) > 0:
            return

        devices = [
            ("CHL-A01", "10.20.11.21", "SN-CHL-A01-7731", "CVHF-1000", "1#冷水机组", "YORK", "hvac_source", "chiller", "冷站 B1", "modbus-tcp"),
            ("CT-A01", "10.20.11.31", "SN-CT-A01-2210", "NCW-300", "1#冷却塔", "BAC", "hvac_source", "cooling_tower", "冷站 B1", "modbus-tcp"),
            ("CHWP-A01", "10.20.11.41", "SN-CHWP-A01-1190", "KSB-200", "1#冷冻水泵", "KSB", "hvac_source", "chw_pump", "冷站 B1", "modbus-tcp"),
            ("CRAC-A01", "10.20.21.11", "SN-CRAC-A01-5520", "Liebert-PEX+", "A区1#精密空调", "Emerson", "hvac_terminal", "crac", "机房 A 列头", "modbus-tcp"),
            ("FAU-A01", "10.20.21.21", "SN-FAU-A01-3301", "Gree-FAU", "A区新风机组", "Gree", "hvac_terminal", "fau", "机房 A", "modbus-tcp"),
            ("HV-IN-01", "10.20.31.11", "SN-HV-IN-01-9001", "Schneider-SM6", "10kV 1#进线柜", "Schneider", "power_hv", "hv_incomer", "10kV 配电室", "iec104"),
            ("TR-A01", "10.20.31.21", "SN-TR-A01-7712", "S11-2000", "1#变压器", "Siemens", "power_lv", "transformer", "低压室", "modbus-tcp"),
            ("UPS-A01", "10.20.31.31", "SN-UPS-A01-6630", "Hipulse-U", "A区1#UPS", "Emerson", "power_lv", "ups", "UPS 室", "snmp"),
            ("GEN-A01", "10.20.31.41", "SN-GEN-A01-4410", "MTU-1600", "1#柴油发电机", "MTU", "power_genset", "genset", "柴发机房", "modbus-tcp"),
            ("CAM-A01", "10.20.41.11", "SN-CAM-A01-8801", "IPC-HFW", "A区1#球机", "Dahua", "security_cctv", "camera", "机房 A 走道", "onvif"),
        ]
        for d in devices:
            ext_crud.upsert_device(db, DeviceRegisterRequest(
                device_id=d[0], ip=d[1], sn=d[2], model=d[3],
                name=d[4], vendor=d[5], domain=d[6], category=d[7],
                location=d[8], protocol=d[9],
                tags=[d[7], d[6]],
                description=f"{d[4]} 演示采集设备",
            ))
        # 将演示设备归属到当前数据中心 (idc_id=1), 供关联服务聚合
        from sqlalchemy import update as sa_update
        db.execute(sa_update(ExternalDevice).values(idc_id=1))
        db.commit()
        logger.info("已种子外部设备 %d 台", len(devices))

        now = datetime.utcnow()
        total = 0
        for d in devices:
            defs = _CATEGORY_METRICS.get(d[7], [])
            if not defs:
                defs = [("online", "", 1, 1)]
            chosen = defs[:12]
            for (mname, unit, lo, hi) in chosen:
                base = round(random.uniform(lo, hi), 2)
                for k in range(6):
                    db.add(MetricRaw(
                        device_id=d[0],
                        ts=now - timedelta(minutes=10 * (5 - k)),
                        metric_name=mname,
                        value=round(base + random.uniform(-0.01, 0.01) * max(abs(base), 1), 2),
                        quality=MetricQuality.GOOD.value,
                        unit=unit,
                    ))
                    total += 1
            db.commit()
        logger.info("已种子测点 %d 条", total)
    except Exception as e:
        if db is not None:
            db.rollback()
        logger.warning("外部设备种子跳过: %s", e)
    finally:
        if db is not None:
            db.close()


def _seed_idc():
    """首次启动时填充多数据中心演示数据 (幂等)。"""
    import logging
    logger = logging.getLogger("seed")
    from app.db.session import SessionLocal, engine
    from app.models import Base

    db = None
    try:
        db = SessionLocal()
        from sqlalchemy import text
        db.execute(text("select 1"))
    except Exception:
        if db is not None:
            db.close()
        return

    try:
        Base.metadata.create_all(bind=engine)
        from sqlalchemy import select, func
        from app.models.idc import IDC

        if (db.scalar(select(func.count()).select_from(IDC)) or 0) > 0:
            return

        seeds = [
            {"code": "EC1-HZ", "name": "杭州东冠数据中心", "region": "华东1(杭州)", "address": "杭州市滨江区", "power_capacity_mw": 20.0, "cooling_capacity_mw": 18.0, "rack_capacity": 1200, "rooms": 6, "status": "运营", "capacity_kw": 8, "description": "核心生产中心，承载主要业务", "is_current": True},
            {"code": "EC2-SH", "name": "上海临港数据中心", "region": "华东2(上海)", "address": "上海市浦东新区临港", "power_capacity_mw": 30.0, "cooling_capacity_mw": 27.0, "rack_capacity": 1800, "rooms": 8, "status": "运营", "capacity_kw": 10, "description": "高密算力中心", "is_current": False},
            {"code": "NC1-BJ", "name": "北京亦庄数据中心", "region": "华北2(北京)", "address": "北京市大兴区亦庄", "power_capacity_mw": 25.0, "cooling_capacity_mw": 22.0, "rack_capacity": 1500, "rooms": 7, "status": "运营", "capacity_kw": 9, "description": "北方灾备中心", "is_current": False},
            {"code": "SC1-CD", "name": "成都天府数据中心", "region": "西南1(成都)", "address": "成都市天府新区", "power_capacity_mw": 15.0, "cooling_capacity_mw": 14.0, "rack_capacity": 900, "rooms": 5, "status": "建设", "capacity_kw": 7, "description": "新建西部节点，建设中", "is_current": False},
        ]
        for s in seeds:
            db.add(IDC(**s))
        db.commit()
        logger.info("已种子数据中心 %d 个", len(seeds))

        # 将尚无归属的外部设备归集到当前数据中心 (idc_id=1), 供关联服务聚合展示
        from sqlalchemy import update as sa_update
        from app.models.external import ExternalDevice
        db.execute(sa_update(ExternalDevice).where(ExternalDevice.idc_id.is_(None)).values(idc_id=1))
        db.commit()
    except Exception as e:
        if db is not None:
            db.rollback()
        logger.warning("数据中心种子跳过: %s", e)
    finally:
        if db is not None:
            db.close()


def _seed_alarm_rules():
    """首次启动用 DEFAULT_RULES 播种 alarm_rule 表 (幂等, 保留用户启停)。

    与 B7(规则配置化) 同源: alarm_rule 为规则配置单一事实源。
    """
    import logging
    logger = logging.getLogger("seed")
    from app.db.session import SessionLocal, engine
    from app.models import Base
    from app.services import alarm_engine

    db = None
    try:
        db = SessionLocal()
        from sqlalchemy import text
        db.execute(text("select 1"))
    except Exception:
        if db is not None:
            db.close()
        return
    try:
        Base.metadata.create_all(bind=engine)
        alarm_engine.seed_alarm_rules(db)
        logger.info("已种子告警规则 (与 DEFAULT_RULES 同源)")
    except Exception as e:
        if db is not None:
            db.rollback()
        logger.warning("告警规则种子跳过: %s", e)
    finally:
        if db is not None:
            db.close()


# ======================================================================
#  生命周期
# ======================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- 启动 ----
    try:
        _seed_default_users()
    except Exception as e:
        logger.warning("种子数据初始化跳过: %s", e)

    try:
        _seed_knowledge_and_shift()
    except Exception as e:
        logger.warning("知识库/排班种子跳过: %s", e)

    try:
        _seed_drill_risk_inspection()
    except Exception as e:
        logger.warning("演练/风险/巡检种子跳过: %s", e)

    try:
        _seed_external_devices()
    except Exception as e:
        logger.warning("外部设备种子跳过: %s", e)

    try:
        _seed_idc()
    except Exception as e:
        logger.warning("数据中心种子跳过: %s", e)

    try:
        _seed_tenants()
    except Exception as e:
        logger.warning("租户种子跳过: %s", e)

    try:
        _seed_alarm_rules()
    except Exception as e:
        logger.warning("告警规则种子跳过: %s", e)

    consumer_task = await maybe_start_consumer()
    mock_task = await maybe_start_mock_collector()

    from app.services import alarm_engine
    from app.services.alarm_persist import persist_alarm_event
    alarm_engine.register_notify_handler("db", persist_alarm_event)

    # [P2-7] 通知渠道接通: 启动即注册 WS 实时广播 + Webhook 预留通道,
    # 不再依赖 KPI 广播循环启动后才注册。告警面板经 WS 实时刷新, Webhook 默认关闭。
    from app.services import ws_broadcaster
    from app.services.alarm_notify_webhook import register_webhook_notifier
    ws_broadcaster.setup_alarm_notify()
    register_webhook_notifier()

    try:
        alarm_engine.hydrate_alarm_engine()
        logger.info("告警引擎运行态已从 DB hydrate (P0-3)")
    except Exception as e:
        logger.warning("告警引擎 hydrate 跳过: %s", e)

    kpi_task = asyncio.create_task(kpi_broadcast_loop(), name="kpi-broadcast")
    logger.info("KPI 广播循环已启动")

    from app.services.metric_agg import agg_refresh_loop
    agg_task = asyncio.create_task(agg_refresh_loop(), name="metric-agg-refresh")
    logger.info("测点聚合视图刷新循环已启动")

    sweep_task = asyncio.create_task(alarm_sweep_loop(), name="alarm-sweep")
    logger.info("告警周期兜底扫描循环已启动")

    retention_task = asyncio.create_task(metric_retention_loop(), name="metric-retention")
    logger.info("测点保留清理循环已启动 (保留 %d 天)", METRIC_RETENTION_DAYS)

    # [S-04] 数据源模式启动日志 + 生产误用检查
    if settings.DATA_SOURCE == "real":
        logger.info(
            "[数据源] 模式=real (真实采集器接入)。聚合层要求已注册外部设备存在, "
            "无真实数据时将拒绝服务 (HTTP 503)。"
        )
        if settings.EXTERNAL_MOCK_COLLECTOR_ENABLED:
            logger.warning(
                "[数据源] 检测到 DATA_SOURCE=real 但 EXTERNAL_MOCK_COLLECTOR_ENABLED=True, "
                "二者互斥。Mock 采集器推送的是演示数据, 生产真实模式下应设为 False。"
            )
    else:
        logger.info(
            "[数据源] 模式=mock (开发/演示)。无真实外部设备时静默回退内置生成器 (_source=generated)。"
        )

    try:
        yield
    finally:
        # ---- 关闭 ----
        for t in (consumer_task, mock_task, kpi_task, agg_task, sweep_task, retention_task):
            if t is not None:
                t.cancel()
                try:
                    await t
                except (asyncio.CancelledError, Exception):
                    pass
        logger.info("应用已关闭")
