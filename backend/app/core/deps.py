"""认证依赖注入: get_current_user / require_permission / require_role。

用法:
- 需要登录: Depends(get_current_user)
- 需要特定角色: Depends(require_role("admin"))
- 需要特定权限: Depends(require_permission("alarm:write"))
"""
import json
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models.user import User

security_scheme = HTTPBearer(auto_error=False)


def get_db():
    """获取数据库会话（用于依赖注入）。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """从 Bearer token 解析当前用户，未登录或 token 无效返回 401。"""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供认证令牌")

    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="认证令牌无效或已过期")
    # 兼容代理透传：Java 端 JWT 未必带 type 字段，仅当明确为 refresh 时拒绝
    if payload.get("type") == "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌类型无效 (需使用 access token)")

    username = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌格式错误")

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    return user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """可选认证：已登录返回 User，未登录返回 None（不拦截）。"""
    if credentials is None:
        return None
    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        return None
    username = payload.get("sub")
    if username is None:
        return None
    return db.query(User).filter(User.username == username, User.is_active.is_(True)).first()


class RoleChecker:
    """需要特定角色的依赖。"""
    def __init__(self, *roles: str):
        self.required_roles = set(roles)

    def __call__(self, user: User = Depends(get_current_user)):
        user_roles = {r.name for r in (user.roles or [])}
        if user.is_superuser:
            return user
        if self.required_roles & user_roles:
            return user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")

    def __repr__(self):
        return f"RoleChecker({','.join(self.required_roles)})"


class PermissionChecker:
    """需要特定权限的依赖。"""
    def __init__(self, *permissions: str):
        self.required = set(permissions)

    def __call__(self, user: User = Depends(get_current_user)):
        if user.is_superuser:
            return user
        user_perms = set()
        for role in (user.roles or []):
            try:
                perms = json.loads(role.permissions or "[]")
                user_perms.update(perms)
            except (json.JSONDecodeError, TypeError):
                pass
        if self.required & user_perms:
            return user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")


require_role = RoleChecker
require_permission = PermissionChecker
