"""统一图形编辑入口 (graphic-config / refuel-records) 接口与 CRUD 测试。

策略:
- graphic_config 端点: crud 四个函数用内存假仓替换 —— 模型含 JSONB (PG 方言),
  SQLite 无法建表, 因此只测路由/鉴权/序列化, 不测 SQL。
- refuel_record: 模型为纯通用类型, 用 SQLite 内存库真实落库,
  端点模块的 SessionLocal 直接 monkeypatch 到测试库。
"""
import pytest

from app.api.v1.endpoints import graphic_editor as ge_ep
from app.crud import graphic_editor as ge_crud
from app.models.refuel_record import RefuelRecord
from conftest import FakeUser, make_client, make_sqlite_sessionmaker

CFG = "/api/ops/graphic-config/power-lv-schematic"
CFG_LIST = "/api/ops/graphic-config"
REFUEL = "/api/ops/refuel-records"

VALID_SCENE = {
    "nodes": [
        {"id": "QB", "label": "低压母联", "type": "断路器", "x": 100.0, "y": 50.0, "status": "分闸", "params": {}}
    ],
    "edges": [],
    "params": {"coldThreshold": "22"},
    "removed": ["DG"],
}


# ------------------------------------------------------------------ #
# fixtures
# ------------------------------------------------------------------ #
@pytest.fixture()
def store(monkeypatch):
    """graphic_config 内存假仓: 替换 ge_crud 的四个读写函数。"""
    data: dict = {}

    def fake_get(db, kind):
        if kind not in data:
            return None
        return {"kind": kind, "title": "", "payload": data[kind], "updatedBy": "tester", "updatedAt": None}

    def fake_save(db, kind, title, payload, user="system"):
        data[kind] = payload
        return {"kind": kind, "title": title or "", "payload": payload, "updatedBy": user, "updatedAt": None}

    def fake_delete(db, kind):
        return data.pop(kind, None) is not None

    def fake_list(db):
        return [
            {"kind": k, "title": "", "payload": v, "updatedBy": "tester", "updatedAt": None}
            for k, v in data.items()
        ]

    monkeypatch.setattr(ge_crud, "get_config", fake_get)
    monkeypatch.setattr(ge_crud, "save_config", fake_save)
    monkeypatch.setattr(ge_crud, "delete_config", fake_delete)
    monkeypatch.setattr(ge_crud, "list_configs", fake_list)
    return data


# SQLite 自增主键要求 INTEGER PRIMARY KEY; 模型的 BigInteger 主键 (BIGINT)
# 不会成为 rowid 别名, 故测试库用原生 DDL 建表 (列定义与模型一致)。
_REFUEL_DDL = """
CREATE TABLE IF NOT EXISTS refuel_record (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    no          VARCHAR(64)    NOT NULL UNIQUE,
    date        VARCHAR(32)    NOT NULL,
    tank        VARCHAR(64)    DEFAULT '',
    amount      DOUBLE PRECISION DEFAULT 0,
    before_pct  DOUBLE PRECISION,
    after_pct   DOUBLE PRECISION,
    vendor      VARCHAR(128)   DEFAULT '',
    grade       VARCHAR(64)    DEFAULT '',
    qc          VARCHAR(32)    DEFAULT '',
    operator    VARCHAR(64)    DEFAULT '',
    status      VARCHAR(32)    DEFAULT '已完成',
    note        TEXT,
    created_by  VARCHAR(64)    DEFAULT 'system',
    updated_by  VARCHAR(64)    DEFAULT 'system',
    created_at  TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP      DEFAULT CURRENT_TIMESTAMP
)
"""


@pytest.fixture()
def refuel_db(monkeypatch):
    """refuel_record SQLite 内存库: 替换端点模块命名空间里的 SessionLocal。"""
    SessionLocal = make_sqlite_sessionmaker(RefuelRecord.__table__, pre_ddl=_REFUEL_DDL)
    monkeypatch.setattr(ge_ep, "SessionLocal", SessionLocal)
    return SessionLocal


@pytest.fixture()
def client(store, refuel_db):
    return make_client([(ge_ep.router, "/api/ops"), (ge_ep.refuel_router, "/api/ops")])


# ------------------------------------------------------------------ #
# graphic-config 端点
# ------------------------------------------------------------------ #
def test_get_config_returns_empty_scene_when_missing(client):
    r = client.get(CFG)
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "power-lv-schematic"
    assert body["payload"]["nodes"] == []
    assert body["payload"]["removed"] == []
    assert body["payload"]["params"] == {}


