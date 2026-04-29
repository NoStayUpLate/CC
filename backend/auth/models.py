"""鉴权相关 Pydantic 模型。"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    invite_code: str


class AuthConfig(BaseModel):
    """前端在登录页 mount 时拉取，决定是否显示注册入口。
    不暴露任何敏感信息。"""
    registration_enabled: bool


class User(BaseModel):
    """对外暴露的用户信息（不含 password_hash）。"""
    id: str                      # SQLite 模式为整数主键的字符串；File 模式为 username 本身
    username: str
    created_at: Optional[datetime] = None


class LoginResponse(BaseModel):
    user: User


class MeResponse(BaseModel):
    user: User
