from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from flask import current_app

Base = declarative_base()

class PaymentRequest(Base):
    __tablename__ = 'payments_requests'
    ID = Column(Integer, primary_key=True, autoincrement=True)
    requestGUID = Column(String(64), nullable=False, unique=True)
    customer_id = Column(String(255), nullable=True)
    total_amount = Column(Float, nullable=True)
    source = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class InvoiceStateLog(Base):
    __tablename__ = 'invoice_state_log'
    id = Column(Integer, primary_key=True, autoincrement=True)
    guid = Column(String(64), nullable=False)
    invoice_id = Column(Integer, nullable=False)
    amount_residual = Column(Float, nullable=True)
    amount_total = Column(Float, nullable=True)
    state = Column(String(50), nullable=True)
    log_stage = Column(String(10), nullable=False)  # 'before' or 'after'
    logged_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class PaymentInvoiceResult(Base):
    __tablename__ = 'payment_invoice_result'
    id = Column(Integer, primary_key=True, autoincrement=True)
    guid = Column(String(64), nullable=False)
    invoice_id = Column(Integer, nullable=False)
    amount_paid = Column(Float, nullable=False)
    amount_remaining = Column(Float, nullable=True)
    invoice_total_amount = Column(Float, nullable=True)
    status = Column(String(255), nullable=False)
    logged_at = Column(DateTime, nullable=False, default=datetime.utcnow)

def get_engine():
    config = current_app.config
    return create_engine(config['DATABASE_URL'], pool_pre_ping=True)

def get_session():
    engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def init_db(app):
    with app.app_context():
        engine = get_engine()
        # Create all tables if they don't exist
        Base.metadata.create_all(bind=engine)
