"""Isolated v5 regression exercises; run with `python tests/v5_smoke.py`."""
import os,sys,tempfile,re,io,json
from pathlib import Path
from datetime import date
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
_tmp=tempfile.TemporaryDirectory();os.environ.update({
'DATABASE_URL':'sqlite:///'+str(Path(_tmp.name)/'qa.db'),
'DATA_DIR':str(Path(_tmp.name)/'assets'),
'STORAGE_BACKEND':'database',
'APP_SECRET':'v5_qa_session_'+'S'*45,
'CERT_SIGNING_KEY':'v5_qa_hmac_'+'Q'*45,
'PUBLIC_BASE_URL':'http://testserver',
'PRODUCTION':'false'})
from fastapi.testclient import TestClient
from app.main import app,SessionLocal, password_hash, integrity_ok
from app.rendering import certificate_html
from app.models import Plan,Organization,User,Subscription,CertificateTemplate,Certificate,CertificateCategory,StoredFile,AuditEvent
from app.catalog import make_design,sanitize_design
import pypdfium2 as pdfium

def token(client):
 response=client.get('/login')
 assert response.status_code==200
 return re.search(r'name="csrf" value="([^"]+)"',response.text).group(1)

def post(c,url,data={},files=None,expected=200):
 data={**data,'csrf':token(c)}
 r=c.post(url,data=data,files=files,follow_redirects=True)
 assert r.status_code==expected,(url,r.status_code,r.text[-700:])
 return r

def login(c,email,pw):
 return post(c,'/login',{'email':email,'password':pw})

def png():
 out=io.BytesIO();Image.new('RGB',(180,240),'#cfdaeb').save(out,'PNG');return out.getvalue()

