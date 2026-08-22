"""CLI entry point: ``python -m app.seeds.seed``.

Ensures tables exist (convenience for demos) then loads demo data and prints the
demo credentials for the evaluator.
"""
from __future__ import annotations

from app.core.database import Base, SessionLocal, engine
from app import models  # noqa: F401  ensures all tables are registered on Base
from app.seeds.seed_data import seed
from app.utils.logging import configure_logging


def main() -> None:
    configure_logging("INFO")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        creds = seed(db)
    finally:
        db.close()

    print("\n" + "=" * 60)
    print(" RouteFlow demo data ready. Login credentials:")
    print("=" * 60)
    print(f"  Admin    : {creds.admin}")
    print(f"  Customer : {creds.customer}")
    print(f"  Agent    : {creds.agent}")
    print(f"  Password : {creds.password}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
