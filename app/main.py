import os, io, csv, json, secrets, re, hashlib
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from contextlib import asynccontextmanager
from urllib.parse import quote, urlparse

from fastapi import FastAPI, Depends, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import func, select, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from jinja2 import Environment
from fastapi.templating import Jinja2Templates

from .db import Base, engine, get_db, SessionLocal
from .models import (Organization, User, Plan, Subscription, CertificateTemplate,
                     Certificate, AuditEvent, AuthAttempt, VerificationEvent, StoredFile, WebsiteSettings, WebsiteMessage, utcnow)
from .security import (SECRET, SIGNING_KEY, password_verify, password_hash, sign_payload,
                       verify_signed, csrf_token, require_roles, require_org, safe_slug, audit, hash_ip)
from .catalog import CATEGORIES, LABELS, make_design, sanitize_design
from .i18n import LANGUAGES, translate
from .rendering import FILES_DIR, CERT_DIR, save_certificate_pdf
from .assets import safe_upload

ROOT = Path(__file__).resolve().parent
def configured_public_origin():
    explicit = os.getenv('PUBLIC_BASE_URL','').strip() or os.getenv('RENDER_EXTERNAL_URL','').strip()
    if explicit:
        return explicit.rstrip('/')
    hostname = os.getenv('VERCEL_PROJECT_PRODUCTION_URL','').strip() or os.getenv('VERCEL_URL','').strip()
    if hostname:
        return 'https://' + hostname.removeprefix('https://').removeprefix('http://').strip('/')
    return ''

PRODUCTION = os.getenv('PRODUCTION','false').lower() == 'true' 
if PRODUCTION and (
    len(SECRET)<40 or len(SIGNING_KEY)<40 or SECRET==SIGNING_KEY
    or SECRET.startswith(('DEV-','REPLACE')) or SIGNING_KEY.startswith(('DEV-','REPLACE'))
):
    raise RuntimeError('Set unique APP_SECRET and CERT_SIGNING_KEY before production deployment')
if PRODUCTION and not configured_public_origin().startswith('https://'):
    raise RuntimeError('PUBLIC_BASE_URL must use HTTPS in production')


DEFAULT_SITE = {
    'brand_name':'CertiGov',
    'tagline':'Design. Issue. Verify.',
    'hero_title':'Credentials built for trust.',
    'hero_text':'Create beautiful certificates, invite your team and make authenticity verifiable through a public QR link.',
    'about_title':'One place for credible certificates.',
    'about_text':'CertiGov brings organizations, certificate designers, administrators and recipients into a single traceable workflow. Design, issue, verify and revoke credentials from a secure online portal.',
    'why_text':'Printed documents can be altered or difficult to verify. Every CertiGov certificate has a unique verification address linked to its issuing organization and current registry status.',
    'mission_text':'Help institutions deliver beautifully designed, verifiable credentials with transparent processes and simple tools.',
    'contact_email':'', 'phone':'', 'address':'',
    'facebook':'', 'instagram':'', 'linkedin':'', 'youtube':'', 'x':'', 'whatsapp':'',
    'primary_color':'#102f49', 'accent_color':'#d6a659', 'background_color':'#f6f8fb',
    'hero_style':'aurora', 'font_style':'modern', 'logo_text':'CG',
}
SITE_TEXT_FIELDS = {'brand_name':60,'tagline':120,'hero_title':130,'hero_text':500,'about_title':150,
 'about_text':3000,'why_text':3000,'mission_text':3000,'contact_email':254,'phone':80,
 'address':300,'logo_text':3}
SITE_LINK_FIELDS = ('facebook','instagram','linkedin','youtube','x','whatsapp')
SITE_PALETTES = ('primary_color','accent_color','background_color')

def website_settings(db):
    record=db.get(WebsiteSettings,1)
    return {**DEFAULT_SITE, **(record.values if record and isinstance(record.values,dict) else {})}

def safe_site_url(value):
    value=(value or '').strip()[:350]
    if not value:return ''
    parsed=urlparse(value)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Social links must be complete HTTPS URLs')
    return value


def initialize_database():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.query(Plan).count() == 0:
            db.add_all([
                Plan(name='Starter',price_usd=Decimal('79.00'),duration_days=365,max_certificates=500),
                Plan(name='Professional',price_usd=Decimal('200.00'),duration_days=365,max_certificates=None),
                Plan(name='Enterprise',price_usd=Decimal('450.00'),duration_days=365,max_certificates=None),
            ])
            db.commit()
        # One-time cloud bootstrap: do not replace or reset an existing administrator.
        email = os.getenv('INITIAL_ADMIN_EMAIL', '').lower().strip()
        password = os.getenv('INITIAL_ADMIN_PASSWORD', '')
        if email and password and not db.query(User).filter_by(role='superadmin').first():
            from .security import password_hash
            db.add(User(email=email, full_name=os.getenv('INITIAL_ADMIN_NAME', 'Platform Owner')[:160],
                        password_hash=password_hash(password), role='superadmin'))
            db.commit()


@asynccontextmanager
async def lifespan(app):
    initialize_database()
    yield


async def validate_csrf(request: Request):
    if request.method in ('POST','PUT','PATCH','DELETE'):
        supplied = request.headers.get('x-csrf-token','')
        if not supplied:
            form = await request.form()
            supplied = str(form.get('csrf',''))
        expected = request.session.get('csrf','')
        if not supplied or not expected or not secrets.compare_digest(supplied, expected):
            raise HTTPException(status_code=403,detail='CSRF validation failed. Refresh the page.')


app = FastAPI(title='CertiGov — Certificate Issuance and Verification', version='1.0.0', lifespan=lifespan,
              dependencies=[Depends(validate_csrf)],
              docs_url=None if PRODUCTION else '/api/docs', redoc_url=None)
app.add_middleware(SessionMiddleware,secret_key=SECRET,session_cookie='certigov_session',
                   same_site='lax',https_only=PRODUCTION,max_age=8*60*60)
app.mount('/static',StaticFiles(directory=str(ROOT/'static')) ,name='static')
templates=Jinja2Templates(directory=str(ROOT/'templates'))


