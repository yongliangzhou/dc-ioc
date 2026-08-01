"""告警引擎运行态的 DB 持久化 (P0-3)。

设计:
- 所有读写对「DB 不可用」静默降级 (返回默认值 / 跳过), 保证引擎在无 DB 时仍按
  原纯内存模式运行; 因此单元测试 (无 DB) 行为不变。
- 写路径 (upsert / delete / set_*) 为 best-effort: 异常仅记录, 不影响主流程。
- 读路径提供内存降级兜底 (见 alarm_engine.get_active_alarms)。
"""
from __future__ import annotations

import json
import logging
from time import time as _now
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.alarm_state import (
    AlarmActiveState,
    AlarmRule,
    AlarmSuppressedDevice,
)

logger = logging.getLogger("alarm.engine")


def _get_db() -> Optional[Session]:
    try:
        db = SessionLocal()
        db.execute(text("select 1"))
        return db
    except Exception as e:  # noqa: BLE001
        logger.debug("alarm_store: DB 不可用, 降级内存态: %s", e)
        return None


# ---------------- 规则启停 (alarm_rule.enabled) ----------------

def load_disabled_set() -> set[str]:
    """返回被禁用的 rule_id 集合 (enabled=False)。DB 不可用时返回空。"""
    db = _get_db()
    if db is None:
        return set()
    try:
        rows = db.execute(
            text("SELECT rule_id FROM alarm_rule WHERE enabled = FALSE")
        ).fetchall()
        return {r[0] for r in rows}
    except Exception as e:  # noqa: BLE001
        logger.debug("load_disabled_set 失败: %s", e)
        return set()
    finally:
        db.close()


def set_rule_enabled(rule_id: str, enabled: bool) -> None:
    db = _get_db()
    if db is None:
        return
    try:
        db.execute(
            text(
                "UPDATE alarm_rule SET enabled = :en, updated_at = now() "
                "WHERE rule_id = :rid"
            ),
            {"en": enabled, "rid": rule_id},
        )
        db.commit()
    except Exception as e:  # noqa: BLE001
        logger.debug("set_rule_enabled 失败: %s", e)
        db.rollback()
    finally:
        db.close()


def set_rule_silenced(rule_id: str, silenced: bool, duration_minutes: int = 0) -> None:
    """静默标记 (alarm_rule 表新增 silenced 列, 0=不限时长)。"""
    db = _get_db()
    if db is None:
        return
    try:
        db.execute(
            text(
                "UPDATE alarm_rule SET enabled = FALSE, silenced = :sl, "
                "silence_until = CASE WHEN :dur > 0 THEN now() + :dur * INTERVAL '1 minute' ELSE NULL END, "
                "updated_at = now() WHERE rule_id = :rid"
            ),
            {"sl": silenced, "dur": duration_minutes, "rid": rule_id},
        )
        db.commit()
    except Exception as e:  # noqa: BLE001
        logger.debug("set_rule_silenced 失败: %s", e)
        db.rollback()
    finally:
        db.close()


def insert_rule(rule_id: str, category: str, metric: str,
                warn_lo: float | None, warn_hi: float | None,
                crit_lo: float | None, crit_hi: float | None,
                unit: str = "") -> None:
    """创建告警规则记录 (best-effort)。"""
    db = _get_db()
    if db is None:
        return
    try:
        db.execute(
            text(
                "INSERT INTO alarm_rule (rule_id, category, metric, warn_lo, warn_hi, "
                " crit_lo, crit_hi, unit, enabled, created_at, updated_at) "
                "VALUES (:rid, :cat, :met, :wlo, :whi, :clo, :chi, :u, TRUE, now(), now()) "
                "ON CONFLICT (rule_id) DO UPDATE SET "
                " warn_lo=:wlo, warn_hi=:whi, crit_lo=:clo, crit_hi=:chi, unit=:u, updated_at=now()"
            ),
            {"rid": rule_id, "cat": category, "met": metric,
             "wlo": warn_lo, "whi": warn_hi, "clo": crit_lo, "chi": crit_hi, "u": unit},
        )
        db.commit()
    except Exception as e:  # noqa: BLE001
        logger.debug("insert_rule 失败: %s", e)
        db.rollback()
    finally:
        db.close()


def update_rule_db(rule_id: str, category: str, metric: str,
                   warn_lo: float | None, warn_hi: float | None,
                   crit_lo: float | None, crit_hi: float | None,
                   unit: str = "") -> None:
    """更新告警规则记录 (best-effort)。"""
    db = _get_db()
    if db is None:
        return
    try:
        db.execute(
            text(
                "UPDATE alarm_rule SET category=:cat, metric=:met, warn_lo=:wlo, warn_hi=:whi, "
                " crit_lo=:clo, crit_hi=:chi, unit=:u, updated_at=now() WHERE rule_id=:rid"
            ),
            {"rid": rule_id, "cat": category, "met": metric,
             "wlo": warn_lo, "whi": warn_hi, "clo": crit_lo, "chi": crit_hi, "u": unit},
        )
        db.commit()
    except Exception as e:  # noqa: BLE001
        logger.debug("update_rule_db 失败: %s", e)
        db.rollback()
    finally:
        db.close()


