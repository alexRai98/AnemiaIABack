from dataclasses import dataclass

from pydantic import BaseModel


@dataclass(frozen=True)
class CreateCaptureCommand:
    image: bytes
    dni: str
    sex: str
    age: int


@dataclass(frozen=True)
class CaptureResult:
    id: int
    image: str
    dni: str
    age: int
    gender: str


class CaptureResponse(BaseModel):
    id: int
    image: str
    dni: str
    age: int
    gender: str


class ErrorResponse(BaseModel):
    code: str
    detail: str