@app.middleware('http')
async def safety_middleware(request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
    response.headers['Content-Security-Policy']=("default-src 'self'; img-src 'self' data:; "
       "style-src 'self' 'unsafe-inline'; script-src 'self'; font-src 'self'; "
       "base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
    if request.url.path.startswith(('/verify/','/api/verify/')):
        response.headers['X-Robots-Tag']='noindex, nofollow'
        response.headers['Cache-Control']='no-store'
    if PRODUCTION: response.headers['Strict-Transport-Security']='max-age=31536000; includeSubDomains'
    return response


def current_user(request: Request, db:Session=Depends(get_db)):
    uid = request.session.get('user_id')
    if not uid: return None
    user = db.get(User,uid)
    if not user or not user.is_active:
        request.session.pop('user_id',None)
        return None
    return user


def need_user(user=Depends(current_user)):
    if not user: raise HTTPException(401,'Sign in first')
    return user


def need_admin(user=Depends(need_user)):
    if user.role != 'superadmin': raise HTTPException(403,'Super administrator required')
    return user


def need_org(user=Depends(need_user), db:Session=Depends(get_db)):
    if not user.organization_id: raise HTTPException(403,'Organization required')
    org=db.get(Organization,user.organization_id)
    if not org or org.status!='active': raise HTTPException(403,'Organization account is suspended')
    return user


def need_manager(user=Depends(need_org)):
    return require_roles(user,'org_admin')


def need_editor(user=Depends(need_org)):
    return require_roles(user,'org_admin','designer')


def need_issuer(user=Depends(need_org)):
    return require_roles(user,'org_admin','issuer')


def flash(req, msg, kind='success'):
    req.session['flash']={'text':msg,'kind':kind}


def go(path):
    return RedirectResponse(path,status_code=303)


def render(req, filename, db=None, user=None, status_code=200, **extra):
    lang=req.session.get('lang','en')
    if lang not in LANGUAGES: lang='en'
    if user is None and db:
        uid=req.session.get('user_id')
        user=db.get(User,uid) if uid else None
    context={'request':req,'user':user,'lang':lang,'rtl':lang in ('ps','fa'),
      't':lambda s:translate(s,lang),'languages':LANGUAGES,
      'categories':CATEGORIES,'flash':req.session.pop('flash',None), 'csrf':csrf_token(req),
      'site':website_settings(db) if db is not None else DEFAULT_SITE}
    context.update(extra)
    return templates.TemplateResponse(req,filename,context,status_code=status_code)


def active_subscription(db, org_id, lock=False):
    q=(select(Subscription).where(Subscription.organization_id==org_id,
      Subscription.status=='active',Subscription.start_at<=utcnow(),
      Subscription.expire_at>utcnow()).order_by(Subscription.expire_at.desc()))
    if lock:q=q.with_for_update()
    return db.execute(q).scalars().first()


def assert_tenant(obj, user):
    if not obj or (user.role!='superadmin' and obj.organization_id != user.organization_id):
        raise HTTPException(404,'Record not found')
    return obj


def require_issuing_capacity(db,org):
    sub=active_subscription(db,org.id,lock=True)
    if not sub: raise ValueError('No active paid subscription for this organization')
    if sub.plan.max_certificates is not None and sub.issued_count >= sub.plan.max_certificates:
        raise ValueError('Certificate allowance exhausted — renew or upgrade your plan')
    return sub


def payload_for(cert):
    return {'organization_id':cert.organization_id,'template_id':cert.template_id,
      'serial':cert.serial, 'public_token':cert.public_token, 'recipient_en':cert.recipient_en,
      'recipient_ps':cert.recipient_ps or '', 'recipient_fa':cert.recipient_fa or '',
      'award':cert.award,'program':cert.program or '', 'issue_date':str(cert.issue_date),
      'valid_until':str(cert.valid_until) if cert.valid_until else '',
      'language':cert.language,'custom':cert.custom or {}, 'snapshot':cert.snapshot}


def integrity_ok(cert):
    signed, sig=sign_payload(payload_for(cert))
    return secrets.compare_digest(signed.encode('utf-8'),cert.signed_payload.encode('utf-8')) and verify_signed(cert.signed_payload,cert.signature)


def verification_state(cert):
    if not integrity_ok(cert): return 'integrity_failed'
    if cert.status=='revoked': return 'revoked'
    if cert.valid_until and cert.valid_until<date.today(): return 'expired'
    return 'valid'


def public_base_url(request):
    base = configured_public_origin() or str(request.base_url).rstrip('/')
    if PRODUCTION and not base.startswith('https://'):
        raise RuntimeError('Public verification requires HTTPS')
    return base.rstrip('/')


def make_certificate(db,request,user,org,template,data):
    sub=require_issuing_capacity(db,org)
    serial=f'{org.code}-{date.today().year}-{org.next_sequence:07d}'
    org.next_sequence+=1
    sub.issued_count+=1
    token=secrets.token_urlsafe(24)
    snapshot={'config':sanitize_design(template.config),'background_path':template.background_path or '',
              'logo_path':org.logo_path or '', 'signature_path':org.signature_path or '',
              'organization_name':org.name,'organization_name_ps':org.name_ps or '',
              'organization_name_fa':org.name_fa or ''}
    cert=Certificate(organization_id=org.id,template_id=template.id,serial=serial,
      public_token=token, recipient_en=data['recipient_en'].strip(),
      recipient_ps=data.get('recipient_ps','').strip(),recipient_fa=data.get('recipient_fa','').strip(),
      award=data['award'].strip(),program=data.get('program','').strip(),
      issue_date=data['issue_date'],valid_until=data.get('valid_until'),
      language=data.get('language','en'), issuer_id=user.id,
      custom={},snapshot=snapshot,signed_payload='',signature='')
    cert.signed_payload,cert.signature=sign_payload(payload_for(cert))
    db.add(cert)
    db.flush()
    base=public_base_url(request)
    cert.pdf_path, cert.pdf_sha256=save_certificate_pdf(cert,org,snapshot,base,db=db)
    audit(db,request,user,'certificate.issued',cert.serial,details={'template_id':template.id})
    return cert


def parse_fields(recipient_en,recipient_ps,recipient_fa,award,program,issue_date,valid_until,language):
    recipient_en=recipient_en.strip(); award=award.strip()
    if not recipient_en or not award: raise ValueError('Recipient name and award are required')
    if len(recipient_en)>180 or len(award)>240: raise ValueError('Recipient / award is too long')
    if max(len(recipient_ps),len(recipient_fa))>180 or len(program)>240: raise ValueError('Field is too long')
    if language not in LANGUAGES: raise ValueError('Invalid certificate language')
    try:
        issue=date.fromisoformat(issue_date)
        expires=date.fromisoformat(valid_until) if valid_until else None
    except ValueError as exc: raise ValueError('Invalid date') from exc
    if expires and expires<issue: raise ValueError('Expiry date precedes issue date')
    return dict(recipient_en=recipient_en,recipient_ps=recipient_ps,recipient_fa=recipient_fa,
                award=award,program=program,issue_date=issue,valid_until=expires,language=language)


@app.exception_handler(HTTPException)
async def web_error(req,exc):
    if exc.status_code==401 and not req.url.path.startswith('/api/'):
        return go('/login')
    if req.url.path.startswith('/api/'):
        return JSONResponse({'error':exc.detail},status_code=exc.status_code)
    return render(req,'error.html',status_code=exc.status_code,error=exc.detail,code=exc.status_code)


@app.get('/',response_class=HTMLResponse)
def home(req:Request,db:Session=Depends(get_db),user=Depends(current_user)):
    if user:return go('/admin' if user.role=='superadmin' else '/dashboard')
    return render(req,'home.html',db=db,plans=db.query(Plan).filter_by(is_active=True).order_by(Plan.price_usd).all())


@app.get('/plans',response_class=HTMLResponse)
def public_plans(req:Request,db:Session=Depends(get_db),user=Depends(current_user)):
    plans=db.query(Plan).filter_by(is_active=True).order_by(Plan.price_usd).all()
    return render(req,'public_plans.html',db=db,user=user,plans=plans)


@app.get('/signup',response_class=HTMLResponse)
def public_signup(req:Request,plan_id:int=0,db:Session=Depends(get_db),user=Depends(current_user)):
    plans=db.query(Plan).filter_by(is_active=True).order_by(Plan.price_usd).all()
    selected=db.get(Plan,plan_id) if plan_id else (plans[0] if plans else None)
    return render(req,'signup.html',db=db,user=user,plans=plans,selected=selected)


@app.post('/signup')
def public_signup_submit(req:Request,plan_id:int=Form(...),organization_name:str=Form(...),
    category:str=Form('university'),admin_name:str=Form(...),email:str=Form(...),
    password:str=Form(...),phone:str=Form(''),website:str=Form(''),
    db:Session=Depends(get_db)):
    if website.strip():raise HTTPException(400,'Invalid registration')
    plan=db.get(Plan,plan_id)
    if not plan or not plan.is_active:raise HTTPException(400,'Selected plan is unavailable')
    name=organization_name.strip();admin_name=admin_name.strip();email=email.lower().strip()
    if not 3<=len(name)<=180 or not 2<=len(admin_name)<=160 or category not in CATEGORIES:
        raise HTTPException(400,'Invalid organization registration details')
    if len(phone)>80 or len(email)>254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):
        raise HTTPException(400,'Enter a valid email address')
    # Prevent registration bursts from one IP while allowing normal institutional applications.
    ip=hash_ip(req.client.host if req.client else '')
    recent=utcnow()-timedelta(hours=1)
    if db.query(WebsiteMessage).filter_by(ip_hash=ip,subject='New organization registration').filter(WebsiteMessage.created_at>=recent).count()>=3:
        raise HTTPException(429,'Too many registrations from this network. Try again later.')
    try:
        pwd=password_hash(password)
        slug_root=safe_slug(name)[:65]
        suffix=secrets.token_hex(4)
        org=Organization(name=name,slug=f'{slug_root}-{suffix}',code=('REG'+secrets.token_hex(5).upper())[:13],
            category=category,status='active')
        db.add(org);db.flush()
        db.add(User(email=email,full_name=admin_name,password_hash=pwd,role='org_admin',organization_id=org.id))
        db.add(Subscription(organization_id=org.id,plan_id=plan.id,status='pending',payment_method='manual'))
        db.add(WebsiteMessage(name=admin_name,email=email,subject='New organization registration',
            message=f'Organization: {name} | Category: {category} | Plan: {plan.name} | Phone: {phone[:80]}',ip_hash=ip))
        db.commit()
    except (ValueError,IntegrityError):
        db.rollback();flash(req,'Email already registered or password invalid (minimum 12 characters)','error')
        return go(f'/signup?plan_id={plan_id}')
    flash(req,'Account created. Subscription request is pending platform approval. You can sign in now.')
    return go('/login')


@app.get('/about',response_class=HTMLResponse)
def public_about(req:Request,db:Session=Depends(get_db),user=Depends(current_user)):
    return render(req,'about.html',db=db,user=user)


@app.get('/contact',response_class=HTMLResponse)
def public_contact(req:Request,db:Session=Depends(get_db),user=Depends(current_user)):
    return render(req,'contact.html',db=db,user=user)


@app.post('/contact')
def public_contact_submit(req:Request,name:str=Form(...),email:str=Form(...),
    subject:str=Form(...),message:str=Form(...),website:str=Form(''),db:Session=Depends(get_db)):
    if website.strip():raise HTTPException(400,'Invalid inquiry')
    name=name.strip();email=email.lower().strip();subject=subject.strip();message=message.strip()
    if not 2<=len(name)<=120 or not 3<=len(subject)<=160 or not 10<=len(message)<=3000:
        raise HTTPException(400,'Please complete all fields')
    if len(email)>254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):
        raise HTTPException(400,'Valid email required')
    ip=hash_ip(req.client.host if req.client else '')
    if db.query(WebsiteMessage).filter(WebsiteMessage.ip_hash==ip,WebsiteMessage.created_at>=utcnow()-timedelta(hours=1)).count()>=5:
        raise HTTPException(429,'Message limit reached. Please try later.')
    db.add(WebsiteMessage(name=name,email=email,subject=subject,message=message,ip_hash=ip))
    db.commit();flash(req,'Message received. Thank you for contacting CertiGov.')
    return go('/contact')


