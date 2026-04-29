"""JWT 编码/解码工具。

Token payload 仅含必要字段：
  sub  - user.id（字符串）
  uname- 用户名（便于日志/审计）
  exp  - 过期时间戳
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt as pyjwt

from config import settings

_ALG = "HS256"


class TokenError(Exception):
    """JWT 无效 / 过期 / 缺字段时抛出。"""


def encode_token(user_id: str, username: str) -> str:
    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET 未配置，无法签发 token")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "uname": username,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=settings.jwt_expire_hours)).timestamp()),
    }
    return pyjwt.encode(payload, settings.jwt_secret, algorithm=_ALG)


def decode_token(token: str) -> tuple[str, str]:
    """返回 (user_id, username)；任何问题统一抛 TokenError。"""
    if not settings.jwt_secret:
        raise TokenError("JWT_SECRET 未配置")
    try:
        payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[_ALG])
    except pyjwt.ExpiredSignatureError as e:
        raise TokenError("token 已过期") from e
    except pyjwt.InvalidTokenError as e:
        raise TokenError(f"token 无效: {e}") from e

    sub = payload.get("sub")
    uname = payload.get("uname")
    if not sub or not uname:
        raise TokenError("token 缺少必要字段")
    return str(sub), str(uname)
