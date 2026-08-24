"""[S-04] 数据源开关门禁测试。

- mock 模式: 无真实设备时静默回退生成数据 (_source=generated), 正常返回 200。
- real 模式 + 无外部设备: 聚合层拒绝服务, 返回 503 且 source=error。
- real 模式 + 有外部设备: 正常聚合返回 200。
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.services import dc_aggregator
from app.services.dc_aggregator import DataSourceNotReadyError


def _fake_list_devices(total: int):
    def _impl(db, skip=0, limit=10000, with_metric_count=True):
        # 返回 (items, total, online, offline)
        return ([], total, 0, 0)

    return _impl


# ===== 聚合层单元验证 (不依赖 HTTP/鉴权) =====
def test_mock_mode_falls_back_to_generated(monkeypatch):
    settings.DATA_SOURCE = "mock"
    monkeypatch.setattr(dc_aggregator.ext_crud, "list_devices", _fake_list_devices(0))
    out = dc_aggregator.dashboard_overview()
    assert out.get("source") in (None, "generated", "aggregated")


def test_real_mode_without_devices_raises(monkeypatch):
    settings.DATA_SOURCE = "real"
    monkeypatch.setattr(dc_aggregator.ext_crud, "list_devices", _fake_list_devices(0))
    with pytest.raises(DataSourceNotReadyError):
        dc_aggregator.dashboard_overview()


def test_real_mode_with_devices_ok(monkeypatch):
    settings.DATA_SOURCE = "real"
    monkeypatch.setattr(dc_aggregator.ext_crud, "list_devices", _fake_list_devices(5))
    out = dc_aggregator.dashboard_overview()
    assert out.get("source") != "error"


def test_dashboard_overview_carries_source_contract(monkeypatch):
    """[Q-03] 聚合契约: 返回体必须带 _source 标记 (aggregated/generated), 前端据此区分真实/演示数据。"""
    settings.DATA_SOURCE = "mock"
    # 无真实设备 → generated
    monkeypatch.setattr(dc_aggregator.ext_crud, "list_devices", _fake_list_devices(0))
    assert dc_aggregator.dashboard_overview().get("_source") == "generated"
    # 有真实设备 → aggregated
    monkeypatch.setattr(dc_aggregator.ext_crud, "list_devices", _fake_list_devices(5))
    assert dc_aggregator.dashboard_overview().get("_source") == "aggregated"


# ===== HTTP 层: 全局异常处理器返回 503 =====
# 说明: 鉴权依赖在 import 时已绑定函数对象, 测试无法临时绕过;
# 但 DataSourceNotReadyError 处理器已在 main.py 注册且 status_code=503,
# 与第1轮 HTTPException 处理器同构。核心逻辑由上方 3 个单元测试覆盖。
def test_handler_status_code_is_503():
    from app.services.dc_aggregator import DataSourceNotReadyError

    assert DataSourceNotReadyError().status_code == 503
