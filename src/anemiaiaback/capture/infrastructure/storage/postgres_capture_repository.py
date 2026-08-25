from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Identity,
    SmallInteger,
    String,
    create_engine,
)
from sqlalchemy.dialects.postgresql import CHAR
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from anemiaiaback.capture.domain.entity.capture import Capture
from anemiaiaback.capture.domain.errors import PersistenceError


class Base(DeclarativeBase):
    pass


class CaptureModel(Base):
    __tablename__ = "patients"
    __table_args__ = (
        CheckConstraint("dni ~ '^[0-9]{8}$'", name="patients_dni_digits"),
        CheckConstraint("age >= 0", name="patients_age_nonnegative"),
        CheckConstraint("gender IN ('M', 'F')", name="patients_gender_values"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    image: Mapped[str] = mapped_column(String, nullable=False)
    dni: Mapped[str] = mapped_column(CHAR(8), nullable=False)
    age: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    gender: Mapped[str] = mapped_column(CHAR(1), nullable=False)


def build_session_factory(database_url: str | URL) -> sessionmaker[Session]:
    try:
        engine = create_engine(
            database_url,
            connect_args={"prepare_threshold": None},
            pool_pre_ping=True,
        )
        return sessionmaker(engine, expire_on_commit=False)
    except Exception as exc:
        raise PersistenceError("Database is unavailable") from exc


class SqlAlchemyCaptureRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def add(self, capture: Capture) -> Capture:
        model = CaptureModel(
            image=capture.image,
            dni=capture.dni,
            age=capture.age,
            gender=capture.gender,
        )
        with self._session_factory() as session:
            try:
                session.add(model)
                session.flush()
                generated_id = model.id
                session.commit()
            except Exception as exc:
                session.rollback()
                raise PersistenceError("Capture could not be persisted") from exc
        return Capture(
            id=generated_id,
            image=model.image,
            dni=model.dni,
            age=model.age,
            gender=model.gender,
        )
