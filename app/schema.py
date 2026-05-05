from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UserCreate(BaseModel):
    email: str = Field(..., min_length=5, max_length=255, examples=["student@example.com"])
    password: str = Field(..., min_length=8, max_length=128, examples=["strongpassword123"])

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Invalid email format")
        return normalized


class UserRead(BaseModel):
    id: str
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Invalid email format")
        return normalized


class AuthResponse(BaseModel):
    message: str
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class UserUpdate(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Invalid email format")
        return normalized


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class CalculationType(str, Enum):
    ADDITION = "addition"
    SUBTRACTION = "subtraction"
    MULTIPLICATION = "multiplication"
    DIVISION = "division"
    EXPONENTIATION = "exponentiation"
    MODULUS = "modulus"
    AVERAGE = "average"


class CalculationCreate(BaseModel):
    type: CalculationType = Field(..., description="Type of calculation", examples=["addition"])
    inputs: list[float] = Field(..., min_length=2, description="Input values", examples=[[10, 5]])

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, value):
        if isinstance(value, str):
            return value.lower()
        return value

    @model_validator(mode="after")
    def validate_inputs(self):
        if self.type == CalculationType.DIVISION and any(v == 0 for v in self.inputs[1:]):
            raise ValueError("Cannot divide by zero")
        if self.type == CalculationType.MODULUS and self.inputs[1] == 0:
            raise ValueError("Cannot compute modulus with divisor zero")
        return self


class CalculationRead(BaseModel):
    id: str
    a: float
    b: float
    type: CalculationType
    inputs: list[float]
    result: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CalculationTypeStat(BaseModel):
    type: str
    count: int


class ReportRead(BaseModel):
    total_calculations: int
    by_type: list[CalculationTypeStat]
    average_result: float | None
    most_used_type: str | None


