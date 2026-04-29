"""bcrypt 密码哈希工具（直接用 bcrypt 库，不经 passlib）。

bcrypt 5.x 移除了 passlib 依赖的内部属性，passlib 暂未适配，
直接用 bcrypt 既简洁又长期可维护。

bcrypt 算法本身有 72 字节硬上限，超出部分被忽略 —— 这里显式截断
让行为对调用方明确（避免 bcrypt 5.x 在超长输入时直接抛 ValueError）。
"""
import bcrypt

_BCRYPT_MAX_BYTES = 72


def _truncate(plain: str) -> bytes:
    return plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_truncate(plain), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(_truncate(plain), hashed.encode("ascii"))
    except (ValueError, TypeError):
        return False