with TestClient(app) as c:
 with SessionLocal() as db:
  root=User(email='root@v5.test',full_name='Platform Admin',role='superadmin',password_hash=password_hash('V5-Super-Administrator-2026'))
  db.add(root);db.commit()
 assert 'Platform Control' in login(c,'root@v5.test','V5-Super-Administrator-2026').text
 assert 'Edit plan' in c.get('/admin/plans').text
 plan_id=post(c,'/admin/plans',{'name':'Pilot Plus','price_usd':'29.50','duration_days':'180','max_certificates':'10'})
 with SessionLocal() as db:plan=db.query(Plan).filter_by(name='Pilot Plus').one();pid=plan.id
 post(c,f'/admin/plans/{pid}/edit',{'name':'Pilot Gold','price_usd':'39.50','duration_days':'365','max_certificates':'20'})
 with SessionLocal() as db:assert db.get(Plan,pid).name=='Pilot Gold'
 post(c,f'/admin/plans/{pid}/status',{'status':'archived'})
 assert 'Pilot Gold' not in c.get('/plans').text
 post(c,f'/admin/plans/{pid}/status',{'status':'active'})
 assert 'Pilot Gold' in c.get('/plans').text
 post(c,'/admin/organizations',{'name':'Example Institute','name_ps':'','name_fa':'','slug':'example-inst','code':'EXI',
         'category':'university','admin_name':'Org Manager','admin_email':'org@v5.test','admin_password':'V5-Manager-Password-2026'})
 with SessionLocal() as db:org=db.query(Organization).filter_by(code='EXI').one();oid=org.id
 post(c,f'/admin/organizations/{oid}/edit',{'name':'Example Education','name_ps':'','name_fa':'','category':'training'})
 assert 'Example Education' in c.get('/admin/organizations').text
 c.post('/logout',data={'csrf':token(c)})
 login(c,'org@v5.test','V5-Manager-Password-2026')
 assert 'Certificate Categories' in c.get('/categories').text
 post(c,'/categories',{'name':'Training Awards','slug':'training-awards','description':'Workshops and training'})
 with SessionLocal() as db:cat=db.query(CertificateCategory).filter_by(organization_id=oid).one();cid=cat.id
 post(c,f'/categories/{cid}/edit',{'name':'Training and Workshops','description':'Seminars and courses'})
 assert 'Training and Workshops' in c.get('/categories').text
 r=post(c,'/templates/catalog/create',{'category':'university','number':'23','language':'en','name':'Portrait and fields'})
 with SessionLocal() as db:
  tmpl=db.query(CertificateTemplate).filter_by(organization_id=oid).one();tid=tmpl.id
  config=dict(tmpl.config)
  config['variables']=[{'key':'student_id','label':'Student ID','required':True},{'key':'faculty','label':'Faculty','required':False}]
  config['elements']=config['elements']+[
   {'kind':'photo','text':'','x':75,'y':20,'w':15,'h':25,'size':10,'color':'#102a43','visible':True},
   {'kind':'text','text':'ID: {{field:student_id}}','x':25,'y':85,'w':50,'h':8,'size':20,'color':'#102a43','visible':True},
   {'kind':'logo','text':'','x':5,'y':5,'w':16,'h':14,'size':11,'color':'#102a43','visible':True},
   {'kind':'text','text':'Category: {{category}}','x':27,'y':89,'w':50,'h':9,'size':15,'color':'#102a43','visible':True},]
 post(c,f'/templates/{tid}/edit',{'name':'Portrait and fields','design_json':json.dumps(config)})
 r=c.get('/certificates/new');assert 'Student ID' in r.text and 'field__' in r.text or 'template-variables' in r.text
 # approve a real subscription
 post(c,'/billing/request',{'plan_id':pid,'payment_reference':'QA-2026'})
 c.post('/logout',data={'csrf':token(c)});login(c,'root@v5.test','V5-Super-Administrator-2026')
 with SessionLocal() as db:sub=db.query(Subscription).filter_by(organization_id=oid).one();sid=sub.id
 post(c,f'/admin/subscriptions/{sid}/review',{'decision':'approve'})
 assert 'already processed' in post(c,f'/admin/subscriptions/{sid}/review',{'decision':'approve'}).text
 c.post('/logout',data={'csrf':token(c)});login(c,'org@v5.test','V5-Manager-Password-2026')
 r=post(c,'/certificates/new',{'template_id':tid,'recipient_en':'Sample Student','recipient_ps':'','recipient_fa':'',
       'award':'Certified AI Training','program':'Computer Science','issue_date':'2026-11-23','valid_until':'',
       'language':'en','category_id':cid,'field__student_id':'STD-12345','field__faculty':'Engineering'},
       files={'recipient_photo':('portrait.png',png(),'image/png')})
 assert 'Example Education' in r.text or 'EXI-2026' in r.text,r.text[-900:]
 with SessionLocal() as db:
  cert=db.query(Certificate).one();certid=cert.id
  assert cert.category_id==cid and cert.custom['values']['student_id']=='STD-12345'
  assert cert.snapshot['recipient_photo_path'].endswith('.png')
  assert integrity_ok(cert)
  stored=db.get(StoredFile,cert.snapshot['recipient_photo_path']);assert stored and stored.organization_id==oid
  markup=certificate_html(cert,cert.organization,cert.snapshot['config'],cert.snapshot['background_path'],
      cert.snapshot['logo_path'],cert.snapshot['signature_path'],'https://example.org/verify/test',db=db,
      photo_path=cert.snapshot['recipient_photo_path'])
  assert 'STD-12345' in markup and 'data:image/png;base64' in markup
  assert '{{field:student_id}}' not in markup
 pdf=c.get(f'/certificates/{certid}/pdf');assert pdf.status_code==200 and pdf.content[:4]==b'%PDF'
 doc=pdfium.PdfDocument(io.BytesIO(pdf.content));assert len(doc)==1
 pdftext=doc[0].get_textpage().get_text_range();assert 'STD-12345' in pdftext,pdftext[-500:]
 doc.close()
 assert c.get('/certificates?category='+str(cid)).status_code==200
 assert 'Sample Student' in c.get('/certificates?category='+str(cid)).text
 assert 'Sample Student' not in c.get('/certificates?category=uncategorized').text
 assert 'Sample Student' in c.get('/certificates?date_from=2026-11-01&date_to=2026-11-30').text
 assert 'Sample Student' not in c.get('/certificates?date_from=2027-01-01').text
 assert 'Training and Workshops' in c.get('/certificates/export.csv?category='+str(cid)).text
 post(c,f'/categories/{cid}/delete',{})
 with SessionLocal() as db:assert db.get(CertificateCategory,cid).is_active is False
 assert c.get('/categories').status_code==200
 # tenant isolation
 with SessionLocal() as db:
  other=Organization(name='Other Tenant',slug='other-tenant',code='OTH',category='school')
  db.add(other);db.flush()
  db.add(User(email='other@v5.test',full_name='Other User',password_hash=password_hash('V5-Other-Password-2026'),role='org_admin',organization_id=other.id));db.commit()
 c.post('/logout',data={'csrf':token(c)});login(c,'other@v5.test','V5-Other-Password-2026')
 assert c.get('/certificates?category='+str(cid)).status_code==400
 assert c.post(f'/categories/{cid}/edit',data={'csrf':token(c),'name':'Attack','description':''}).status_code==404
 assert c.get(f'/certificates/{certid}').status_code==404
 # missing csrf fails, stale csrf redirects to safe page, token renewal endpoint works
 assert c.post('/billing/request',data={'plan_id':pid,'payment_reference':'x'}).status_code==403
 assert c.get('/api/session/csrf').json()['csrf']
 r=c.post('/billing/request',data={'plan_id':pid,'payment_reference':'x','csrf':'stale-token'})
 assert r.status_code==200 and any(h.status_code==303 for h in r.history)
print('V5 SMOKE PASSED: plans, categories, tenant-isolation, issuer photo + variables, PDF, filters, CSRF, approvals')