def delete_rule_db(rule_id: str) -> None:
    """删除告警规则记录 (best-effort)。"""
    db = _get_db()
    if db is None:
        return
    try:
        db.execute(text("DELETE FROM alarm_rule WHERE rule_id = :rid"), {"rid": rule_id})
        db.commit()
    except Exception as e:  # noqa: BLE001
        logger.debug("delete_rule_db 失败: %s", e)
        db.rollback()
    finally:
        db.close()


# ---------------- 设备抑制 (alarm_suppressed_device) ----------------

def load_suppressed_set() -> set[str]:
    db = _get_db()
    if db is None:
        return set()
    try:
        rows = db.execute(text("SELECT device_id FROM alarm_suppressed_device")).fetchall()
        return {r[0] for r in rows}
    except Exception as e:  # noqa: BLE001
        logger.debug("load_suppressed_set 失败: %s", e)
        return set()
    finally:
        db.close()


def set_device_suppressed(device_id: str, suppressed: bool, reason: str = "") -> None:
    db = _get_db()
    if db is None:
        return
    try:
        if suppressed:
            db.execute(
                text(
                    "INSERT INTO alarm_suppressed_device (device_id, reason, created_at) "
                    "VALUES (:did, :rs, now()) "
                    "ON CONFLICT (device_id) DO UPDATE SET reason = :rs, created_at = now()"
                ),
                {"did": device_id, "rs": reason},
            )
        else:
            db.execute(
                text("DELETE FROM alarm_suppressed_device WHERE device_id = :did"),
                {"did": device_id},
            )
        db.commit()
    except Exception as e:  # noqa: BLE001
        logger.debug("set_device_suppressed 失败: %s", e)
        db.rollback()
    finally:
        db.close()


# ---------------- 活跃告警状态 (alarm_active_state) ----------------

def upsert_active_state(key: str, alarm: dict, conv_ts: float,
                        first_seen_ts: float, ack_state: str, status: str = "active") -> None:
    db = _get_db()
    if db is None:
        return
    try:
        db.execute(
            text(
                "INSERT INTO alarm_active_state "
                "(key, device_id, metric_name, level, alarm_json, conv_ts, "
                " first_seen_ts, ack_state, status, updated_at) "
                "VALUES (:k, :did, :mn, :lv, :aj, :ct, :fst, :ak, :st, now()) "
                "ON CONFLICT (key) DO UPDATE SET "
                " alarm_json = :aj, conv_ts = :ct, first_seen_ts = :fst, "
                " ack_state = :ak, status = :st, updated_at = now()"
            ),
            {
                "k": key,
                "did": alarm.get("device_id", ""),
                "mn": alarm.get("metric_name", ""),
                "lv": alarm.get("level", "warn"),
                "aj": json.dumps(alarm, ensure_ascii=False, default=str),
                "ct": conv_ts,
                "fst": first_seen_ts,
                "ak": ack_state,
                "st": status,
            },
        )
        db.commit()
    except Exception as e:  # noqa: BLE001
        logger.debug("upsert_active_state 失败: %s", e)
        db.rollback()
    finally:
        db.close()


def set_active_ack(key: str, ack_state: str) -> None:
    db = _get_db()
    if db is None:
        return
    try:
        db.execute(
            text(
                "UPDATE alarm_active_state SET ack_state = :ak, updated_at = now() "
                "WHERE key = :k"
            ),
            {"ak": ack_state, "k": key},
        )
        db.commit()
    except Exception as e:  # noqa: BLE001
        logger.debug("set_active_ack 失败: %s", e)
        db.rollback()
    finally:
        db.close()


def delete_active_state(key: str) -> None:
    db = _get_db()
    if db is None:
        return
    try:
        db.execute(text("DELETE FROM alarm_active_state WHERE key = :k"), {"k": key})
        db.commit()
    except Exception as e:  # noqa: BLE001
        logger.debug("delete_active_state 失败: %s", e)
        db.rollback()
    finally:
        db.close()


def load_active_states() -> list[dict]:
    """返回所有活跃告警状态行 (dict 形式), 供启动时 hydrate 与多 worker 读取。"""
    db = _get_db()
    if db is None:
        return []
    try:
        rows = db.execute(
            text(
                "SELECT key, device_id, metric_name, level, alarm_json, conv_ts, "
                " first_seen_ts, ack_state, status FROM alarm_active_state"
            )
        ).fetchall()
        out = []
        for r in rows:
            try:
                alarm = json.loads(r[4]) if r[4] else {}
            except Exception:  # noqa: BLE001
                alarm = {}
            out.append({
                "key": r[0],
                "device_id": r[1],
                "metric_name": r[2],
                "level": r[3],
                "alarm": alarm,
                "conv_ts": r[5],
                "first_seen_ts": r[6],
                "ack_state": r[7],
                "status": r[8],
            })
        return out
    except Exception as e:  # noqa: BLE001
        logger.debug("load_active_states 失败: %s", e)
        return []
    finally:
        db.close()
