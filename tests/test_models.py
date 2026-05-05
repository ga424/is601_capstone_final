import pytest

from app.models import Addition, Average, Calculation, Division, Exponentiation, Modulus, Multiplication, Subtraction


def test_calculation_factory_returns_correct_subclass():
    assert isinstance(Calculation.create("addition", [1, 2]), Addition)
    assert isinstance(Calculation.create("subtraction", [5, 2]), Subtraction)
    assert isinstance(Calculation.create("multiplication", [2, 3]), Multiplication)
    assert isinstance(Calculation.create("division", [8, 2]), Division)
    assert isinstance(Calculation.create("exponentiation", [2, 3]), Exponentiation)
    assert isinstance(Calculation.create("modulus", [10, 3]), Modulus)
    assert isinstance(Calculation.create("average", [1, 2, 3]), Average)


def test_factory_invalid_type_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported calculation type"):
        Calculation.create("modulo", [8, 2])


def test_polymorphic_results():
    calcs = [
        Calculation.create("addition", [1, 2, 3]),
        Calculation.create("subtraction", [10, 3, 2]),
        Calculation.create("multiplication", [2, 3, 4]),
        Calculation.create("division", [100, 2, 5]),
    ]

    assert [c.get_result() for c in calcs] == [6, 5, 24, 10]


def test_division_by_zero_raises():
    calc = Calculation.create("division", [10, 0])
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        calc.get_result()


def test_exponentiation_get_result():
    assert Calculation.create("exponentiation", [2, 3]).get_result() == 8.0
    assert Calculation.create("exponentiation", [2, 3, 2]).get_result() == 64.0


def test_modulus_get_result():
    assert Calculation.create("modulus", [10, 3]).get_result() == 1.0
    assert Calculation.create("modulus", [10, 5]).get_result() == 0.0


def test_modulus_by_zero_raises():
    calc = Calculation.create("modulus", [10, 0])
    with pytest.raises(ValueError, match="Cannot compute modulus with divisor zero"):
        calc.get_result()


def test_average_get_result():
    assert Calculation.create("average", [1, 2, 3]).get_result() == 2.0
    assert Calculation.create("average", [10, 20]).get_result() == 15.0
