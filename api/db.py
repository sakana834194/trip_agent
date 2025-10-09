from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    create_engine,
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    UniqueConstraint,
    Boolean,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from .config import DB_URL as CONFIG_DB_URL


# 固定配置优先（来自 api/config.py）
if CONFIG_DB_URL:
    engine = create_engine(CONFIG_DB_URL)
else:
    # 兜底为本地 SQLite（理论上不会走到）
    DB_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "trip_planner.db")
    engine = create_engine(f"sqlite:///{DB_DEFAULT_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass

# 用户表，存放用户的id，用户名，密码，创建时间，计划，收藏
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    plans: Mapped[list[Plan]] = relationship("Plan", back_populates="user", cascade="all, delete-orphan")  # type: ignore[name-defined]
    favorites: Mapped[list[Favorite]] = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")  # type: ignore[name-defined]

# 计划表，存放计划的id，用户id，计划标题，创建时间，版本，备注
class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship("User", back_populates="plans")
    versions: Mapped[list[PlanVersion]] = relationship("PlanVersion", back_populates="plan", cascade="all, delete-orphan")  # type: ignore[name-defined]

# 计划版本表，存放计划版本的id，计划id，版本，数据，备注，评分，创建时间
class PlanVersion(Base):
    __tablename__ = "plan_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)  # 1,2,3...
    data: Mapped[dict] = mapped_column(JSON)  # 存储结构化行程与地图编辑数据
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    rating: Mapped[Optional[int]] = mapped_column(Integer, default=None)  # 1-5
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    plan: Mapped[Plan] = relationship("Plan", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("plan_id", "version", name="uq_plan_version"),
    )

# 收藏表，存放收藏的id，用户id，计划id，创建时间，是否活跃
class Favorite(Base):
    __tablename__ = "favorites"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User] = relationship("User", back_populates="favorites")
    plan: Mapped[Plan] = relationship("Plan")

# 初始化数据库
def init_db() -> None:
    Base.metadata.create_all(bind=engine)

# 获取数据库
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


