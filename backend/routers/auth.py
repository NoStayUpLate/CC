"""
鉴权 API：登录 / 注册 / 登出 / 当前用户 / 公开配置。

Cookie 策略：
  - HTTP-only：JS 拿不到，抗 XSS
  - SameSite：默认 lax，跨站表单提交会被拒
  - Secure：上云 HTTPS 时设为 True（由 settings.cookie_secure 控制）

注册策略：
  - 仅在 AUTH_BACKEND=sqlite 时可用（file 模式无法运行时写）
  - 必须提供 REGISTRATION_CODE，与服务端 settings.registration_code 完全一致
  - REGISTRATION_CODE 为空 → 注册功能完全关闭，前端连入口都不显示
"""
import re

from fastapi import APIRouter, Depends, HTTPException, Response, status

from auth.backends import SqliteUserBackend, get_user_backend
from auth.dependencies import COOKIE_NAME, require_user
from auth.jwt import encode_token
from auth.models import (
    AuthConfig,
    LoginRequest,
    LoginResponse,
    MeResponse,
    RegisterRequest,
    User,
)
from config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

# 校验规则：用户名 3-32 位字母数字下划线，密码至少 6 位
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,32}$")
_MIN_PASSWORD_LEN = 6


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=settings.jwt_expire_hours * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


def _registration_enabled() -> bool:
    """注册同时满足：sqlite 模式 + 邀请码非空。"""
    return (
        settings.auth_backend.lower() == "sqlite"
        and bool(settings.registration_code)
    )


@router.get("/config", response_model=AuthConfig)
def public_config():
    """前端在登录页 mount 时拉取；用于决定是否展示「注册账号」入口。"""
    return AuthConfig(registration_enabled=_registration_enabled())


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, response: Response):
    backend = get_user_backend()
    user = backend.authenticate(req.username, req.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    token = encode_token(user.id, user.username)
    _set_auth_cookie(response, token)
    return LoginResponse(user=user)


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, response: Response):
    """
    注册新用户。成功后直接种 cookie 登录，前端不需要再调一次 /login。

    错误码语义：
      400 - 服务端关闭了注册（未配置邀请码 / 非 sqlite 模式）/ 用户名格式不符 / 密码太短
      403 - 邀请码错误
      409 - 用户名已存在
    """
    if not _registration_enabled():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="注册功能未启用",
        )

    if req.invite_code != settings.registration_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="邀请码无效",
        )

    if not _USERNAME_RE.match(req.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名仅支持 3-32 位字母、数字或下划线",
        )

    if len(req.password) < _MIN_PASSWORD_LEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"密码至少 {_MIN_PASSWORD_LEN} 位",
        )

    backend = get_user_backend()
    # 校验通过后理论上一定是 sqlite，断言保险
    assert isinstance(backend, SqliteUserBackend)

    try:
        user = backend.add_user(req.username, req.password)
    except ValueError as e:
        # add_user 在用户名重复时抛 ValueError
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    token = encode_token(user.id, user.username)
    _set_auth_cookie(response, token)
    return LoginResponse(user=user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(require_user)):
    return MeResponse(user=user)
