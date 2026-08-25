from dataclasses import dataclass


@dataclass(frozen=True)
class Capture:
    id: int | None
    image: str
    dni: str
    age: int
    gender: str
