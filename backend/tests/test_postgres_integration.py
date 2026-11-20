from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import Base


pytestmark = pytest.mark.skipif(
    not settings.database_url.startswith("postgresql"),
    reason="PostgreSQL integration requires a PostgreSQL DATABASE_URL",
)


def test_postgres_schema_and_concurrent_inserts():
    engine = create_engine(settings.database_url)
    with engine.begin() as connection:
        connection.execute(text("select 1"))

    Base.metadata.create_all(bind=engine)

    def insert_marker(index: int) -> int:
        session_local = sessionmaker(bind=engine)
        with session_local() as session:
            session.execute(
                text(
                    "insert into users "
                    "(email, password_hash, email_verified) "
                    "values (:email, :password_hash, false)"
                ),
                {
                    "email": f"concurrency-{index}@example.com",
                    "password_hash": "test-only",
                },
            )
            session.commit()
        return index

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(insert_marker, range(8)))

    assert results == list(range(8))
    with engine.connect() as connection:
        count = connection.scalar(
            text(
                "select count(*) from users "
                "where email like 'concurrency-%@example.com'"
            )
        )
    assert count == 8
    engine.dispose()
