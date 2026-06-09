from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import DATABASE_URL

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    full_name = Column(String)
    username = Column(String, nullable=True)
    theta = Column(Float, default=0.0)  # Rasch qobiliyat darajasi
    is_subscribed = Column(Boolean, default=False)
    subscription_end = Column(DateTime, nullable=True)
    single_tests_left = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    payments = relationship("Payment", back_populates="user")
    answers = relationship("Answer", back_populates="user")

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True)
    text = Column(Text)
    option_a = Column(String)
    option_b = Column(String)
    option_c = Column(String)
    option_d = Column(String)
    correct = Column(String)  # 'a', 'b', 'c', 'd'
    difficulty = Column(Float, default=0.0)  # Rasch b parametri (logit)
    subject = Column(String, default="Fizika")
    created_at = Column(DateTime, default=datetime.now)
    answers = relationship("Answer", back_populates="question")

class DailyTest(Base):
    __tablename__ = "daily_tests"
    id = Column(Integer, primary_key=True)
    date = Column(String, unique=True)  # "2024-01-15"
    question_ids = Column(Text)  # JSON: [1,2,3,...]
    is_active = Column(Boolean, default=True)

class Answer(Base):
    __tablename__ = "answers"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    selected = Column(String)
    is_correct = Column(Boolean)
    answered_at = Column(DateTime, default=datetime.now)
    user = relationship("User", back_populates="answers")
    question = relationship("Question", back_populates="answers")

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Integer)
    payment_type = Column(String)  # "single" yoki "monthly"
    screenshot_file_id = Column(String)
    status = Column(String, default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.now)
    user = relationship("User", back_populates="payments")

def init_db():
    Base.metadata.create_all(engine)

def get_session():
    return Session()
