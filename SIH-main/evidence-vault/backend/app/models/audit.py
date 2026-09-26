"""Audit log model"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(Integer, nullable=True)
    user_email = Column(String(255), default="")
    role = Column(String(50), default="")
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), default="")
    resource_id = Column(String(100), default="")
    ip_address = Column(String(50), default="127.0.0.1")
    status = Column(String(50), default="SUCCESS")
    details = Column(Text, default="")


class PrivilegeRequest(Base):
    __tablename__ = "privilege_requests"

    id = Column(Integer, primary_key=True, index=True)
    requested_by_email = Column(String(255), nullable=False)
    target_user_email = Column(String(255), nullable=False)
    target_full_name = Column(String(255), default="")
    requested_role = Column(String(50), nullable=False)
    justification = Column(Text, default="")
    status = Column(String(50), default="PENDING")  # PENDING, APPROVED, REJECTED
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

