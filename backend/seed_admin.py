"""5.3.2 种子脚本(一): 初始化账号与角色。

- 幂等: 已存在的用户名/角色名跳过, 不覆盖密码。
- 创建: admin(超级用户) / operator(运维) / viewer(只读) 三账号 + 对应角色。
- 运行: python seed_admin.py
"""
from __future__ import annotations

import os
import sys

# 允许以脚本形式直接运行 (不依赖工作目录)
_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import Role, User

# (用户名, 显示名, 密码, 是否超级用户, 角色名)
SEED_USERS = [
    ("admin", "Administrator", "admin123", True, "admin"),
    ("operator", "运维操作员", "operator123", False, "operator"),
    ("viewer", "只读访客", "viewer123", False, "viewer"),
]

# 角色名 -> 权限串(JSON), 预留细粒度权限扩展
SEED_ROLES = {
    "admin": '["*:*"]',
    "operator": '["ticket:write","alarm:write","knowledge:write","inspection:write","drill:write","shift:write","risk:write","ops:write"]',
    "viewer": '["*:read"]',
}


def seed():
    db = SessionLocal()
    try:
        # 1. 角色
        role_cache = {}
        for name, perms in SEED_ROLES.items():
            role = db.query(Role).filter(Role.name == name).first()
            if role is None:
                role = Role(name=name, label=name, permissions=perms)
                db.add(role)
                db.commit()
                db.refresh(role)
                print(f"created role: {name}")
            else:
                role.permissions = perms
                db.commit()
            role_cache[name] = role

        # 2. 用户
        for username, disp, pwd, superuser, rolename in SEED_USERS:
            u = db.query(User).filter(User.username == username).first()
            if u is None:
                u = User(
                    username=username,
                    display_name=disp,
                    email=f"{username}@dcioc.local",
                    password_hash=hash_password(pwd),
                    is_active=True,
                    is_superuser=superuser,
                    roles=[role_cache[rolename]],
                )
                db.add(u)
                db.commit()
                db.refresh(u)
                print(f"created user: {username} (role={rolename})")
            else:
                print(f"skip existing user: {username}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("seed_admin done.")
