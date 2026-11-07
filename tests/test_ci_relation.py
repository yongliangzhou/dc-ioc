"""阶段二 · CMDB 关系层接口/CRUD/BFS 测试 (SQLite + 依赖覆盖)。"""
import pytest

from app.api.v1.endpoints import ci_relation as ci_ep
from app.crud import ci_relation as ci_crud
from app.models.ci_relation import CiRelation
from conftest import FakeUser, make_client, make_sqlite_sessionmaker

BASE = "/api/ops/ci-relations"


@pytest.fixture()
def db_factory(monkeypatch):
    SessionLocal = make_sqlite_sessionmaker(CiRelation.__table__)
    monkeypatch.setattr(ci_ep, "SessionLocal", SessionLocal)
    return SessionLocal


@pytest.fixture()
def client(db_factory):
    return make_client([(ci_ep.router, BASE)])


def _edge(src="equipment:1", tgt="cabinet:A01", rtype="powers", **extra):
    payload = {
        "source_ci": src,
        "target_ci": tgt,
        "source_name": "UPS-01",
        "target_name": "A01 机柜",
        "relation_type": rtype,
        "description": "A 路供电",
    }
    payload.update(extra)
    return payload


def test_create_and_list_roundtrip(client):
    r = client.post(BASE, json=_edge())
    assert r.status_code == 200, r.text
    assert r.json()["source_ci"] == "equipment:1"
    assert r.json()["created_by"] == "tester"
    rows = client.get(BASE).json()
    assert len(rows) == 1 and rows[0]["relation_type"] == "powers"


def test_duplicate_edge_returns_409(client):
    assert client.post(BASE, json=_edge()).status_code == 200
    dup = client.post(BASE, json=_edge())
    assert dup.status_code == 409


def test_self_loop_rejected_by_schema(client):
    r = client.post(BASE, json=_edge(src="equipment:1", tgt="equipment:1"))
    assert r.status_code == 422


def test_invalid_relation_type_rejected(client):
    r = client.post(BASE, json=_edge(rtype="unknown_type"))
    assert r.status_code == 422


def test_delete_and_404(client):
    rid = client.post(BASE, json=_edge()).json()["id"]
    assert client.delete(f"{BASE}/{rid}").json() == {"deleted": True, "id": rid}
    assert client.delete(f"{BASE}/{rid}").status_code == 404


def test_viewer_cannot_write(client):
    viewer = make_client([(ci_ep.router, BASE)], user=FakeUser(roles=("viewer",)))
    assert viewer.post(BASE, json=_edge()).status_code == 403
    assert viewer.delete(f"{BASE}/1").status_code == 403


def test_graph_nodes_and_edges(client):
    client.post(BASE, json=_edge())
    client.post(BASE, json=_edge(src="cabinet:A01", tgt="server:S1", rtype="hosts"))
    graph = client.get(f"{BASE}/graph").json()
    assert graph["total"] == 2
    assert graph["topology_source"] == "real"
    assert len(graph["nodes"]) == 3
    assert {e["type"] for e in graph["edges"]} == {"powers", "hosts"}


def test_impact_bfs_multihop(client):
    client.post(BASE, json=_edge())
    client.post(BASE, json=_edge(src="cabinet:A01", tgt="server:S1", rtype="hosts"))
    client.post(BASE, json=_edge(src="server:S1", tgt="app:trade", rtype="depends_on"))
    res = client.get(f"{BASE}/impact/equipment:1", params={"depth": 3}).json()
    assert res["topology_source"] == "real"
    assert res["total"] == 3
    by_ci = {i["ci"]: i for i in res["impacted"]}
    assert by_ci["cabinet:A01"]["hop"] == 1
    assert by_ci["server:S1"]["hop"] == 2
    assert by_ci["app:trade"]["hop"] == 3
    assert by_ci["app:trade"]["path"][0] == "equipment:1"


def test_impact_depth_cap_and_cycle(client):
    client.post(BASE, json=_edge(src="a", tgt="b"))
    client.post(BASE, json=_edge(src="b", tgt="a"))
    res = client.get(f"{BASE}/impact/a", params={"depth": 6}).json()
    assert res["has_cycle"] is True
    assert "a" not in [i["ci"] for i in res["impacted"]]


def test_impact_empty_graph_is_fallback(client):
    res = client.get(f"{BASE}/impact/unknown").json()
    assert res["topology_source"] == "fallback"
    assert res["impacted"] == [] and res["total"] == 0


def test_crud_conflict_error_on_unknown_type(db_factory):
    db = db_factory()
    try:
        with pytest.raises(ci_crud.CiConflictError):
            ci_crud.create_relation(db, {
                "source_ci": "a", "target_ci": "b", "relation_type": "bogus",
            })
    finally:
        db.close()
