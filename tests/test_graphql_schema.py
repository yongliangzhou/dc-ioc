"""阶段四 · GraphQL 只读 Schema 冒烟 (strawberry 为可选依赖, 未安装时跳过)。"""
import pytest

strawberry = pytest.importorskip("strawberry")

from app.graphql import schema as schema_module  # noqa: E402


def test_schema_available_when_dependency_installed():
    schema = schema_module.schema
    assert schema is not None
    sdl = schema.as_str()
    for field in ("cis", "relations", "impact", "ipSubnets", "equipment"):
        assert field in sdl


def test_query_degrades_to_empty_without_database():
    """数据库不可达时 resolver 降级为空列表, 不把异常泄漏为 GraphQL errors。"""
    schema = schema_module.schema
    result = schema.execute_sync("{ cis(limit: 2) { id name } ipSubnets(limit: 2) { cidr } }")
    assert result.errors is None or len(result.errors) == 0
    assert result.data is not None
    assert isinstance(result.data["cis"], list)
    assert isinstance(result.data["ipSubnets"], list)


def test_limit_is_capped():
    assert schema_module._limit(9999) == 200
    assert schema_module._limit(0) == 1
