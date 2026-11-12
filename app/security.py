import os, hashlib, hmac, secrets, json, re
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from fastapi import HTTPException
from .models import AuditEvent

hasher = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)
SECRET = os.getenv('APP_SECRET', 'DEV-REPLACE-ME-NOT-FOR-PRODUCTION')
SIGNING_KEY = os.getenv('CERT_SIGNING_KEY', 'DEV-REPLACE-ME-SIGNING-KEY')


def password_hash(p):
    if len(p) < 12 or len(p) > 128:
        raise ValueError('Passwords must contain 12 to 128 characters.')
    return hasher.hash(p)


def password_verify(p, h):
    try:
        return hasher.verify(h, p)
    except (VerifyMismatchError, InvalidHashError):
        return False


def hmac_signature(s):
    return hmac.new(SIGNING_KEY.encode(), s.encode(), hashlib.sha256).hexdigest()


def sign_payload(data):
    serialized = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str)
    return serialized, hmac_signature(serialized)


def verify_signed(payload, signature):
    return hmac.compare_digest(hmac_signature(payload), signature)


def hash_ip(ip):
    return hashlib.sha256((SECRET + '|' + (ip or '')).encode()).hexdigest()


def csrf_token(request):
    if 'csrf' not in request.session:
        request.session['csrf'] = secrets.token_urlsafe(24)
    return request.session['csrf']


def require_roles(user, *roles):
    if not user:
        raise HTTPException(status_code=401, detail='Sign in required')
    if user.role != 'superadmin' and user.role not in roles:
        raise HTTPException(status_code=403, detail='Not authorized for this action')
    return user


def require_org(user):
    if not user or not user.organization_id:
        raise HTTPException(status_code=403, detail='Organization access required')
    return user.organization_id


def safe_slug(s):
    s = re.sub('[^a-z0-9-]+', '-', s.lower().strip()).strip('-')
    if not s:
        raise ValueError('Enter a valid Latin-letter organization code/slug')
    return s[:90]


def audit(db, request, actor, action, target='', organization_id=None, details=None):
    db.add(AuditEvent(organization_id=organization_id if organization_id is not None else (actor.organization_id if actor else None),
        actor_id=actor.id if actor else None, action=action, target=target,
        metadata_json=details or {}, ip_hash=hash_ip(request.client.host if request.client else '')))
