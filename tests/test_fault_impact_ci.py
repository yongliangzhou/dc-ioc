"""阶段二 · 影响分析叠加真实关系链的回归测试。

断言: 未建关系时输出与改造前兼容 (legacy + 空 realRelations + 旧字段齐全);
      有关系时标记 real+legacy 并带出关系链, 不破坏既有 summary 结构。
"""
from app.crud import ci_relation as ci_crud
from app.crud import fault_impact as fi_crud

SCOPE = {"power": True, "cool": True, "network": True, "business": True}


def test_no_real_relations_keeps_legacy_output(monkeypatch):
    monkeypatch.setattr(ci_crud, "relations_for_faults", lambda _ids, _depth=3: [])
    out = fi_crud.analyze([], SCOPE)
    assert out["topologySource"] == "legacy"
    assert out["realRelations"] == []
    assert out["summary"]["realRelationCount"] == 0
    for key in ("faultIds", "generatedAt", "nodes", "edges", "affectedIds",
                "summary", "businesses", "suggestion", "mitigations"):
        assert key in out


def test_real_relations_are_exposed(monkeypatch):
    chain = [
        {"faultId": 1, "sourceCi": "equipment:1", "ci": "cabinet:A01",
         "name": "A01", "hop": 1, "via": "powers", "path": ["equipment:1", "cabinet:A01"]},
    ]
    monkeypatch.setattr(ci_crud, "relations_for_faults", lambda _ids, _depth=3: chain)
    out = fi_crud.analyze([1], SCOPE)
    assert out["topologySource"] == "real+legacy"
    assert out["realRelations"] == chain
    assert out["summary"]["realRelationCount"] == 1
    assert "severity" in out["summary"] and "affectedCount" in out["summary"]


def test_relation_source_failure_falls_back_to_legacy(monkeypatch):
    """关系库不可达时 relations_for_faults 自身降级为空, analyze 输出 legacy。"""
    from app.db import session as db_session

    def broken():
        raise RuntimeError("db down")

    monkeypatch.setattr(db_session, "SessionLocal", broken)
    assert ci_crud.relations_for_faults([1]) == []
    out = fi_crud.analyze([1], SCOPE)
    assert out["topologySource"] == "legacy"
    assert out["realRelations"] == []
