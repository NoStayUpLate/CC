"""FastAPI Dependency：从 cookie 读取 JWT，校验后返回 User。"""
from fastapi import Cookie, HTTPException, status

from .backends import get_user_backend
from .jwt import TokenError, decode_token
from .models import User

COOKIE_NAME = "access_token"


def require_user(access_token: str | None = Cookie(default=None)) -> User:
    """
    业务路由的全局守卫。无 cookie / token 无效 / 用户不存在 → 401。
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
            headers={"WWW-Authenticate": "Cookie"},
        )

    try:
        user_id, _username = decode_token(access_token)
    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Cookie"},
        )

    backend = get_user_backend()
    user = backend.get_by_id(user_id)
    if user is None:
        # token 合法但 backend 已删/禁用该用户
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用",
            headers={"WWW-Authenticate": "Cookie"},
        )
    return user
