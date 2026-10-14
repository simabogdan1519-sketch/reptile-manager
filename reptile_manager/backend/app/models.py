import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, Date, Text, ForeignKey, Enum as SAEnum, Table
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Sex(str, enum.Enum):
    male = "male"
    female = "female"
    unknown = "unknown"

class FieldType(str, enum.Enum):
    text = "text"
    number = "number"
    date = "date"
    boolean = "boolean"

class Animal(Base):
    __tablename__ = "animals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    species = Column(String(150), nullable=False)        # e.g. "Python regius"
    common_name = Column(String(100))                    # e.g. "Ball Python"
    morph = Column(String(200))
    sex = Column(SAEnum(Sex), default=Sex.unknown)
    date_of_birth = Column(Date, nullable=True)
    date_acquired = Column(Date, nullable=True)
    origin = Column(String(100))                         # "captive bred" / "wild caught"
    weight_g = Column(Float, nullable=True)
    length_cm = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True, index=True)  # kept for legacy queries
    status    = Column(String(20), default='active', index=True)  # active | inactive | sold
    tracking_id = Column(String(50), nullable=True, index=True)   # human-readable ID
    notes = Column(Text)
    photo_url = Column(String(500))

    # Per-animal feeding reminder (overrides global HA config if set)
    feeding_reminder_enabled = Column(Boolean, default=True)
    feeding_reminder_days = Column(Integer, nullable=True)  # null = use global setting

    # Haltungsbedingungen
    temp_day_c      = Column(Float,       nullable=True)   # Tagestemperatur °C
    temp_night_c    = Column(Float,       nullable=True)   # Nachttemperatur °C
    humidity_min    = Column(Integer,     nullable=True)   # Luftfeuchtigkeit min %
    humidity_max    = Column(Integer,     nullable=True)   # Luftfeuchtigkeit max %
    terrarium_size  = Column(String(100), nullable=True)   # z.B. "120×60×60 cm"
    substrate       = Column(String(200), nullable=True)   # Substrat
    uv_required     = Column(Boolean,     nullable=True)   # UV benötigt?
    lighting_hours  = Column(Integer,     nullable=True)   # Beleuchtungsstunden/Tag

    # Parentage (self-referential)
    mother_id = Column(Integer, ForeignKey("animals.id", ondelete="SET NULL"), nullable=True)
    father_id = Column(Integer, ForeignKey("animals.id", ondelete="SET NULL"), nullable=True)

    mother = relationship(
        "Animal",
        foreign_keys=[mother_id],
        primaryjoin="Animal.mother_id == Animal.id",
        uselist=False,
        lazy="select",
    )
    father = relationship(
        "Animal",
        foreign_keys=[father_id],
        primaryjoin="Animal.father_id == Animal.id",
        uselist=False,
        lazy="select",
    )

    # Access group (NULL = only visible to admins)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True, index=True)
    group = relationship("Group", back_populates="animals")

    feedings = relationship("Feeding", back_populates="animal", cascade="all, delete-orphan")
    sheddings = relationship("Shedding", back_populates="animal", cascade="all, delete-orphan")
    custom_fields = relationship("CustomField", back_populates="animal", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Feeding(Base):
    __tablename__ = "feedings"

    id = Column(Integer, primary_key=True, index=True)
    animal_id = Column(Integer, ForeignKey("animals.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    food_type = Column(String(100))             # "mouse", "rat", "cricket", "dubia", etc.
    food_size = Column(String(50))              # "pinky", "fuzzy", "adult", "XL"
    food_weight_g = Column(Float)
    food_count = Column(Integer, default=1)
    live = Column(Boolean, default=False)       # live vs frozen/thawed
    accepted = Column(Boolean, default=True)
    notes = Column(Text)

    animal = relationship("Animal", back_populates="feedings")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Shedding(Base):
    __tablename__ = "sheddings"

    id = Column(Integer, primary_key=True, index=True)
    animal_id = Column(Integer, ForeignKey("animals.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    complete = Column(Boolean, default=True)        # complete vs stuck shed
    in_one_piece = Column(Boolean, default=True)
    pre_shed_days = Column(Integer)                 # days in "blue phase"
    notes = Column(Text)

    animal = relationship("Animal", back_populates="sheddings")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class BreedingEvent(Base):
    __tablename__ = "breeding_events"

    id = Column(Integer, primary_key=True, index=True)
    female_id = Column(Integer, ForeignKey("animals.id", ondelete="CASCADE"), nullable=False)
    male_id = Column(Integer, ForeignKey("animals.id", ondelete="CASCADE"), nullable=False)
    date_paired = Column(Date)
    date_separated = Column(Date)
    copulation_observed = Column(Boolean, default=False)
    date_eggs_or_birth = Column(Date)
    clutch_size = Column(Integer)       # total eggs / neonates
    fertile_count = Column(Integer)     # fertile eggs / live neonates
    success = Column(Boolean)
    notes = Column(Text)

    female = relationship("Animal", foreign_keys=[female_id])
    male = relationship("Animal", foreign_keys=[male_id])
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class CustomField(Base):
    __tablename__ = "custom_fields"

    id = Column(Integer, primary_key=True, index=True)
    animal_id = Column(Integer, ForeignKey("animals.id", ondelete="CASCADE"), nullable=False, index=True)
    field_name = Column(String(100), nullable=False)
    field_value = Column(String(500))
    field_type = Column(SAEnum(FieldType), default=FieldType.text)

    animal = relationship("Animal", back_populates="custom_fields")

class HAConfig(Base):
    __tablename__ = "ha_config"

    id = Column(Integer, primary_key=True, index=True)
    ha_url = Column(String(300))            # e.g. http://homeassistant.local:8123
    ha_token = Column(String(500))          # Long-Lived Access Token
    webhook_id = Column(String(200))        # HA webhook ID for events
    enabled = Column(Boolean, default=False)
    notify_feeding = Column(Boolean, default=True)
    notify_shedding = Column(Boolean, default=True)
    notify_breeding = Column(Boolean, default=True)
    feeding_reminder_days = Column(Integer, default=7)
    # Züchter/Verkäufer Profil für Herkunftsnachweise
    breeder_name     = Column(String(200), nullable=True)
    breeder_street   = Column(String(200), nullable=True)
    breeder_zip_city = Column(String(100), nullable=True)
    breeder_phone    = Column(String(50),  nullable=True)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(200), unique=True, nullable=True)
    hashed_password = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    groups = relationship("Group", secondary=lambda: user_groups, back_populates="members")


user_groups = Table(
    "user_groups",
    Base.metadata,
    Column("user_id",  Integer, ForeignKey("users.id",  ondelete="CASCADE"), primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
)


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(300), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    members = relationship("User", secondary=user_groups, back_populates="groups")
    animals = relationship("Animal", back_populates="group")