@app.get('/admin/website')
def admin_website(req:Request,db:Session=Depends(get_db),user=Depends(need_admin)):
    return render(req,'admin_website.html',db=db,user=user)


@app.post('/admin/website')
async def admin_website_save(req:Request,db:Session=Depends(get_db),user=Depends(need_admin)):
    form=await req.form()
    current=website_settings(db)
    updated={}
    for key,maxlen in SITE_TEXT_FIELDS.items():
        updated[key]=str(form.get(key,'')).strip()[:maxlen]
    for key in SITE_LINK_FIELDS:
        try: updated[key]=safe_site_url(str(form.get(key,'')))
        except ValueError as ex: raise HTTPException(400,str(ex))
    for key in SITE_PALETTES:
        value=str(form.get(key,DEFAULT_SITE[key]))
        if not re.fullmatch(r'#[0-9a-fA-F]{6}',value):raise HTTPException(400,'Invalid website theme color')
        updated[key]=value
    updated['hero_style']=str(form.get('hero_style','aurora')) if str(form.get('hero_style','aurora')) in ('aurora','minimal','editorial','midnight') else 'aurora'
    updated['font_style']=str(form.get('font_style','modern')) if str(form.get('font_style','modern')) in ('modern','classic','rounded') else 'modern'
    record=db.get(WebsiteSettings,1)
    if record:record.values={**current,**updated}
    else:db.add(WebsiteSettings(id=1,values={**current,**updated}))
    audit(db,req,user,'website.settings.updated','homepage');db.commit()
    flash(req,'Public website settings published')
    return go('/admin/website')


@app.get('/admin/messages')
def admin_messages(req:Request,db:Session=Depends(get_db),user=Depends(need_admin)):
    messages=db.query(WebsiteMessage).order_by(WebsiteMessage.id.desc()).limit(200).all()
    return render(req,'admin_messages.html',db=db,user=user,messages=messages)


@app.post('/admin/messages/{message_id}/status')
def admin_message_status(req:Request,message_id:int,status:str=Form(...),
    db:Session=Depends(get_db),user=Depends(need_admin)):
    record=db.get(WebsiteMessage,message_id)
    if not record or status not in ('new','reviewed','closed'):raise HTTPException(400,'Invalid message or status')
    record.status=status;db.commit();return go('/admin/messages')


@app.get('/health')
def health():
    return {'status':'ok','service':'certigov'}


@app.get('/language/{lang}')
def change_language(req:Request,lang:str):
    if lang in LANGUAGES:req.session['lang']=lang
    next_url=req.headers.get('referer','/')
    # Never redirect to a different origin.
    from urllib.parse import urlparse
    parsed=urlparse(next_url)
    path=parsed.path or '/'
    return go(path + (('?' + parsed.query) if parsed.query else ''))


