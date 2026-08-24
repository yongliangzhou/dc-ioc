"""用户与角色模型。"""
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Table, Column, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

# 用户-角色多对多关联表
user_role = Table(
    "user_role", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), default="")
    email: Mapped[str | None] = mapped_column(String(128), default=None)
    phone: Mapped[str | None] = mapped_column(String(32), default=None)
    department: Mapped[str] = mapped_column(String(64), default="")          # 部门/班组
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    roles: Mapped[list["Role"]] = relationship("Role", secondary=user_role, back_populates="users", lazy="selectin")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)      # admin/operator/viewer
    label: Mapped[str] = mapped_column(String(32), default="")                       # 展示名称
    permissions: Mapped[str | None] = mapped_column(String(1024), default=None)  # JSON 权限列表
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    users: Mapped[list["User"]] = relationship("User", secondary=user_role, back_populates="roles", lazy="selectin")
