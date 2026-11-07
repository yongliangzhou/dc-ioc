"""阶段四 · 多租户行级隔离测试 (SQLite + ORM hook)。"""
from concurrent.futures import ThreadPoolExecutor

from app.core.tenant_context import get_current_tenant, tenant_scope, without_tenant_filter
from app.db.session import install_tenant_filter
from app.models.ci_relation import CiRelation
from conftest import make_sqlite_sessionmaker


def _make_db():
    Session = make_sqlite_sessionmaker(CiRelation.__table__)
    install_tenant_filter(Session)
    db = Session()
    db.add_all([
        CiRelation(source_ci="a", target_ci="b", relation_type="powers", tenant_id=1),
        CiRelation(source_ci="c", target_ci="d", relation_type="powers", tenant_id=2),
        CiRelation(source_ci="e", target_ci="f", relation_type="cools", tenant_id=None),
    ])
    db.commit()
    return db


def test_no_context_no_filter():
    db = _make_db()
    try:
        assert get_current_tenant() is None
        assert db.query(CiRelation).count() == 3
    finally:
        db.close()


def test_tenant_a_cannot_see_tenant_b():
    db = _make_db()
    try:
        with tenant_scope(1):
            rows = db.query(CiRelation).all()
            assert len(rows) == 1 and rows[0].tenant_id == 1
        with tenant_scope(2):
            rows = db.query(CiRelation).all()
            assert len(rows) == 1 and rows[0].tenant_id == 2
    finally:
        db.close()


def test_without_tenant_filter_exemption():
    db = _make_db()
    try:
        with tenant_scope(1):
            with without_tenant_filter():
                assert get_current_tenant() is None
                assert db.query(CiRelation).count() == 3
            assert db.query(CiRelation).count() == 1  # 退出豁免后恢复过滤
    finally:
        db.close()


def test_context_does_not_leak_between_threads():
    def worker(tenant_id: int):
        with tenant_scope(tenant_id):
            return get_current_tenant()

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(worker, [1, 2, 1, 2]))
    assert results == [1, 2, 1, 2]
    assert get_current_tenant() is None
