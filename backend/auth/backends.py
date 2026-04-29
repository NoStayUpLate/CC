"""
可插拔的 UserBackend：File 模式 / SQLite 模式。

切换由 settings.auth_backend 控制（"file" | "sqlite"）。
两个 backend 都不依赖 ORM，sqlite 直接用 stdlib sqlite3，避免引入 SQLAlchemy。
"""
from __future__ import annotations

import sqlite3
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from functools import lru_cache
from typing import Optional

from config import settings

from .models import User
from .password import verify_password, hash_password


class UserBackend(ABC):
    """统一抽象。authenticate 是 hot path，其他方法供 CLI 调用。"""

    @abstractmethod
    def authenticate(self, username: str, password: str) -> Optional[User]: ...

    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[User]: ...

    # 以下 CRUD 在 File 模式下可抛 NotImplementedError
    def add_user(self, username: str, password: str) -> User:
        raise NotImplementedError

    def list_users(self) -> list[User]:
        raise NotImplementedError

    def delete_user(self, username: str) -> bool:
        raise NotImplementedError

    def change_password(self, username: str, new_password: str) -> bool:
        raise NotImplementedError


# ─────────────────────────────────────────────────────────────
# FileUserBackend
# 配置示例（.env）：
#   AUTH_USERS=admin:$2b$12$xxx;reader:$2b$12$yyy
# 用 ';' 分隔多用户，用 ':' 分隔 username 与 bcrypt hash。
# ─────────────────────────────────────────────────────────────
class FileUserBackend(UserBackend):
    def __init__(self, raw: str):
        self._users: dict[str, str] = {}    # username -> password_hash
        for entry in (raw or "").split(";"):
            entry = entry.strip()
            if not entry or ":" not in entry:
                continue
            username, _, pwd_hash = entry.partition(":")
            username = username.strip()
            pwd_hash = pwd_hash.strip()
            if username and pwd_hash:
                self._users[username] = pwd_hash

    def authenticate(self, username: str, password: str) -> Optional[User]:
        h = self._users.get(username)
        if not h or not verify_password(password, h):
            return None
        return User(id=username, username=username)

    def get_by_id(self, user_id: str) -> Optional[User]:
        # File 模式 user_id 即 username
        if user_id in self._users:
            return User(id=user_id, username=user_id)
        return None


# ─────────────────────────────────────────────────────────────
# SqliteUserBackend
# 表结构：
#   users(id INTEGER PK, username TEXT UNIQUE, password_hash TEXT,
#         created_at TEXT, is_active INTEGER DEFAULT 1)
# 用 stdlib sqlite3，启用 WAL 提升并发读，加 thread lock 保护写。
# ─────────────────────────────────────────────────────────────
_SQLITE_DDL = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    is_active     INTEGER NOT NULL DEFAULT 1
)
"""


class SqliteUserBackend(UserBackend):
    def __init__(self, path: str):
        self._path = path
        self._lock = threading.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, check_same_thread=False, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(_SQLITE_DDL)

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> User:
        ts = row["created_at"]
        try:
            ca = datetime.fromisoformat(ts) if ts else None
        except ValueError:
            ca = None
        return User(id=str(row["id"]), username=row["username"], created_at=ca)

    def authenticate(self, username: str, password: str) -> Optional[User]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, username, password_hash, created_at, is_active "
                "FROM users WHERE username = ? AND is_active = 1",
                (username,),
            ).fetchone()
        if not row or not verify_password(password, row["password_hash"]):
            return None
        return self._row_to_user(row)

    def get_by_id(self, user_id: str) -> Optional[User]:
        try:
            uid = int(user_id)
        except (TypeError, ValueError):
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, username, password_hash, created_at, is_active "
                "FROM users WHERE id = ? AND is_active = 1",
                (uid,),
            ).fetchone()
        return self._row_to_user(row) if row else None

    def add_user(self, username: str, password: str) -> User:
        with self._lock, self._connect() as conn:
            try:
                cur = conn.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, hash_password(password)),
                )
            except sqlite3.IntegrityError as e:
                raise ValueError(f"用户已存在: {username}") from e
            uid = cur.lastrowid
            row = conn.execute(
                "SELECT id, username, password_hash, created_at, is_active "
                "FROM users WHERE id = ?",
                (uid,),
            ).fetchone()
        return self._row_to_user(row)

    def list_users(self) -> list[User]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, username, password_hash, created_at, is_active "
                "FROM users WHERE is_active = 1 ORDER BY id"
            ).fetchall()
        return [self._row_to_user(r) for r in rows]

    def delete_user(self, username: str) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "UPDATE users SET is_active = 0 WHERE username = ? AND is_active = 1",
                (username,),
            )
        return cur.rowcount > 0

    def change_password(self, username: str, new_password: str) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "UPDATE users SET password_hash = ? "
                "WHERE username = ? AND is_active = 1",
                (hash_password(new_password), username),
            )
        return cur.rowcount > 0


# ─────────────────────────────────────────────────────────────
# Backend 单例工厂
# ─────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_user_backend() -> UserBackend:
    mode = (settings.auth_backend or "file").lower()
    if mode == "sqlite":
        return SqliteUserBackend(settings.auth_sqlite_path)
    if mode == "file":
        return FileUserBackend(settings.auth_users)
    raise RuntimeError(f"未知 AUTH_BACKEND: {mode}（仅支持 file / sqlite）")
