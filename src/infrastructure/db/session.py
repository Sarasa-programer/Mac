from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from src.config.settings import settings

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    pool_pre_ping=True,  # Check connection health
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Session:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create tables in database"""
    # Import all models to ensure they are registered with Base
    from src.core.domain import user, case, task
    Base.metadata.create_all(bind=engine)
    
    # Create default user
    from src.core.domain.user import User
    from src.core.security import get_password_hash
    
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.email == "admin@example.com").first()
        if not existing_user:
            new_user = User(
                email="admin@example.com",
                hashed_password=get_password_hash("password123"),
                full_name="Admin User",
                role="admin",
                is_active=True
            )
            db.add(new_user)
            db.commit()
            print("✅ Default user created: admin@example.com / password123")
    except Exception as e:
        print(f"⚠️ Error creating default user: {e}")
    finally:
        db.close()

    print("✅ Database tables created successfully")