@app.get('/login')
def login_page(req:Request,db:Session=Depends(get_db)):
    return render(req,'login.html',db=db)


@app.post('/login')
def login(req:Request,email:str=Form(...),password:str=Form(...),db:Session=Depends(get_db)):
    ip=hash_ip(req.client.host if req.client else '')
    recent=utcnow()-timedelta(minutes=10)
    if db.query(AuthAttempt).filter(AuthAttempt.ip_hash==ip,AuthAttempt.created_at>=recent).count()>15:
        return render(req,'login.html',status_code=429,error='Too many login attempts; try again later')
    user=db.query(User).filter(User.email==email.lower().strip()).first()
    if not user or not user.is_active or not password_verify(password,user.password_hash):
        db.add(AuthAttempt(ip_hash=ip));db.commit()
        return render(req,'login.html',status_code=401,error='Incorrect email or password')
    if user.organization_id:
        org=db.get(Organization,user.organization_id)
        if not org or org.status!='active':
            return render(req,'login.html',status_code=403,error='Organization account suspended')
    lang=req.session.get('lang','en')
    req.session.clear()
    req.session.update({'user_id':user.id,'lang':lang,'csrf':secrets.token_urlsafe(24)})
    audit(db,req,user,'auth.login');db.commit()
    return go('/admin' if user.role=='superadmin' else '/dashboard')


@app.post('/logout')
def logout(req:Request):
    req.session.clear()
    return go('/')


@app.get('/admin')
def admin_dashboard(req:Request,db:Session=Depends(get_db),user=Depends(need_admin)):
    data={'organizations':db.query(Organization).count(),
          'certificates':db.query(Certificate).count(),
          'active':db.query(Organization).filter_by(status='active').count(),
          'pending':db.query(Subscription).filter_by(status='pending').count()}
    events=db.query(AuditEvent).order_by(AuditEvent.id.desc()).limit(12).all()
    return render(req,'admin_dashboard.html',db=db,user=user,stats=data,events=events)


@app.get('/admin/organizations')
def admin_organizations(req:Request,db:Session=Depends(get_db),user=Depends(need_admin)):
    items=db.query(Organization).order_by(Organization.id.desc()).all()
    return render(req,'organizations.html',db=db,user=user,organizations=items)


@app.post('/admin/organizations')
def admin_organizations_add(req:Request,name:str=Form(...),name_ps:str=Form(''),name_fa:str=Form(''),
  slug:str=Form(...),code:str=Form(...),category:str=Form('university'),
  admin_email:str=Form(...),admin_name:str=Form(...),admin_password:str=Form(...),
  db:Session=Depends(get_db),user=Depends(need_admin)):
    try:
        slug=safe_slug(slug)
        code=re.sub(r'[^A-Z0-9]','',code.upper())[:12]
        if len(code)<3 or len(name.strip())<2 or category not in CATEGORIES:raise ValueError('Enter a valid organization name, type and code (3–12 Latin letters/digits)')
        pwd=password_hash(admin_password)
        org=Organization(name=name.strip()[:180],name_ps=name_ps[:180],name_fa=name_fa[:180],
                         slug=slug,code=code,category=category)
        db.add(org);db.flush()
        org_user=User(email=admin_email.lower().strip(),full_name=admin_name[:160],
                      password_hash=pwd,organization_id=org.id,role='org_admin')
        db.add(org_user)
        audit(db,req,user,'organization.created',str(org.id),organization_id=org.id,
              details={'name':org.name,'admin_email':org_user.email})
        db.commit()
        flash(req,'Organization and its administrator were created. Assign a subscription next.')
        return go('/admin/organizations')
    except (ValueError,IntegrityError) as exc:
        db.rollback()
        flash(req,'Unable to create organization: duplicate email/code/slug or invalid input','error')
        return go('/admin/organizations')


@app.post('/admin/organizations/{org_id}/status')
def organization_status(req:Request,org_id:int,status:str=Form(...),db:Session=Depends(get_db),user=Depends(need_admin)):
    org=db.get(Organization,org_id)
    if not org:raise HTTPException(404,'Organization not found')
    if status not in ('active','suspended'):raise HTTPException(400,'Invalid status')
    org.status=status
    audit(db,req,user,'organization.status',str(org.id),organization_id=org.id,details={'status':status})
    db.commit();flash(req,'Organization status updated')
    return go('/admin/organizations')


@app.get('/admin/plans')
def plan_page(req:Request,db:Session=Depends(get_db),user=Depends(need_admin)):
    plans=db.query(Plan).order_by(Plan.price_usd).all()
    return render(req,'plans.html',db=db,user=user,plans=plans)


@app.post('/admin/plans')
def plan_create(req:Request,name:str=Form(...),price_usd:str=Form(...),duration_days:int=Form(...),
                max_certificates:str=Form(''),db:Session=Depends(get_db),user=Depends(need_admin)):
    try:
        price=Decimal(price_usd)
        cap=int(max_certificates) if max_certificates.strip() else None
        if price<0 or price>100000 or duration_days<1 or duration_days>3650 or (cap is not None and (cap<1 or cap>100000000)):
            raise ValueError('Invalid price, duration or allowance')
        db.add(Plan(name=name.strip()[:90],price_usd=price,duration_days=duration_days,max_certificates=cap))
        audit(db,req,user,'plan.created',name[:90]);db.commit()
        flash(req,'Plan created')
    except (ValueError,InvalidOperation,IntegrityError):
        db.rollback();flash(req,'Invalid or duplicate plan','error')
    return go('/admin/plans')


@app.get('/admin/subscriptions')
def subscription_requests(req:Request,db:Session=Depends(get_db),user=Depends(need_admin)):
    items=db.query(Subscription).order_by(Subscription.id.desc()).limit(150).all()
    return render(req,'admin_subscriptions.html',db=db,user=user,subscriptions=items)


@app.post('/admin/subscriptions/{sub_id}/review')
def review_subscription(req:Request,sub_id:int,decision:str=Form(...),
                        db:Session=Depends(get_db),user=Depends(need_admin)):
    sub=db.execute(select(Subscription).where(Subscription.id==sub_id).with_for_update()).scalar_one_or_none()
    if not sub or sub.status!='pending':raise HTTPException(400,'Only pending requests can be reviewed')
    if decision not in ('approve','reject'):raise HTTPException(400,'Invalid decision')
    if decision=='approve':
        # Only one active subscription per organization.
        db.query(Subscription).filter(Subscription.organization_id==sub.organization_id,
                Subscription.status=='active').update({'status':'superseded'})
        sub.status='active';sub.start_at=utcnow();sub.expire_at=utcnow()+timedelta(days=sub.plan.duration_days)
        sub.issued_count=0
    else:sub.status='rejected'
    sub.approved_by=user.id
    audit(db,req,user,'subscription.'+decision,str(sub.id),organization_id=sub.organization_id,
          details={'plan':sub.plan.name,'payment_reference':sub.payment_reference})
    db.commit();flash(req,'Subscription '+decision+'d')
    return go('/admin/subscriptions')


