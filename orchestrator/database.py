"""
Database initialization and session management
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from models import Base, User

# Database URL from environment or default to SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ralph_advanced.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Password hashing - bcrypt__ident specifies the version to use
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)


def init_db():
    """Initialize database and create tables"""
    Base.metadata.create_all(bind=engine)
    
    # Create default admin user if not exists
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "Admin").first()
        if not admin:
            # Password: 123Test@2026!
            hashed_password = pwd_context.hash("123Test@2026!")
            admin = User(username="Admin", password_hash=hashed_password)
            db.add(admin)
            db.commit()
            print("✓ Default admin user created (Admin / 123Test@2026!)")
        else:
            print("✓ Admin user already exists")
    finally:
        db.close()


def get_db():
    """Dependency for FastAPI to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)
