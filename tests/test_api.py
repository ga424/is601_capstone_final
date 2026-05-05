import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
import app.main as main_module


def auth_headers(client: TestClient, email: str = "calc-user@example.com") -> dict[str, str]:
    register_response = client.post(
        "/register",
        json={"email": email, "password": "strongpassword123"},
    )
    assert register_response.status_code == 201
    token = register_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    original_engine = main_module.engine
    main_module.engine = test_engine
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    main_module.engine = original_engine


@pytest.mark.parametrize(
    "payload, expected_result, expected_class",
    [
        ({"type": "addition", "inputs": [3, 4, 5]}, 12.0, "addition"),
        ({"type": "subtraction", "inputs": [10, 4, 1]}, 5.0, "subtraction"),
        ({"type": "multiplication", "inputs": [5, 6, 2]}, 60.0, "multiplication"),
        ({"type": "division", "inputs": [120, 3, 2]}, 20.0, "division"),
        ({"type": "exponentiation", "inputs": [2, 3]}, 8.0, "exponentiation"),
        ({"type": "modulus", "inputs": [10, 3]}, 1.0, "modulus"),
        ({"type": "average", "inputs": [1, 2, 3, 4]}, 2.5, "average"),
    ],
)
def test_calculate_success(client, payload, expected_result, expected_class):
    headers = auth_headers(client, email=f"calc-{expected_class}@example.com")
    response = client.post("/calculate", json=payload, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["type"] == expected_class
    assert data["inputs"] == [float(v) for v in payload["inputs"]]
    assert data["a"] == float(payload["inputs"][0])
    assert data["b"] == float(payload["inputs"][1])
    assert data["result"] == expected_result
    assert data["id"]
    assert data["created_at"]
    assert data["updated_at"]


def test_root_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Successfully accessed the API. Use the /calculate endpoint to perform calculations."
    }


def test_division_by_zero_is_rejected(client):
    headers = auth_headers(client, email="div-zero@example.com")
    response = client.post(
        "/calculate",
        json={"type": "division", "inputs": [10, 0]},
        headers=headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["detail"]


def test_modulus_by_zero_is_rejected(client):
    headers = auth_headers(client, email="mod-zero@example.com")
    response = client.post(
        "/calculate",
        json={"type": "modulus", "inputs": [10, 0]},
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"]


def test_invalid_calculation_type_is_rejected(client):
    headers = auth_headers(client, email="invalid-type@example.com")
    response = client.post(
        "/calculate",
        json={"type": "modulo", "inputs": [10, 3]},
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"]


def test_register_user_success(client):
    response = client.post(
        "/register",
        json={"email": "student@example.com", "password": "strongpassword123"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "Registration successful"
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["user"]["email"] == "student@example.com"
    assert data["user"]["is_active"] is True
    assert data["user"]["id"]
    assert data["user"]["created_at"]
    assert data["user"]["updated_at"]


def test_register_user_rejects_duplicate_email(client):
    first = client.post(
        "/register",
        json={"email": "dup@example.com", "password": "strongpassword123"},
    )
    assert first.status_code == 201

    response = client.post(
        "/register",
        json={"email": "dup@example.com", "password": "anotherstrongpassword"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"


def test_login_user_success(client):
    client.post(
        "/register",
        json={"email": "login@example.com", "password": "strongpassword123"},
    )

    response = client.post(
        "/login",
        json={"email": "login@example.com", "password": "strongpassword123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Login successful"
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["user"]["email"] == "login@example.com"


def test_login_user_rejects_invalid_password(client):
    client.post(
        "/register",
        json={"email": "badpass@example.com", "password": "strongpassword123"},
    )

    response = client.post(
        "/login",
        json={"email": "badpass@example.com", "password": "wrongpassword123"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_calculation_crud_flow(client):
    headers = auth_headers(client, email="crud-user@example.com")
    create_response = client.post(
        "/calculations",
        json={"type": "addition", "inputs": [2, 3, 4]},
        headers=headers,
    )

    assert create_response.status_code == 201
    created = create_response.json()
    calculation_id = created["id"]
    assert created["result"] == 9.0

    list_response = client.get("/calculations", headers=headers)
    assert list_response.status_code == 200
    calculations = list_response.json()
    assert any(item["id"] == calculation_id for item in calculations)

    read_response = client.get(f"/calculations/{calculation_id}", headers=headers)
    assert read_response.status_code == 200
    read_data = read_response.json()
    assert read_data["id"] == calculation_id
    assert read_data["type"] == "addition"
    assert read_data["inputs"] == [2.0, 3.0, 4.0]

    update_response = client.put(
        f"/calculations/{calculation_id}",
        json={"type": "multiplication", "inputs": [2, 3, 4]},
        headers=headers,
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["id"] == calculation_id
    assert updated["type"] == "multiplication"
    assert updated["result"] == 24.0

    delete_response = client.delete(f"/calculations/{calculation_id}", headers=headers)
    assert delete_response.status_code == 204

    missing_response = client.get(f"/calculations/{calculation_id}", headers=headers)
    assert missing_response.status_code == 404
    assert missing_response.json()["detail"] == "Calculation not found"


def test_calculation_create_rejects_invalid_payload(client):
    headers = auth_headers(client, email="invalid-payload@example.com")
    response = client.post(
        "/calculations",
        json={"type": "division", "inputs": [10, 0]},
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"]


def test_calculation_delete_missing_returns_not_found(client):
    headers = auth_headers(client, email="missing-delete@example.com")
    response = client.delete("/calculations/not-a-real-id", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Calculation not found"


def test_calculation_endpoints_require_authentication(client):
    post_response = client.post(
        "/calculate",
        json={"type": "addition", "inputs": [1, 2]},
    )
    list_response = client.get("/calculations")

    assert post_response.status_code == 401
    assert post_response.json()["detail"] == "Missing bearer token"
    assert list_response.status_code == 401
    assert list_response.json()["detail"] == "Missing bearer token"