@app.get('/dashboard')
def dashboard(req:Request,db:Session=Depends(get_db),user=Depends(need_org)):
    org=db.get(Organization,user.organization_id)
    count=db.query(Certificate).filter_by(organization_id=org.id).count()
    valid=db.query(Certificate).filter(Certificate.organization_id==org.id,
        Certificate.status=='valid',or_(Certificate.valid_until.is_(None),Certificate.valid_until>=date.today())).count()
    start=date.today().replace(day=1)
    month=db.query(Certificate).filter(Certificate.organization_id==org.id,Certificate.issue_date>=start).count()
    sub=active_subscription(db,org.id)
    recents=db.query(Certificate).filter_by(organization_id=org.id).order_by(Certificate.id.desc()).limit(8).all()
    return render(req,'dashboard.html',db=db,user=user,org=org,stats={'count':count,'valid':valid,'month':month},
                  subscription=sub,recents=recents)


@app.get('/billing')
def billing(req:Request,db:Session=Depends(get_db),user=Depends(need_org)):
    plans=db.query(Plan).filter_by(is_active=True).order_by(Plan.price_usd).all()
    subs=db.query(Subscription).filter_by(organization_id=user.organization_id).order_by(Subscription.id.desc()).all()
    return render(req,'billing.html',db=db,user=user,plans=plans,subscriptions=subs,subscription=active_subscription(db,user.organization_id))


@app.post('/billing/request')
def request_plan(req:Request,plan_id:int=Form(...),payment_reference:str=Form(''),
                 db:Session=Depends(get_db),user=Depends(need_manager)):
    plan=db.get(Plan,plan_id)
    if not plan or not plan.is_active: raise HTTPException(400,'Unavailable plan')
    if db.query(Subscription).filter_by(organization_id=user.organization_id,status='pending').count():
        flash(req,'You already have a pending request','error');return go('/billing')
    sub=Subscription(organization_id=user.organization_id,plan_id=plan.id,
                     status='pending',payment_reference=payment_reference[:120].strip())
    db.add(sub);db.flush()
    audit(db,req,user,'subscription.requested',str(sub.id),details={'plan_id':plan.id})
    db.commit();flash(req,'Subscription request submitted. The platform administrator must verify payment and approve it.')
    return go('/billing')


@app.get('/team')
def team(req:Request,db:Session=Depends(get_db),user=Depends(need_org)):
    members=db.query(User).filter_by(organization_id=user.organization_id).order_by(User.id).all()
    return render(req,'team.html',db=db,user=user,members=members)


@app.post('/team')
def team_create(req:Request,email:str=Form(...),full_name:str=Form(...),
                password:str=Form(...),role:str=Form(...),db:Session=Depends(get_db),user=Depends(need_manager)):
    if role not in ('org_admin','designer','issuer','auditor'):raise HTTPException(400,'Invalid role')
    try:
        member=User(email=email.lower().strip(),full_name=full_name.strip()[:160],
          password_hash=password_hash(password),role=role,organization_id=user.organization_id)
        db.add(member);db.flush();audit(db,req,user,'team.created',str(member.id),details={'role':role})
        db.commit();flash(req,'Team member added')
    except (ValueError,IntegrityError):
        db.rollback();flash(req,'Invalid password or duplicate email (12+ password characters required)','error')
    return go('/team')


@app.post('/team/{member_id}/status')
def team_status(req:Request,member_id:int,status:str=Form(...),db:Session=Depends(get_db),user=Depends(need_manager)):
    member=db.get(User,member_id)
    assert_tenant(member,user)
    if member.id==user.id:raise HTTPException(400,'You cannot disable your own account')
    if status not in ('active','inactive'):raise HTTPException(400,'Invalid status')
    member.is_active=status=='active'
    audit(db,req,user,'team.status',str(member.id),details={'active':member.is_active})
    db.commit();return go('/team')


@app.get('/branding')
def branding(req:Request,db:Session=Depends(get_db),user=Depends(need_org)):
    org=db.get(Organization,user.organization_id)
    return render(req,'branding.html',db=db,user=user,org=org)


@app.post('/branding')
def branding_save(req:Request,name_ps:str=Form(''),name_fa:str=Form(''),
        logo:UploadFile|None=File(None),signature:UploadFile|None=File(None),
        db:Session=Depends(get_db),user=Depends(need_manager)):
    org=db.get(Organization,user.organization_id)
    org.name_ps=name_ps.strip()[:180];org.name_fa=name_fa.strip()[:180]
    if logo and logo.filename:org.logo_path=safe_upload(logo,db=db,organization_id=org.id)
    if signature and signature.filename:org.signature_path=safe_upload(signature,db=db,organization_id=org.id)
    audit(db,req,user,'branding.updated',str(org.id));db.commit()
    flash(req,'Branding updated');return go('/branding')


@app.get('/assets/{filename}')
def authorized_asset(filename:str,db:Session=Depends(get_db),user=Depends(need_user)):
    if not re.fullmatch(r'[0-9a-f]{40}\.png',filename):raise HTTPException(404,'Image not found')
    if user.role!='superadmin':
        allowed=(db.query(Organization).filter(Organization.id==user.organization_id,
            or_(Organization.logo_path==filename,Organization.signature_path==filename)).first() is not None or
                 db.query(CertificateTemplate).filter_by(organization_id=user.organization_id,background_path=filename).first() is not None)
        if not allowed:raise HTTPException(404,'Image not found')
    if os.getenv('STORAGE_BACKEND', 'filesystem') == 'database':
        stored=db.get(StoredFile,filename)
        if not stored or stored.media_type!='image/png':raise HTTPException(404,'Image not found')
        return Response(content=stored.payload, media_type='image/png',
                        headers={'Cache-Control':'private, max-age=120'})
    file=FILES_DIR/filename
    if not file.is_file():raise HTTPException(404,'Image not found')
    return FileResponse(file,media_type='image/png',headers={'Cache-Control':'private, max-age=120'})


@app.get('/templates/import')
def template_import_page(req:Request,db:Session=Depends(get_db),user=Depends(need_org)):
    return render(req,'template_import.html',db=db,user=user)


@app.post('/templates/import')
def template_import_submit(req:Request,name:str=Form(...),orientation:str=Form('landscape'),
    background:UploadFile=File(...),db:Session=Depends(get_db),user=Depends(need_editor)):
    if not name.strip() or len(name)>140:raise HTTPException(400,'Template name is required')
    if not background.filename:raise HTTPException(400,'Choose your own JPG, PNG or PDF template design')
    org=db.get(Organization,user.organization_id)
    template=CertificateTemplate(organization_id=org.id,category=org.category,
       name=name.strip(), config=make_design(org.category, 3,req.session.get('lang','en')),
       created_by=user.id)
    template.config={**template.config,'orientation':orientation if orientation in ('portrait','landscape') else 'landscape',
                     'catalog_index':None,'composition':4,'frame':2}
    # safe_upload converts uploaded PDF page 1 or a JPG/PNG into a constrained PNG.
    template.background_path=safe_upload(background,allow_pdf=True,db=db,organization_id=org.id)
    db.add(template);db.flush()
    audit(db,req,user,'template.imported',str(template.id))
    db.commit();flash(req,'Your custom certificate design is ready. Adjust the text and QR positions.')
    return go(f'/templates/{template.id}/edit')


