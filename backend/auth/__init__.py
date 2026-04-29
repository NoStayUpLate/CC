"""
鉴权子系统：可插拔 UserBackend + JWT Cookie 认证。

模块入口暴露最常用的两个对象：
  - get_user_backend(): 根据 settings.auth_backend 返回单例 backend
  - require_user:       FastAPI Dependency，未登录抛 401，登录返回 User
"""
from .backends import get_user_backend
from .dependencies import require_user
from .models import User

__all__ = ["get_user_backend", "require_user", "User"]
