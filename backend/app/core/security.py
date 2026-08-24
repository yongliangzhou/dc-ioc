"""JWT 认证与安全工具。

提供:
- 密码哈希 (passlib bcrypt)
- JWT 令牌生成 / 校验 (python-jose)
- 用户会话管理
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ---- 密码上下文 ----
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS384"  # 与 Java 后端 (io.jsonwebtoken JJWT) 默认算法保持一致, 以便代理透传的 JWT 可被互信解析
SUPPORTED_ALGORITHMS = ["HS384", "HS256"]


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """签发 JWT access token。"""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode = {"sub": subject, "exp": expire, "iat": datetime.now(timezone.utc), "type": "access"}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """签发 refresh token (有效期 7 天)。"""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"sub": subject, "exp": expire, "iat": datetime.now(timezone.utc), "type": "refresh"}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """解码 JWT，失败返回 None。"""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=SUPPORTED_ALGORITHMS)
        return payload
    except JWTError:
        return None
