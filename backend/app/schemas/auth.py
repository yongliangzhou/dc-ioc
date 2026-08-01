"""认证 DTO 层: 登录请求/响应、用户信息。"""
import json
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=4, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int                         # 秒
    user: "UserInfo"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str = ""
    email: Optional[str] = None
    department: str = ""
    is_superuser: bool = False
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


class UserCreate(BaseModel):
    """管理员创建用户。"""
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = ""
    email: Optional[str] = None
    department: str = ""
    role_names: list[str] = Field(default_factory=lambda: ["viewer"])


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=128)