@app.get('/templates/catalog')
def catalog_page(req:Request,category:str='',page:int=1,db:Session=Depends(get_db),user=Depends(need_org)):
    org=db.get(Organization,user.organization_id)
    category=category if category in CATEGORIES else org.category
    page=max(1,min(20,page))
    designs=[{'number':n,'config':make_design(category,n,req.session.get('lang','en'))} for n in range((page-1)*25+1,page*25+1)]
    return render(req,'catalog.html',db=db,user=user,designs=designs,category=category,page=page)


@app.post('/templates/catalog/create')
def catalog_choose(req:Request,category:str=Form(...),number:int=Form(...),name:str=Form(''),
        language:str=Form('en'),db:Session=Depends(get_db),user=Depends(need_editor)):
    org=db.get(Organization,user.organization_id)
    if category not in CATEGORIES or not 1<=number<=500:raise HTTPException(400,'Invalid catalog template')
    if language not in LANGUAGES: language='en'
    template=CertificateTemplate(organization_id=org.id, category=category,
        name=(name.strip() or f'{CATEGORIES[category]} • Design {number:03d}')[:140],
        config=make_design(category,number,language),created_by=user.id)
    db.add(template);db.flush()
    audit(db,req,user,'template.created',str(template.id),details={'catalog_number':number})
    db.commit();flash(req,'Template added. Customize text, positions and background.')
    return go(f'/templates/{template.id}/edit')


@app.get('/templates')
def template_list(req:Request,db:Session=Depends(get_db),user=Depends(need_org)):
    items=db.query(CertificateTemplate).filter_by(organization_id=user.organization_id).order_by(CertificateTemplate.id.desc()).all()
    return render(req,'templates.html',db=db,user=user,items=items)


@app.get('/templates/{template_id}/edit')
def template_edit(req:Request,template_id:int,db:Session=Depends(get_db),user=Depends(need_org)):
    template=assert_tenant(db.get(CertificateTemplate,template_id),user)
    return render(req,'designer.html',db=db,user=user,template=template,config=template.config)


@app.post('/templates/{template_id}/edit')
def template_save(req:Request,template_id:int,name:str=Form(...),design_json:str=Form(...),
          background:UploadFile|None=File(None),db:Session=Depends(get_db),user=Depends(need_editor)):
    template=assert_tenant(db.get(CertificateTemplate,template_id),user)
    try:
        config=sanitize_design(json.loads(design_json))
    except (ValueError,TypeError, json.JSONDecodeError) as exc:
        flash(req,'Design data is invalid: '+str(exc),'error');return go(f'/templates/{template_id}/edit')
    if background and background.filename:
        # Rasterize submitted PNG/JPG/PDF before storage; never run arbitrary HTML from uploads.
        template.background_path=safe_upload(background,allow_pdf=True,db=db,organization_id=template.organization_id)
    template.name=name.strip()[:140]
    if not template.name:raise HTTPException(400,'Template name required')
    template.config=config
    audit(db,req,user,'template.updated',str(template.id));db.commit()
    flash(req,'Template saved successfully')
    return go(f'/templates/{template_id}/edit')


@app.post('/templates/{template_id}/duplicate')
def duplicate_template(req:Request,template_id:int,db:Session=Depends(get_db),user=Depends(need_editor)):
    old=assert_tenant(db.get(CertificateTemplate,template_id),user)
    new=CertificateTemplate(organization_id=user.organization_id,name=(old.name+' (copy)')[:140],
            category=old.category,config=json.loads(json.dumps(old.config)),background_path=old.background_path,created_by=user.id)
    db.add(new);db.flush();audit(db,req,user,'template.duplicated',str(new.id));db.commit()
    flash(req,'Template duplicated');return go(f'/templates/{new.id}/edit')


@app.get('/certificates')
def certificate_list(req:Request,q:str='',db:Session=Depends(get_db),user=Depends(need_org)):
    query=db.query(Certificate).filter_by(organization_id=user.organization_id)
    if q:
        term=f'%{q[:100]}%'
        query=query.filter(or_(Certificate.serial.ilike(term),Certificate.recipient_en.ilike(term),
          Certificate.recipient_ps.ilike(term),Certificate.recipient_fa.ilike(term)))
    items=query.order_by(Certificate.id.desc()).limit(300).all()
    return render(req,'certificates.html',db=db,user=user,items=items,q=q)


@app.get('/certificates/new')
def issue_page(req:Request,db:Session=Depends(get_db),user=Depends(need_org)):
    org=db.get(Organization,user.organization_id)
    items=db.query(CertificateTemplate).filter_by(organization_id=org.id,is_active=True).order_by(CertificateTemplate.id.desc()).all()
    return render(req,'issue.html',db=db,user=user,templates_list=items,subscription=active_subscription(db,org.id),today=date.today().isoformat())


@app.post('/certificates/new')
def issue_certificate(req:Request,template_id:int=Form(...),recipient_en:str=Form(...),
        recipient_ps:str=Form(''),recipient_fa:str=Form(''),award:str=Form(...),
        program:str=Form(''),issue_date:str=Form(...),valid_until:str=Form(''),
        language:str=Form('en'),db:Session=Depends(get_db),user=Depends(need_issuer)):
    org=db.execute(select(Organization).where(Organization.id==user.organization_id).with_for_update()).scalar_one()
    template=assert_tenant(db.get(CertificateTemplate,template_id),user)
    if not template.is_active:raise HTTPException(400,'Template not active')
    try:
        details=parse_fields(recipient_en,recipient_ps,recipient_fa,award,program,issue_date,valid_until,language)
        cert=make_certificate(db,req,user,org,template,details)
        db.commit()
        flash(req,'Certificate generated and signed')
        return go(f'/certificates/{cert.id}')
    except Exception as exc:
        db.rollback()
        # Avoid information disclosure for unforeseen rendering failures.
        if isinstance(exc,ValueError): flash(req,str(exc),'error')
        else: flash(req,'Could not generate document; check the design, fonts and subscription','error')
        return go('/certificates/new')


@app.get('/certificates/bulk')
def bulk_page(req:Request,db:Session=Depends(get_db),user=Depends(need_org)):
    items=db.query(CertificateTemplate).filter_by(organization_id=user.organization_id,is_active=True).all()
    return render(req,'bulk.html',db=db,user=user,items=items)


