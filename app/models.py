from datetime import datetime, timezone
from sqlalchemy import (Column, Integer, String, ForeignKey, DateTime, Date, Boolean,
                        Numeric, JSON, Text, UniqueConstraint, Index, LargeBinary)
from sqlalchemy.orm import relationship
from .db import Base


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Organization(Base):
    __tablename__ = 'organizations'
    id = Column(Integer, primary_key=True)
    name = Column(String(180), nullable=False)
    name_ps = Column(String(180), default='')
    name_fa = Column(String(180), default='')
    slug = Column(String(100), unique=True, nullable=False)
    code = Column(String(14), unique=True, nullable=False)
    category = Column(String(40), nullable=False, default='university')
    status = Column(String(20), nullable=False, default='active')
    logo_path = Column(String(240), default='')
    signature_path = Column(String(240), default='')
    next_sequence = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    users = relationship('User', back_populates='organization')


class CertificateCategory(Base):
    """An organization's editable taxonomy for issued certificates."""
    __tablename__ = 'certificate_categories'
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=False, index=True)
    slug = Column(String(60), nullable=False)
    name = Column(String(120), nullable=False)
    description = Column(String(320), default='')
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    __table_args__ = (UniqueConstraint('organization_id','slug', name='uq_certificate_category_org_slug'),)


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(254), unique=True, nullable=False, index=True)
    full_name = Column(String(160), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False, default='issuer')
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    organization = relationship('Organization', back_populates='users')


class Plan(Base):
    __tablename__ = 'plans'
    id = Column(Integer, primary_key=True)
    name = Column(String(90), nullable=False, unique=True)
    price_usd = Column(Numeric(10, 2), nullable=False, default=0)
    duration_days = Column(Integer, default=365, nullable=False)
    max_certificates = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)


class Subscription(Base):
    __tablename__ = 'subscriptions'
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey('plans.id'), nullable=False)
    status = Column(String(20), nullable=False, default='pending')
    start_at = Column(DateTime)
    expire_at = Column(DateTime)
    issued_count = Column(Integer, default=0, nullable=False)
    payment_reference = Column(String(120), default='')
    payment_method = Column(String(50), default='manual')
    approved_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    organization = relationship('Organization')
    plan = relationship('Plan')


class CertificateTemplate(Base):
    __tablename__ = 'certificate_templates'
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=False, index=True)
    name = Column(String(140), nullable=False)
    category = Column(String(40), default='university')
    config = Column(JSON, nullable=False)
    background_path = Column(String(240), default='')
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    organization = relationship('Organization')


class Certificate(Base):
    __tablename__ = 'certificates'
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey('certificate_templates.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('certificate_categories.id'), nullable=True, index=True)
    serial = Column(String(64), nullable=False, unique=True, index=True)
    public_token = Column(String(64), nullable=False, unique=True, index=True)
    recipient_en = Column(String(180), nullable=False)
    recipient_ps = Column(String(180), default='')
    recipient_fa = Column(String(180), default='')
    award = Column(String(240), nullable=False)
    program = Column(String(240), default='')
    issue_date = Column(Date, nullable=False)
    valid_until = Column(Date)
    language = Column(String(2), default='en')
    custom = Column(JSON, default=dict)
    issuer_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    issued_at = Column(DateTime, default=utcnow, nullable=False)
    status = Column(String(20), default='valid', nullable=False)
    revoked_at = Column(DateTime)
    revoked_reason = Column(Text, default='')
    signed_payload = Column(Text, nullable=False)
    signature = Column(String(128), nullable=False)
    snapshot = Column(JSON, nullable=False)
    pdf_path = Column(String(240), default='')
    pdf_sha256 = Column(String(64), default='')
    organization = relationship('Organization')
    template = relationship('CertificateTemplate')
    certificate_category = relationship('CertificateCategory')


class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organizations.id'), index=True)
    actor_id = Column(Integer, ForeignKey('users.id'))
    action = Column(String(100), nullable=False)
    target = Column(String(140), default='')
    metadata_json = Column(JSON, default=dict)
    ip_hash = Column(String(64), default='')
    created_at = Column(DateTime, default=utcnow, nullable=False)


class AuthAttempt(Base):
    __tablename__ = 'auth_attempts'
    id = Column(Integer, primary_key=True)
    ip_hash = Column(String(64), index=True)
    created_at = Column(DateTime, default=utcnow)


class VerificationEvent(Base):
    __tablename__ = 'verification_events'
    id = Column(Integer, primary_key=True)
    certificate_id = Column(Integer, ForeignKey('certificates.id'), index=True)
    ip_hash = Column(String(64), index=True)
    created_at = Column(DateTime, default=utcnow)


class StoredFile(Base):
    """Persist generated PDFs and normalized images across stateless hosting restarts.
    For larger paid installations, move to private object storage.
    """
    __tablename__ = 'stored_files'
    name = Column(String(240), primary_key=True)
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=False, index=True)
    media_type = Column(String(60), nullable=False)
    payload = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class WebsiteSettings(Base):
    """Public marketing content and brand controls, managed by platform superadmins."""
    __tablename__ = 'website_settings'
    id = Column(Integer, primary_key=True)
    values = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class WebsiteMessage(Base):
    """Customer inquiries; never made publicly accessible."""
    __tablename__ = 'website_messages'
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(254), nullable=False)
    subject = Column(String(160), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default='new')
    ip_hash = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