def test_put_then_get_roundtrip(client, store):
    r = client.put(CFG, json={"title": "低压一次图", "payload": VALID_SCENE})
    assert r.status_code == 200
    assert "power-lv-schematic" in store

    r2 = client.get(CFG)
    assert r2.status_code == 200
    node = r2.json()["payload"]["nodes"][0]
    assert node["id"] == "QB" and node["label"] == "低压母联"
    assert r2.json()["payload"]["removed"] == ["DG"]


def test_put_rejected_for_role_without_permission(store, refuel_db):
    viewer = make_client(
        [(ge_ep.router, "/api/ops"), (ge_ep.refuel_router, "/api/ops")],
        user=FakeUser(roles=("viewer",)),
    )
    r = viewer.put(CFG, json={"payload": VALID_SCENE})
    assert r.status_code == 403


def test_delete_config_idempotent_flag(client, store):
    client.put(CFG, json={"payload": VALID_SCENE})
    assert client.delete(CFG).status_code == 200
    assert client.delete(CFG).json()["deleted"] is False


def test_list_configs(client, store):
    client.put(CFG, json={"payload": VALID_SCENE})
    r = client.get(CFG_LIST)
    assert r.status_code == 200
    assert any(c["kind"] == "power-lv-schematic" for c in r.json())


def test_put_invalid_payload_returns_422(client):
    # nodes 元素缺必填的 id → pydantic 422
    r = client.put(CFG, json={"payload": {"nodes": [{"label": "no-id"}]}})
    assert r.status_code == 422


# ------------------------------------------------------------------ #
# refuel-record 端点 (SQLite 真实落库)
# ------------------------------------------------------------------ #
def _refuel_body(no: str = "RF20260906-01") -> dict:
    return {
        "no": no,
        "date": "2026-09-06",
        "tank": "T-01",
        "amount": 12000,
        "before": 30.0,
        "after": 70.0,
        "vendor": "中石化 · 华南分公司",
        "grade": "0# 柴油 (国VI)",
        "qc": "合格",
        "operator": "张启明",
        "status": "已完成",
    }


def test_refuel_create_list_update_delete(client):
    r = client.post(REFUEL, json=_refuel_body())
    assert r.status_code == 200
    created = r.json()
    rid = created["id"]
    assert created["no"] == "RF20260906-01"

    # 编号唯一 → 409
    dup = client.post(REFUEL, json=_refuel_body())
    assert dup.status_code == 409

    # 列表
    items = client.get(REFUEL).json()["items"]
    assert any(i["no"] == "RF20260906-01" for i in items)

    # 更新: 驼峰 before/after → 列 before_pct/after_pct
    r4 = client.put(f"{REFUEL}/{rid}", json={"amount": 13500, "after": 75.0})
    assert r4.status_code == 200
    assert r4.json()["amount"] == 13500
    assert r4.json()["after"] == 75.0
    assert r4.json()["before"] == 30.0  # 未更新字段保持

    # 删除成功 + 再删 404
    assert client.delete(f"{REFUEL}/{rid}").json()["deleted"] is True
    assert client.delete(f"{REFUEL}/{rid}").status_code == 404


def test_refuel_update_missing_returns_404(client):
    assert client.put(f"{REFUEL}/999999", json={"amount": 1}).status_code == 404


def test_refuel_requires_write_role(refuel_db, store):
    viewer = make_client(
        [(ge_ep.router, "/api/ops"), (ge_ep.refuel_router, "/api/ops")],
        user=FakeUser(roles=("viewer",)),
    )
    assert viewer.post(REFUEL, json=_refuel_body()).status_code == 403
    assert viewer.delete(f"{REFUEL}/1").status_code == 403


# ------------------------------------------------------------------ #
# crud 层单测 (纯函数级, SQLite)
# ------------------------------------------------------------------ #
def test_refuel_crud_before_after_mapping(refuel_db):
    db = refuel_db()
    try:
        obj = ge_crud.create_refuel(
            db, {"no": "RF-X", "date": "2026-09-06", "amount": 100, "before": 10.0, "after": 20.0}
        )
        # to_dict 驼峰输出
        assert obj["before"] == 10.0 and obj["after"] == 20.0
        # 落库为下划线列
        row = ge_crud.get_refuel_by_no(db, "RF-X")
        assert row is not None and row.before_pct == 10.0 and row.after_pct == 20.0

        updated = ge_crud.update_refuel(db, obj["id"], {"after": 30.0})
        assert updated["after"] == 30.0
        # 不更新 created_by, 更新 updated_by
        assert updated["createdBy"] == "system" and updated["updatedBy"] == "system"

        assert ge_crud.delete_refuel(db, obj["id"]) is True
        assert ge_crud.delete_refuel(db, obj["id"]) is False
    finally:
        db.close()
