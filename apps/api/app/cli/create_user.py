"""Create a user. The password is read from a hidden prompt, never from the command line.
Usage (from apps/api):  python -m app.cli.create_user <username> <analyst|auditor|admin>"""
import getpass
import sys

from app import security
from app.infrastructure.repositories.postgres_users import PostgresUserRepository


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[2] not in security.ROLES:
        sys.exit(f"usage: python -m app.cli.create_user <username> <{'|'.join(security.ROLES)}>")
    password = getpass.getpass("Password (min 12 chars): ")
    if len(password) < 12 or password != getpass.getpass("Repeat: "):
        sys.exit("Passwords differ or are shorter than 12 characters.")
    PostgresUserRepository().create(sys.argv[1], security.hash_password(password), sys.argv[2])
    print(f"created {sys.argv[1]} ({sys.argv[2]})")


if __name__ == "__main__":
    main()