@app.get('/certificates/sample.csv')
def bulk_sample(user=Depends(need_org)):
    csvfile='recipient_en,recipient_ps,recipient_fa,award,program,issue_date,valid_until,language\n'+(
       'Ahmad Safi,احمد صافی,احمد صافی,Completion of Python Course,Computer Science,2026-11-12,,en\n')
    return Response('\ufeff'+csvfile,media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition':'attachment; filename="certificate_sample.csv"'})


@app.post('/certificates/bulk')
def bulk_issue(req:Request,template_id:int=Form(...),csv_file:UploadFile=File(...),
          db:Session=Depends(get_db),user=Depends(need_issuer)):
    if not (csv_file.filename or '').lower().endswith('.csv'):
        flash(req,'Choose a .csv file','error');return go('/certificates/bulk')
    data=csv_file.file.read(1_000_001)
    if len(data)>1_000_000:flash(req,'CSV file must be under 1 MB','error');return go('/certificates/bulk')
    try:
        content=data.decode('utf-8-sig')
        reader=csv.DictReader(io.StringIO(content))
        required={'recipient_en','award','issue_date'}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError('Missing columns: '+', '.join(required))
        parsed=[]
        for rowno,row in enumerate(reader,start=2):
            if len(parsed)>=100:raise ValueError('Maximum 100 certificates per CSV. Split larger batches.')
            if None in row:raise ValueError(f'Row {rowno}: invalid number of columns')
            try:
                parsed.append(parse_fields(row.get('recipient_en') or '',row.get('recipient_ps') or '',
                    row.get('recipient_fa') or '',row.get('award') or '',row.get('program') or '',
                    row.get('issue_date') or '',row.get('valid_until') or '',row.get('language') or 'en'))
            except ValueError as ex:raise ValueError(f'Row {rowno}: {ex}') from ex
        if not parsed:raise ValueError('CSV has no records')
        org=db.execute(select(Organization).where(Organization.id==user.organization_id).with_for_update()).scalar_one()
        template=assert_tenant(db.get(CertificateTemplate,template_id),user)
        sub=require_issuing_capacity(db,org)
        if sub.plan.max_certificates is not None and sub.issued_count+len(parsed)>sub.plan.max_certificates:
            raise ValueError('CSV exceeds remaining certificate allowance')
        for record in parsed:
            make_certificate(db,req,user,org,template,record)
        audit(db,req,user,'certificate.bulk_issued',str(template.id),details={'count':len(parsed)})
        db.commit();flash(req,f'{len(parsed)} certificates successfully issued')
        return go('/certificates')
    except (UnicodeDecodeError,ValueError) as ex:
        db.rollback();flash(req,str(ex),'error')
        return go('/certificates/bulk')
    except Exception:
        db.rollback();flash(req,'Bulk operation was not completed. Check server logs for errors.','error')
        return go('/certificates/bulk')


@app.get('/certificates/export.csv')
def certificates_export(req:Request,db:Session=Depends(get_db),user=Depends(need_org)):
    # Spreadsheet formula prefix hardening: opening this export in Excel must not
    # execute text fields accidentally supplied by certificate recipients.
    def cell(v):
        text=str(v or '')
        return ("'"+text) if text.lstrip().startswith(('=','+','-','@')) else text
    buffer=io.StringIO()
    writer=csv.writer(buffer)
    writer.writerow(['serial','recipient_en','recipient_ps','recipient_fa','award','program',
                     'issue_date','valid_until','language','status','verification_url','pdf_sha256'])
    base=public_base_url(req)
    certs=(db.query(Certificate).filter_by(organization_id=user.organization_id)
           .order_by(Certificate.id.desc()).limit(20000).all())
    for cert in certs:
        writer.writerow([cell(cert.serial),cell(cert.recipient_en),cell(cert.recipient_ps),
          cell(cert.recipient_fa),cell(cert.award),cell(cert.program),str(cert.issue_date),
          str(cert.valid_until or ''),cert.language,cert.status,
          f'{base}/verify/{cert.public_token}',cert.pdf_sha256])
    audit(db,req,user,'certificate.export',details={'exported':len(certs)});db.commit()
    return Response(content='\ufeff'+buffer.getvalue(),media_type='text/csv; charset=utf-8',
       headers={'Content-Disposition':'attachment; filename="certificates_export.csv"',
                'Cache-Control':'private, no-store'})


@app.get('/certificates/{cert_id}')
def certificate_detail(req:Request,cert_id:int,db:Session=Depends(get_db),user=Depends(need_org)):
    cert=assert_tenant(db.get(Certificate,cert_id),user)
    base=public_base_url(req)
    verification_url=f'{base}/verify/{cert.public_token}'
    return render(req,'certificate_detail.html',db=db,user=user,cert=cert,
                  verify_url=verification_url,integrity=integrity_ok(cert),state=verification_state(cert))


@app.get('/certificates/{cert_id}/pdf')
def certificate_pdf(cert_id:int,db:Session=Depends(get_db),user=Depends(need_org)):
    cert=assert_tenant(db.get(Certificate,cert_id),user)
    if os.getenv('STORAGE_BACKEND', 'filesystem') == 'database':
        stored=db.get(StoredFile, Path(cert.pdf_path).name) if cert.pdf_path else None
        if not stored or stored.organization_id != user.organization_id or stored.media_type != 'application/pdf':
            raise HTTPException(404, 'PDF not found')
        if hashlib.sha256(stored.payload).hexdigest()!=cert.pdf_sha256:
            raise HTTPException(409, 'PDF checksum mismatch')
        return Response(content=stored.payload, media_type='application/pdf',
                        headers={'Content-Disposition':f'attachment; filename="{cert.serial}.pdf"',
                                 'Cache-Control':'private, no-store'})
    pdf=CERT_DIR/Path(cert.pdf_path).name
    if not cert.pdf_path or not pdf.is_file():raise HTTPException(404,'PDF not found')
    if hashlib.sha256(pdf.read_bytes()).hexdigest()!=cert.pdf_sha256:
        raise HTTPException(409,'PDF checksum mismatch')
    return FileResponse(pdf,media_type='application/pdf',filename=cert.serial+'.pdf',
                        headers={'Cache-Control':'private, no-store'})


@app.post('/certificates/{cert_id}/regenerate-pdf')
def regenerate_certificate_pdf(req:Request,cert_id:int,db:Session=Depends(get_db),
                               user=Depends(need_manager)):
    cert=assert_tenant(db.get(Certificate,cert_id),user)
    if not integrity_ok(cert):
        raise HTTPException(409, 'Cannot regenerate a certificate whose signed record has changed')
    # Keep the historical issuing institution's display names, even if it was renamed.
    from types import SimpleNamespace
    org=db.get(Organization,cert.organization_id)
    snap=cert.snapshot
    historical_org=SimpleNamespace(
        name=snap.get('organization_name',org.name),
        name_ps=snap.get('organization_name_ps',org.name_ps),
        name_fa=snap.get('organization_name_fa',org.name_fa))
    cert.pdf_path,cert.pdf_sha256=save_certificate_pdf(
        cert,historical_org,snap,public_base_url(req),db=db)
    audit(db,req,user,'certificate.pdf_regenerated',cert.serial,
          details={'reason':'QR public URL updated; signed data unchanged'})
    db.commit()
    flash(req,'Certificate PDF regenerated with the current HTTPS verification QR code')
    return go(f'/certificates/{cert.id}')


@app.post('/certificates/{cert_id}/revoke')
def revoke_certificate(req:Request,cert_id:int,reason:str=Form(...),
               db:Session=Depends(get_db),user=Depends(need_manager)):
    cert=assert_tenant(db.get(Certificate,cert_id),user)
    if cert.status=='revoked':raise HTTPException(400,'Certificate is already revoked')
    if len(reason.strip())<5:raise HTTPException(400,'Reason must be at least five characters')
    cert.status='revoked';cert.revoked_at=utcnow();cert.revoked_reason=reason.strip()[:1000]
    audit(db,req,user,'certificate.revoked',cert.serial,details={'reason':cert.revoked_reason})
    db.commit();flash(req,'Certificate revoked. Its QR link now reports revocation.')
    return go(f'/certificates/{cert.id}')


def verified_record(db,token,req):
    if not re.fullmatch(r'[A-Za-z0-9_-]{20,64}',token):return None, 'not_found'
    # Do not store raw network addresses. A database-backed limiter works across workers.
    iphash=hash_ip(req.client.host if req.client else '')
    since=utcnow()-timedelta(hours=1)
    if db.query(VerificationEvent).filter(VerificationEvent.ip_hash==iphash,
                                        VerificationEvent.created_at>=since).count()>120:
        raise HTTPException(429,'Verification rate limit reached')
    cert=db.query(Certificate).filter_by(public_token=token).first()
    db.add(VerificationEvent(certificate_id=cert.id if cert else None,ip_hash=iphash));db.commit()
    return cert, verification_state(cert) if cert else 'not_found'


@app.get('/verify/{token}')
def public_verify(req:Request,token:str,db:Session=Depends(get_db)):
    cert,state=verified_record(db,token,req)
    return render(req,'verify.html',db=db,cert=cert,verify_state=state,org=cert.organization if cert else None)


@app.get('/api/verify/{token}')
def verification_api(req:Request,token:str,db:Session=Depends(get_db)):
    cert,state=verified_record(db,token,req)
    if not cert:return JSONResponse({'status':'not_found'},status_code=404)
    return JSONResponse({'status':state,'serial':cert.serial,'organization':cert.snapshot.get('organization_name', cert.organization.name),
      'recipient':cert.recipient_en,'recipient_ps':cert.recipient_ps,'recipient_fa':cert.recipient_fa,
      'award':cert.award,'program':cert.program,'issue_date':cert.issue_date.isoformat(),
      'valid_until':cert.valid_until.isoformat() if cert.valid_until else None,
      'pdf_sha256':cert.pdf_sha256 if state in ('valid','expired','revoked') else None},
      headers={'Cache-Control':'no-store'})


@app.get('/audit')
def audit_page(req:Request,db:Session=Depends(get_db),user=Depends(need_org)):
    rows=db.query(AuditEvent).filter_by(organization_id=user.organization_id).order_by(AuditEvent.id.desc()).limit(250).all()
    return render(req,'audit.html',db=db,user=user,events=rows)


@app.get('/admin/audit')
def admin_audit(req:Request,db:Session=Depends(get_db),user=Depends(need_admin)):
    rows=db.query(AuditEvent).order_by(AuditEvent.id.desc()).limit(300).all()
    return render(req,'audit.html',db=db,user=user,events=rows)


@app.get('/certificates/{cert_id}/qr.png')
def certificate_qr(req:Request,cert_id:int,db:Session=Depends(get_db),user=Depends(need_org)):
    import qrcode
    cert=assert_tenant(db.get(Certificate,cert_id),user)
    base=public_base_url(req)
    url=f'{base}/verify/{cert.public_token}'
    qr=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=16,border=4)
    qr.add_data(url);qr.make(fit=True)
    stream=io.BytesIO();qr.make_image(fill_color='black',back_color='white').save(stream,format='PNG')
    return Response(content=stream.getvalue(),media_type='image/png',headers={'Cache-Control':'private, no-store'})


