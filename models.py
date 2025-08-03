import os
from sqlalchemy import Column, String, Integer, DateTime, create_engine, Date, Time, func, DATETIME, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from dotenv import load_dotenv 

# Initialize the database
load_dotenv()

Base = declarative_base()
DATABASE_URL = os.getenv("DATABASE_URL")

# Define the models
# Users table
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(200), nullable=False)
    user_type = Column(String(20), nullable=False)
    sc_code = Column(String(10), nullable=False)
    tel = Column(String(20), nullable=False)
    image_url = Column(String(255), nullable=False)
    appointments = relationship("ScheduleAppointment", back_populates="patient")
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"


# Schedulding appointements table
class ScheduleAppointment(Base):
    __tablename__ = 'schedule_appointments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey('users.id'))
    patient = relationship("User", back_populates="appointments")
    appointment_type = Column(String(200), nullable=False)
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    reason = Column(String(700), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    patient = relationship("User", back_populates="appointments")

    def __repr__(self):
        return f"<ScheduleAppointment(id={self.id}, type='{self.appointment_type}', date='{self.date}')>"
    

# Messages model
class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    receiver_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(String(1000), nullable=False)
    is_read = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Message(id={self.id}, from={self.sender_id}, to={self.receiver_id})>"


# Engine and sessionmaker
engine = create_engine(DATABASE_URL, echo=True)
SQLASession = sessionmaker(bind=engine)

# Create tables
Base.metadata.create_all(engine)