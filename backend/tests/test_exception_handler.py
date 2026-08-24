"""S-03 全局异常处理单元测试: 未捕获异常不得泄露堆栈。"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from app.main import app as real_app


def _build_app() -> FastAPI:
    """复用 main.py 已注册的异常处理器, 附加一个必然抛异常的探针路由。"""
    # real_app 已在模块加载时注册好 exception_handler, 直接加路由即可
    @real_app.get("/__probe_unhandled")
    def _boom(_: Request):
        raise RuntimeError("SECRET_INTERNAL_DETAIL_12345")

    @real_app.get("/__probe_http")
    def _http(_: Request):
        raise HTTPException(status_code=418, detail="teapot says no")

    return real_app


_probe_app = _build_app()
# 生产语义: 关闭 debug 后 ServerErrorMiddleware 才会把未捕获异常交给注册的
# Exception 处理器, 而非直接返回明文堆栈。
_probe_app.debug = False
# raise_server_exceptions=False: 让未捕获异常的响应体回到测试侧, 以便断言不泄露堆栈
_client = TestClient(_probe_app, raise_server_exceptions=False)


def test_unhandled_exception_returns_500_without_stack():
    resp = _client.get("/__probe_unhandled")
    assert resp.status_code == 500
    body = resp.text
    # 不得包含内部细节/堆栈
    assert "SECRET_INTERNAL_DETAIL_12345" not in body
    assert "Traceback" not in body
    assert "traceback" not in body
    data = resp.json()
    assert data["code"] == 500
    assert "内部错误" in data["message"]


def test_http_exception_passthrough():
    resp = _client.get("/__probe_http")
    assert resp.status_code == 418
    data = resp.json()
    assert data["code"] == 418
    assert data["message"] == "teapot says no"