@app.get('/profile')
def profile_page(req:Request,db:Session=Depends(get_db),user=Depends(need_user)):
    return render(req,'profile.html',db=db,user=user)


@app.post('/profile/password')
def change_password(req:Request,old_password:str=Form(...),new_password:str=Form(...),
                    db:Session=Depends(get_db),user=Depends(need_user)):
    if not password_verify(old_password,user.password_hash):
        flash(req,'Current password is incorrect','error');return go('/profile')
    if old_password==new_password:
        flash(req,'Choose a different password','error');return go('/profile')
    try:user.password_hash=password_hash(new_password)
    except ValueError as exc:
        flash(req,str(exc),'error');return go('/profile')
    audit(db,req,user,'auth.password_changed',str(user.id))
    db.commit();flash(req,'Password updated successfully')
    return go('/profile')


@app.post('/team/{member_id}/password')
def manager_reset_password(req:Request,member_id:int,password:str=Form(...),
                           db:Session=Depends(get_db),user=Depends(need_manager)):
    member=assert_tenant(db.get(User,member_id),user)
    if member.id==user.id:raise HTTPException(400,'Use Profile to change your own password')
    try:member.password_hash=password_hash(password)
    except ValueError:
        flash(req,'Password requires at least 12 characters','error');return go('/team')
    audit(db,req,user,'team.password_reset',str(member.id))
    db.commit();flash(req,'Team member password reset. Share the new password securely.')
    return go('/team')


@app.get('/admin/users')
def admin_users(req:Request,db:Session=Depends(get_db),user=Depends(need_admin)):
    users=db.query(User).order_by(User.id.desc()).limit(300).all()
    return render(req,'admin_users.html',db=db,user=user,users=users)


@app.post('/admin/users/{user_id}/password')
def admin_reset_password(req:Request,user_id:int,password:str=Form(...),
                           db:Session=Depends(get_db),user=Depends(need_admin)):
    target=db.get(User,user_id)
    if not target:raise HTTPException(404,'User not found')
    if target.id==user.id:raise HTTPException(400,'Use Profile to change your own password')
    try:target.password_hash=password_hash(password)
    except ValueError:
        flash(req,'Password requires at least 12 characters','error');return go('/admin/users')
    audit(db,req,user,'admin.password_reset',str(target.id),organization_id=target.organization_id)
    db.commit();flash(req,'Password reset. Notify the user through a secure channel.')
    return go('/admin/users')


@app.post('/admin/users/{user_id}/status')
def admin_user_status(req:Request,user_id:int,status:str=Form(...),
                      db:Session=Depends(get_db),user=Depends(need_admin)):
    target=db.get(User,user_id)
    if not target:raise HTTPException(404,'User not found')
    if target.id==user.id:raise HTTPException(400,'You cannot disable your own account')
    if status not in ('active','inactive'):raise HTTPException(400,'Invalid status')
    target.is_active=status=='active'
    audit(db,req,user,'admin.user_status',str(target.id),organization_id=target.organization_id,
          details={'active':target.is_active})
    db.commit();return go('/admin/users')
