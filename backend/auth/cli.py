"""
SQLite 模式用户管理 CLI。

使用：
  python -m auth.cli add-user alice -p secret123
  python -m auth.cli list
  python -m auth.cli passwd alice -p newpass
  python -m auth.cli delete alice
  python -m auth.cli hash secret123      # 生成 bcrypt hash 用于 file 模式 .env

注意：除 hash 子命令外，其他操作要求 settings.auth_backend == "sqlite"。
"""
from __future__ import annotations

import argparse
import getpass
import sys

from config import settings

from .backends import SqliteUserBackend, get_user_backend
from .password import hash_password


def _require_sqlite() -> SqliteUserBackend:
    if settings.auth_backend.lower() != "sqlite":
        sys.stderr.write(
            f"当前 AUTH_BACKEND={settings.auth_backend}，"
            f"用户管理 CLI 仅支持 sqlite 模式。\n"
            f"提示：file 模式请用 `python -m auth.cli hash <password>` "
            f"生成 bcrypt 写入 AUTH_USERS。\n"
        )
        sys.exit(2)
    backend = get_user_backend()
    assert isinstance(backend, SqliteUserBackend)
    return backend


def _read_password(args_pwd: str | None) -> str:
    if args_pwd:
        return args_pwd
    pwd = getpass.getpass("Password: ")
    pwd2 = getpass.getpass("Confirm:  ")
    if pwd != pwd2:
        sys.stderr.write("两次输入不一致\n")
        sys.exit(1)
    if len(pwd) < 6:
        sys.stderr.write("密码至少 6 位\n")
        sys.exit(1)
    return pwd


def cmd_add(args: argparse.Namespace) -> None:
    backend = _require_sqlite()
    pwd = _read_password(args.password)
    try:
        user = backend.add_user(args.username, pwd)
    except ValueError as e:
        sys.stderr.write(f"{e}\n")
        sys.exit(1)
    print(f"已添加用户 id={user.id} username={user.username}")


def cmd_list(_args: argparse.Namespace) -> None:
    backend = _require_sqlite()
    users = backend.list_users()
    if not users:
        print("（无用户）")
        return
    print(f"{'id':>4}  {'username':<20}  created_at")
    for u in users:
        ts = u.created_at.isoformat(sep=" ", timespec="seconds") if u.created_at else "-"
        print(f"{u.id:>4}  {u.username:<20}  {ts}")


def cmd_passwd(args: argparse.Namespace) -> None:
    backend = _require_sqlite()
    pwd = _read_password(args.password)
    if not backend.change_password(args.username, pwd):
        sys.stderr.write(f"用户不存在: {args.username}\n")
        sys.exit(1)
    print(f"已更新 {args.username} 的密码")


def cmd_delete(args: argparse.Namespace) -> None:
    backend = _require_sqlite()
    if not backend.delete_user(args.username):
        sys.stderr.write(f"用户不存在: {args.username}\n")
        sys.exit(1)
    print(f"已禁用 {args.username}")


def cmd_hash(args: argparse.Namespace) -> None:
    pwd = args.password or getpass.getpass("Password: ")
    print(hash_password(pwd))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="auth.cli", description="鉴权用户管理")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add-user", help="添加用户（sqlite）")
    p_add.add_argument("username")
    p_add.add_argument("-p", "--password", help="不传则交互式输入")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="列出用户（sqlite）")
    p_list.set_defaults(func=cmd_list)

    p_pwd = sub.add_parser("passwd", help="修改密码（sqlite）")
    p_pwd.add_argument("username")
    p_pwd.add_argument("-p", "--password")
    p_pwd.set_defaults(func=cmd_passwd)

    p_del = sub.add_parser("delete", help="禁用用户（sqlite，软删除）")
    p_del.add_argument("username")
    p_del.set_defaults(func=cmd_delete)

    p_hash = sub.add_parser("hash", help="生成 bcrypt hash（用于 file 模式 AUTH_USERS）")
    p_hash.add_argument("password", nargs="?")
    p_hash.set_defaults(func=cmd_hash)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
