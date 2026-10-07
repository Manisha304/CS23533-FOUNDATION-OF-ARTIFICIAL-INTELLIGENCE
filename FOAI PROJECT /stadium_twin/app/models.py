from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON
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

class Hospital(Base):
    __tablename__ = "hospitals"
    id = Column(Integer, primary_key=True, index=True)
    osm_id = Column(String, unique=True, index=True)
    name = Column(String, default="Unknown Hospital")
    total_beds = Column(Integer, default=100)
    current_occupancy = Column(Integer, default=50)
    lat = Column(Float)
    lon = Column(Float)
