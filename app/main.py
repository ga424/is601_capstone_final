import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from collections import Counter

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Calculation, User
from app.schema import AuthResponse, CalculationCreate, CalculationRead, CalculationTypeStat, ReportRead, UserCreate, UserLogin, UserRead
from app.security import create_access_token, decode_access_token, hash_password, verify_password

app = FastAPI()
STATIC_DIR = Path(__file__).resolve().parent / "static"
bearer_scheme = HTTPBearer(auto_error=False)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def ensure_calculation_schema() -> None:
    if engine.dialect.name != "postgresql":
        return

    with engine.begin() as connection:
        inspector = inspect(connection)
        if "calculations" not in inspector.get_table_names():
            return

        existing_columns = {column["name"] for column in inspector.get_columns("calculations")}

        if "a" not in existing_columns:
            connection.execute(
                text("ALTER TABLE calculations ADD COLUMN IF NOT EXISTS a DOUBLE PRECISION NOT NULL DEFAULT 0")
            )

        if "b" not in existing_columns:
            connection.execute(
                text("ALTER TABLE calculations ADD COLUMN IF NOT EXISTS b DOUBLE PRECISION NOT NULL DEFAULT 0")
            )

        connection.execute(
            text(
                """
                UPDATE calculations
                SET
                    a = COALESCE((inputs->>0)::double precision, a),
                    b = COALESCE((inputs->>1)::double precision, b)
                """
            )
        )


@app.on_event("startup")
def on_startup():
    max_attempts = 30
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            Base.metadata.create_all(bind=engine)
            ensure_calculation_schema()
            return
        except SQLAlchemyError:
            if attempt == max_attempts:
                raise
            time.sleep(1)


def get_calculation_or_404(calculation_id: str, db: Session, current_user: User) -> Calculation:
    calculation = (
        db.query(Calculation)
        .filter(Calculation.id == calculation_id)
        .filter(Calculation.user_id == current_user.id)
        .first()
    )
    if calculation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calculation not found")
    return calculation


def save_calculation(calculation: Calculation, db: Session) -> Calculation:
    try:
        calculation.result = calculation.get_result()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db.add(calculation)
    db.commit()
    db.refresh(calculation)
    return calculation


def get_user_by_email(email: str, db: Session) -> User | None:
    return db.query(User).filter(User.email == email).first()


def build_auth_response(user: User, message: str) -> AuthResponse:
    access_token = create_access_token(subject=user.id, email=user.email)
    return AuthResponse(message=message, access_token=access_token, user=user)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user

@app.get("/")
def home():
    return {"message": "Successfully accessed the API. Use the /calculate endpoint to perform calculations." }


@app.get("/register", include_in_schema=False)
@app.get("/register.html", include_in_schema=False)
def register_page():
    return FileResponse(STATIC_DIR / "register.html")


@app.get("/login", include_in_schema=False)
@app.get("/login.html", include_in_schema=False)
def login_page():
    return FileResponse(STATIC_DIR / "login.html")


@app.get("/dashboard", include_in_schema=False)
@app.get("/dashboard.html", include_in_schema=False)
def dashboard_page():
    return FileResponse(STATIC_DIR / "dashboard.html")


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@app.post("/users/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing_user = get_user_by_email(payload.email, db)
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return build_auth_response(user, "Registration successful")


@app.post("/login", response_model=AuthResponse)
@app.post("/users/login", response_model=AuthResponse, include_in_schema=False)
def login_user(payload: UserLogin, db: Session = Depends(get_db)):
    user = get_user_by_email(payload.email, db)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    return build_auth_response(user, "Login successful")

@app.post("/calculate", response_model=CalculationRead)
def calculate(
    request: CalculationCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    calculation = Calculation.create(request.type.value, *request.inputs)
    calculation.user_id = _current_user.id
    return save_calculation(calculation, db)


@app.post("/calculations", response_model=CalculationRead, status_code=status.HTTP_201_CREATED)
def create_calculation(
    request: CalculationCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    calculation = Calculation.create(request.type.value, *request.inputs)
    calculation.user_id = _current_user.id
    return save_calculation(calculation, db)


@app.get("/calculations", response_model=list[CalculationRead])
def browse_calculations(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return (
        db.query(Calculation)
        .filter(Calculation.user_id == _current_user.id)
        .order_by(Calculation.created_at.desc())
        .all()
    )


@app.get("/calculations/{calculation_id}", response_model=CalculationRead)
def read_calculation(
    calculation_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return get_calculation_or_404(calculation_id, db, _current_user)


@app.put("/calculations/{calculation_id}", response_model=CalculationRead)
def update_calculation(
    calculation_id: str,
    request: CalculationCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    # ensure calculation belongs to current user
    _ = get_calculation_or_404(calculation_id, db, _current_user)
    updated_calculation = Calculation.create(request.type.value, *request.inputs)
    db.query(Calculation).filter(Calculation.id == calculation_id).update(
        {
            Calculation.type: updated_calculation.type,
            Calculation.inputs: updated_calculation.inputs,
            Calculation.a: updated_calculation.a,
            Calculation.b: updated_calculation.b,
            Calculation.result: updated_calculation.get_result(),
        },
        synchronize_session=False,
    )
    db.commit()
    return get_calculation_or_404(calculation_id, db, _current_user)


@app.delete("/calculations/{calculation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_calculation(
    calculation_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    calculation = get_calculation_or_404(calculation_id, db, _current_user)
    db.delete(calculation)
    db.commit()
    return None


@app.get("/reports", response_model=ReportRead)
def get_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(Calculation)
        .filter(Calculation.user_id == current_user.id)
        .all()
    )
    total = len(rows)
    if total == 0:
        return ReportRead(total_calculations=0, by_type=[], average_result=None, most_used_type=None)

    type_counts = Counter(r.type for r in rows)
    by_type = [CalculationTypeStat(type=t, count=c) for t, c in sorted(type_counts.items())]
    results = [r.result for r in rows if r.result is not None]
    average_result = sum(results) / len(results) if results else None
    most_used_type = type_counts.most_common(1)[0][0]

    return ReportRead(
        total_calculations=total,
        by_type=by_type,
        average_result=average_result,
        most_used_type=most_used_type,
    )

