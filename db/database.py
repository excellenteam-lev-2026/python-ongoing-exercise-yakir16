from datetime import datetime
from typing import List, Optional
import uuid
from pathlib import Path
from sqlalchemy import String, Integer, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "db"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "explainer.db"

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    uploads: Mapped[List["Upload"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Upload(Base):
    __tablename__ = "uploads"
    id: Mapped[int] = mapped_column(primary_key=True)
    uid: Mapped[str] = mapped_column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String, nullable=False)
    upload_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finish_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending") 
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    user: Mapped[Optional["User"]] = relationship(back_populates="uploads")
    def get_upload_path(self) -> Path:
        return BASE_DIR / "uploads" / f"{self.uid}.pptx"
    def get_output_path(self) -> Path:
        return BASE_DIR / "outputs" / f"{self.uid}.json"

Base.metadata.create_all(bind=engine)
