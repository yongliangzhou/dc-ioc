"""认证 API: 登录 / 刷新令牌 / 当前用户 / 修改密码。

默认管理员账号 (首次启动时通过启动脚本或手动创建):
  username: admin   password: admin123
角色体系:
  - admin:    超级管理员，所有权限
  - operator: 运维操作员，可读写大部分业务
  - viewer:   只读用户，仅查看驾驶舱与报表
"""
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db, require_role
from app.core.ratelimit import login_rate_limit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User, Role
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserInfo,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_to_info(user: User) -> UserInfo:
    """User ORM -> UserInfo DTO。"""
    perms: list[str] = []
    roles_list: list[str] = []
    for role in (user.roles or []):
        roles_list.append(role.name)
        try:
            perms.extend(json.loads(role.permissions or "[]"))
        except (json.JSONDecodeError, TypeError):
            pass
    return UserInfo(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        email=user.email,
        department=user.department,
        is_superuser=user.is_superuser,
        roles=list(set(roles_list)),
        permissions=list(set(perms)),
    )


# ------------------------------------------------------------------ 登录
@router.post("/login", response_model=TokenResponse, summary="用户登录", dependencies=[Depends(login_rate_limit)])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已禁用")

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(subject=user.username)
    refresh_token = create_refresh_token(subject=user.username)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=_user_to_info(user),
    )


# ------------------------------------------------------------------ 刷新令牌
@router.post("/refresh", response_model=TokenResponse, summary="刷新 access token")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    token_data = decode_token(payload.refresh_token)
    if token_data is None or token_data.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新令牌")

    username = token_data.get("sub")
    user = db.query(User).filter(User.username == username, User.is_active.is_(True)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")

    access_token = create_access_token(subject=user.username)
    refresh_token = create_refresh_token(subject=user.username)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=_user_to_info(user),
    )


# ------------------------------------------------------------------ 当前用户
@router.get("/me", response_model=UserInfo, summary="获取当前用户信息")
def me(user: User = Depends(get_current_user)):
    return _user_to_info(user)


# ------------------------------------------------------------------ 修改密码
@router.post("/change-password", summary="修改密码")
def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="原密码错误")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "密码修改成功"}


# ------------------------------------------------------------------ 管理员: 创建用户
@router.post("/users", response_model=UserInfo, summary="[管理员] 创建用户")
def create_user(
    payload: UserCreate,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name or payload.username,
        email=payload.email,
        department=payload.department,
    )
    # 分配角色
    roles = db.query(Role).filter(Role.name.in_(payload.role_names)).all()
    user.roles = roles
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_to_info(user)


# ------------------------------------------------------------------ 管理员: 用户列表
@router.get("/users", summary="[管理员] 用户列表")
def list_users(
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    total = db.query(User).count()
    users = db.query(User).offset(skip).limit(limit).all()
    return {"total": total, "items": [_user_to_info(u) for u in users]}


# ------------------------------------------------------------------ 角色列表
@router.get("/roles", summary="角色列表")
def list_roles(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = db.query(Role).all()
    return [{"name": r.name, "label": r.label, "permissions": json.loads(r.permissions or "[]")} for r in roles]
