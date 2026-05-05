from datetime import datetime
import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, JSON, String, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Calculation(Base):
    __tablename__ = "calculations"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    a = Column(Float, nullable=False)
    b = Column(Float, nullable=False)
    type = Column(String(50), nullable=False, index=True)
    inputs = Column(JSON, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    result = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __mapper_args__ = {
        "polymorphic_on": type,
        "polymorphic_identity": "calculation",
    }

    @classmethod
    def create(cls, calculation_type: str, *inputs: float | list[float]) -> "Calculation":
        if len(inputs) == 1 and isinstance(inputs[0], list):
            normalized_inputs = inputs[0]
        else:
            normalized_inputs = [float(value) for value in inputs]

        if len(normalized_inputs) < 2:
            raise ValueError("At least two input values are required")

        calculation_classes = {
            "addition": Addition,
            "subtraction": Subtraction,
            "multiplication": Multiplication,
            "division": Division,
        }
        calculation_class = calculation_classes.get(calculation_type.lower())
        if not calculation_class:
            raise ValueError(f"Unsupported calculation type: {calculation_type}")
        return calculation_class(
            inputs=normalized_inputs,
            a=float(normalized_inputs[0]),
            b=float(normalized_inputs[1]),
        )

    def get_result(self) -> float:
        raise NotImplementedError("Subclasses must implement get_result()")


class Addition(Calculation):
    __mapper_args__ = {"polymorphic_identity": "addition"}

    def get_result(self) -> float:
        return sum(self.inputs)


class Subtraction(Calculation):
    __mapper_args__ = {"polymorphic_identity": "subtraction"}

    def get_result(self) -> float:
        result = self.inputs[0]
        for value in self.inputs[1:]:
            result -= value
        return result


class Multiplication(Calculation):
    __mapper_args__ = {"polymorphic_identity": "multiplication"}

    def get_result(self) -> float:
        result = 1.0
        for value in self.inputs:
            result *= value
        return result


class Division(Calculation):
    __mapper_args__ = {"polymorphic_identity": "division"}

    def get_result(self) -> float:
        result = self.inputs[0]
        for value in self.inputs[1:]:
            if value == 0:
                raise ValueError("Cannot divide by zero")
            result /= value
        return result


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    calculations = relationship("Calculation", backref="user")
