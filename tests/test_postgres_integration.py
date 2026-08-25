import os
from uuid import uuid4

import pytest

from anemiaiaback.capture.infrastructure.storage.postgres_capture_repository import (
    CaptureModel,
    SqlAlchemyCaptureRepository,
    build_session_factory,
)
from anemiaiaback.capture.domain.entity.capture import Capture


@pytest.mark.integration
def test_postgres_capture_round_trip():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    # Once explicitly configured, any connection/schema failure is a real test
    # failure. Only absence of TEST_DATABASE_URL skips this integration test.
    factory = build_session_factory(database_url)

    capture = Capture(
        id=None,
        image=f"s3://test-bucket/integration-{uuid4()}.png",
        dni="12345678",
        age=36,
        gender="F",
    )
    repository = SqlAlchemyCaptureRepository(factory)
    saved = None
    try:
        saved = repository.add(capture)
        with factory() as session:
            stored = session.get(CaptureModel, saved.id) if saved is not None else None
            assert stored is not None
            assert (stored.dni, stored.gender, stored.age, stored.image) == (
                capture.dni, capture.gender, capture.age, capture.image
            )
    finally:
        with factory() as session:
            stored = session.get(CaptureModel, saved.id)
            if stored is not None:
                session.delete(stored)
                session.commit()
