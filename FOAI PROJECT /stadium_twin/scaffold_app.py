import os

base_dir = r'c:\Users\manis\OneDrive\Desktop\new foai\stadium_twin'

config_content = '''import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str = os.getenv("SECRET_KEY", "fallback_secret")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./stadium_twin.db")
    TOMTOM_API_KEY: str | None = os.getenv("TOMTOM_API_KEY")
    SATELLITE_TILE_URL: str = os.getenv("SATELLITE_TILE_URL", "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}")

    AREA_PER_PERSON_COMFORTABLE: float = 2.0
    AREA_PER_PERSON_DENSE: float = 4.0
    AREA_PER_PERSON_DANGER: float = 5.0
    EXIT_THROUGHPUT: float = 1.5

    class Config:
        env_file = ".env"

settings = Settings()
'''

db_content = '''from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
'''

models_content = '''from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user")
    twins = relationship("Twin", back_populates="owner")

class Twin(Base):
    __tablename__ = "twins"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    lat = Column(Float)
    lon = Column(Float)
    graph_json = Column(JSON)
    capacity_estimate = Column(Integer)
    polygon_json = Column(JSON)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="twins")
'''

auth_content = '''from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from .db import get_db
from .models import User
from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter(prefix="/auth", tags=["auth"])

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        if token.startswith("Bearer "):
            token = token[7:]
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

@router.post("/register")
def register(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    new_user = User(username=form_data.username, hashed_password=get_password_hash(form_data.password))
    db.add(new_user)
    db.commit()
    return {"message": "User registered successfully"}

@router.post("/login")
def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": user.username, "role": user.role}, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, samesite="lax", max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    return {"message": "Logged in successfully"}

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}
'''

main_content = '''from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
import os
from .db import engine, Base
from .auth import router as auth_router, get_current_user

Base.metadata.create_all(bind=engine)

app = FastAPI(title="StadiumTwin v2")

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(auth_router)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    token = request.cookies.get("access_token")
    if token:
        return RedirectResponse(url="/static/dashboard.html")
    return RedirectResponse(url="/static/login.html")

@app.get("/api/me")
def get_me(current_user = Depends(get_current_user)):
    return {"username": current_user.username, "role": current_user.role}
'''

files = {
    'app/config.py': config_content,
    'app/db.py': db_content,
    'app/models.py': models_content,
    'app/auth.py': auth_content,
    'app/main.py': main_content,
    'app/__init__.py': ''
}

for path, content in files.items():
    full_path = os.path.join(base_dir, path.replace('/', os.sep))
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)

print("FastAPI app scaffolded.")
