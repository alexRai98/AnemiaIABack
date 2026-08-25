from sqlalchemy import BigInteger, CheckConstraint, SmallInteger, String
from sqlalchemy.dialects.postgresql import CHAR

from anemiaiaback.capture.domain.entity.capture import Capture
from anemiaiaback.capture.infrastructure.storage.postgres_capture_repository import (
    SqlAlchemyCaptureRepository,
    build_session_factory,
)


class FakeSession:
    def __init__(self):
        self.added = None
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        pass

    def add(self, model):
        self.added = model

    def commit(self):
        self.committed = True

    def flush(self):
        self.added.id = 77

    def rollback(self):
        pass


def test_repository_maps_domain_capture_into_persistence_model():
    session = FakeSession()
    repository = SqlAlchemyCaptureRepository(lambda: session)
    capture = Capture(
        id=None,
        image="s3://ImagesProcesed/image.png",
        dni="12345678",
        age=42,
        gender="M",
    )
    saved = repository.add(capture)
    assert saved.id == 77
    assert session.committed
    assert session.added.dni == "12345678"
    assert session.added.image == "s3://ImagesProcesed/image.png"


def test_mapping_matches_existing_patients_table_exactly():
    from anemiaiaback.capture.infrastructure.storage.postgres_capture_repository import (
        CaptureModel,
    )

    table = CaptureModel.__table__
    assert table.name == "patients"
    assert list(table.columns.keys()) == ["id", "image", "dni", "age", "gender"]
    assert isinstance(table.c.id.type, BigInteger)
    assert table.c.id.identity is not None and table.c.id.identity.always
    assert isinstance(table.c.image.type, String) and table.c.image.type.length is None
    assert isinstance(table.c.dni.type, CHAR) and table.c.dni.type.length == 8
    assert isinstance(table.c.age.type, SmallInteger)
    assert isinstance(table.c.gender.type, CHAR) and table.c.gender.type.length == 1
    checks = {
        str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert checks == {
        "dni ~ '^[0-9]{8}$'",
        "age >= 0",
        "gender IN ('M', 'F')",
    }


def test_session_factory_is_safe_for_transaction_pooler(monkeypatch):
    captured = {}

    def fake_create_engine(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(
        "anemiaiaback.capture.infrastructure.storage.postgres_capture_repository.create_engine",
        fake_create_engine,
    )
    build_session_factory("postgresql+psycopg://user:pass@db.example.test/postgres")
    assert captured["connect_args"] == {"prepare_threshold": None}
    assert captured["pool_pre_ping"] is True
