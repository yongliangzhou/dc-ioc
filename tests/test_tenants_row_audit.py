"""tenants / row-audit 接口冒烟测试。

- tenants: 模型为纯通用类型, SQLite 内存库真实落库; 端点用 Depends(get_db)
  (来自 app.db.session), 通过 app.dependency_overrides 覆盖原函数对象。
- row-audit: 模型含 JSONB (SQLite 不兼容), crud 函数替换为内存假体,
  端点内真实 SessionLocal 只创建会话不执行查询, 不会触达 Postgres。
"""
import pytest

from app.api.v1.endpoints import row_audit as ra_ep
from app.api.v1.endpoints import tenant as tenant_ep
from app.db.session import get_db as session_get_db
from app.models.tenant import Tenant
from conftest import FakeUser, make_client, make_sqlite_sessionmaker

TENANTS = "/api/ops/tenants"
ROW_AUDIT = "/api/row-audit"


# ------------------------------------------------------------------ #
# tenants (SQLite 真实落库)
# ------------------------------------------------------------------ #
@pytest.fixture()
def tenant_client():
    SessionLocal = make_sqlite_sessionmaker(Tenant.__table__)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    return make_client([(tenant_ep.router, "/api/ops/tenants")], extra_overrides={session_get_db: override_get_db})


def test_tenant_create_list_update_delete(tenant_client):
    # 创建 (驼峰字段与前端契约一致)
    r = tenant_client.post(TENANTS, json={"name": "ACME 云计算", "code": "TH-01", "contact": "李雷"})
    assert r.status_code == 200
    created = r.json()
    tid = created.get("id")
    assert tid is not None
    assert created["name"] == "ACME 云计算"

    # 列表 + 总数
    lst = tenant_client.get(TENANTS).json()
    assert lst["total"] == 1
    assert lst["tenants"][0]["code"] == "TH-01"

    # 关键字过滤 (命中)
    lst2 = tenant_client.get(TENANTS, params={"kw": "ACME"}).json()
    assert lst2["total"] == 1
    # 关键字过滤 (不命中)
    lst3 = tenant_client.get(TENANTS, params={"kw": "不存在"}).json()
    assert lst3["total"] == 0

    # 更新
    r4 = tenant_client.put(f"{TENANTS}/{tid}", json={"name": "ACME-2"})
    assert r4.status_code == 200
    assert r4.json()["name"] == "ACME-2"

    # 详情
    assert tenant_client.get(f"{TENANTS}/{tid}").json()["name"] == "ACME-2"

    # 删除 (204) + 再删/再查 404
    assert tenant_client.delete(f"{TENANTS}/{tid}").status_code == 204
    assert tenant_client.delete(f"{TENANTS}/{tid}").status_code == 404
    assert tenant_client.get(f"{TENANTS}/{tid}").status_code == 404


def test_tenant_stats_endpoint(tenant_client):
    tenant_client.post(TENANTS, json={"name": "S1", "status": "active"})
    r = tenant_client.get(f"{TENANTS}/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1 and body["active"] == 1


def test_tenant_get_missing_returns_404(tenant_client):
    assert tenant_client.get(f"{TENANTS}/999").status_code == 404


def test_tenant_write_requires_role():
    no_role = make_client(
        [(tenant_ep.router, "/api/ops/tenants")], user=FakeUser(roles=("viewer",))
    )
    assert no_role.post(TENANTS, json={"name": "X"}).status_code == 403
    assert no_role.put(f"{TENANTS}/1", json={"name": "Y"}).status_code == 403
    assert no_role.delete(f"{TENANTS}/1").status_code == 403


# ------------------------------------------------------------------ #
# row-audit (crud 假体, 只测路由/鉴权/序列化)
# ------------------------------------------------------------------ #
@pytest.fixture()
def ra_client(monkeypatch):
    def fake_logs(db=None, skip=0, limit=50, table_name=None, action=None, changed_by=None, start=None, end=None):
        return {
            "items": [
                {
                    "id": 1,
                    "ts": "2026-09-06T00:00:00+00:00",
                    "table_name": "users",
                    "row_id": "1",
                    "action": "U",
                    "old_val": {"username": "a"},
                    "new_val": {"username": "b"},
                    "changed_by": "tester",
                    "app_name": "pytest",
                }
            ],
            "total": 1,
            "page": 1,
            "page_size": limit,
        }

    def fake_stats(db=None):
        return {
            "total": 1,
            "by_table": [{"table_name": "users", "count": 1}],
            "by_action": [{"action": "U", "count": 1}],
        }

    monkeypatch.setattr(ra_ep, "get_row_audit_logs", fake_logs)
    monkeypatch.setattr(ra_ep, "get_row_audit_stats", fake_stats)
    return make_client([(ra_ep.router, ROW_AUDIT)])


def test_row_audit_list(ra_client):
    r = ra_client.get(ROW_AUDIT, params={"page": 1, "page_size": 50})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["table_name"] == "users"
    assert body["items"][0]["action"] == "U"


def test_row_audit_stats(ra_client):
    r = ra_client.get(f"{ROW_AUDIT}/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["by_table"][0]["table_name"] == "users"
    assert body["by_action"][0]["action"] == "U"
