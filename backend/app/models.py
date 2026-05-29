import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    Enum,
    UUID,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    """Модель пользователя системы."""

    __tablename__ = "users"

    # Используем UUID вместо String
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    vehicles = relationship(
        "Vehicle", back_populates="user", lazy="select", cascade="all, delete-orphan"
    )
    sessions = relationship(
        "Session", back_populates="user", lazy="select", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, is_admin={self.is_admin})>"


class Vehicle(Base):
    """Модель транспортного средства."""

    __tablename__ = "vehicles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    license_plate = Column(String(20), unique=True, nullable=False, index=True)
    model = Column(String(100), nullable=True)
    color = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # relationships
    user = relationship("User", back_populates="vehicles", lazy="select")
    sessions = relationship(
        "Session", back_populates="vehicle", lazy="select", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Vehicle(id={self.id}, plate={self.license_plate})>"


class Tariff(Base):
    """Модель тарифа парковки."""

    __tablename__ = "tariffs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    price_per_hour = Column(Numeric(10, 2), nullable=False)
    daily_cap = Column(Numeric(10, 2), nullable=False)

    def __repr__(self):
        return f"<Tariff(id={self.id}, name={self.name}, price={self.price_per_hour})>"


class Session(Base):
    """Модель сессии парковки."""

    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False)
    entry_time = Column(DateTime(timezone=True), nullable=False)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        Enum("pending", "paid", "closed", name="session_status"),
        default="pending",
        nullable=False,
    )
    cost = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    # relationships
    user = relationship("User", back_populates="sessions", lazy="select")
    vehicle = relationship("Vehicle", back_populates="sessions", lazy="select")
    # Зона парковки
    zone_id = Column(UUID(as_uuid=True), ForeignKey("parking_zones.id"), nullable=True)
    zone = relationship("ParkingZone", back_populates="sessions", lazy="select")

    payments = relationship(
        "Payment", back_populates="session", lazy="select", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id}, status={self.status})>"


class ParkingZone(Base):
    """Модель парковочной зоны."""

    __tablename__ = "parking_zones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    total_spots = Column(Numeric(10, 0), default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Foreign keys
    tariff_id = Column(UUID(as_uuid=True), ForeignKey("tariffs.id"), nullable=True)

    # relationships
    tariff = relationship("Tariff", lazy="select")
    sessions = relationship(
        "Session", back_populates="zone", lazy="select"
    )

    def __repr__(self):
        return f"<ParkingZone(id={self.id}, name={self.name}, spots={self.total_spots})>"


class Payment(Base):
    """Модель платежа."""

    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(
        Enum("pending", "completed", "failed", "refunded", name="payment_status"),
        default="pending",
        nullable=False,
    )
    transaction_id = Column(String(255), nullable=True, unique=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)

    # relationships
    session = relationship("Session", back_populates="payments", lazy="select")

    def __repr__(self):
        return f"<Payment(id={self.id}, amount={self.amount}, status={self.status})>"
