"""Create or promote an admin user.

Usage: python -m app.create_admin admin@example.com "a-strong-password"
"""

import sys

from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.security import hash_password


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("Usage: python -m app.create_admin <email> <password>")
    email, password = sys.argv[1].lower(), sys.argv[2]
    if len(password) < 8:
        sys.exit("Password must have at least 8 characters")

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, hashed_password=hash_password(password))
            db.add(user)
        user.is_admin = True
        db.commit()
    print(f"{email} is now an admin")


if __name__ == "__main__":
    main()
