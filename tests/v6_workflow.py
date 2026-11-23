"""CertiGov v6 draft/correction/archive and artwork regression. Uses temporary fake data."""
import io,os,re,tempfile,sys,json
from datetime import datetime,timedelta
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
working=tempfile.TemporaryDirectory()
os.environ.update({'DATABASE_URL':'sqlite:///'+str(Path(working.name)/'certigov_v6_test.db'),
 'DATA_DIR':str(Path(working.name)/'data'),'STORAGE_BACKEND':'database',
 'APP_SECRET':'V6QA-SESSION-'+'X'*48,'CERT_SIGNING_KEY':'V6QA-SIGNING-'+'Y'*48,
 'PUBLIC_BASE_URL':'http://testserver','PRODUCTION':'false'})
from fastapi.testclient import TestClient
from app.main import app,SessionLocal,integrity_ok
from app.security import password_hash
from app.models import Organization,User,Plan,Subscription,CertificateTemplate,Certificate,CertificateDraft,CertificateRecordState,StoredFile
from app.catalog import make_design

def csrf(client):
 r=client.get('/login');assert r.status_code==200
 t=re.search(r'name="csrf" value="([^\"]+)"',r.text)
 assert t, r.text[:300]
 return t.group(1)
def post(client,path,data=None,files=None,expected=200):
 body={'csrf':csrf(client),**(data or {})}
 r=client.post(path,data=body,files=files,follow_redirects=True)
 assert r.status_code==expected,(path,r.status_code,r.url,r.text[:700])
 return r

with TestClient(app) as c:
 with SessionLocal() as db:
  org=Organization(name='Example University',slug='example-v6',code='EXV',category='university')
  db.add(org);db.flush();orgid=org.id
  user=User(email='org@v6.example',full_name='Org Admin',role='org_admin',organization_id=orgid,password_hash=password_hash('V6-Test-Correct-Horse-2026'))
  issuer=User(email='issuer@v6.example',full_name='Issuer',role='issuer',organization_id=orgid,password_hash=password_hash('V6-Test-Issuer-Password'))
  outsider=Organization(name='Other University',slug='other-v6',code='OTH',category='university')
  db.add_all([user,issuer,outsider]);db.flush()
  other=User(email='outside@v6.example',full_name='Other',role='org_admin',organization_id=outsider.id,password_hash=password_hash('V6-Test-Outside-Passphrase'))
  plan=Plan(name='V6 QA',price_usd=0,duration_days=365,max_certificates=200)
  db.add_all([other,plan]);db.flush()
  db.add(Subscription(organization_id=orgid,plan_id=plan.id,status='active',issued_count=0,start_at=datetime.utcnow()-timedelta(days=3),expire_at=datetime.utcnow()+timedelta(days=300)))
  template=CertificateTemplate(organization_id=orgid,created_by=user.id,name='Demo template',category='university',config=make_design('university',3,'en'))
  db.add(template);db.commit();tid=template.id
 assert 'Dashboard' in post(c,'/login',{'email':'org@v6.example','password':'V6-Test-Correct-Horse-2026'}).text
 assert c.get('/certificates/drafts').status_code==200
 draft=post(c,'/certificates/drafts/save',{'template_id':str(tid),'recipient_en':'Draft Student','award':'Workshop','issue_date':'2026-11-23','language':'en','category_id':''})
 assert 'Draft Student' in draft.text
 with SessionLocal() as db:
  items=db.query(CertificateDraft).all();assert len(items)==1;d=items[0];did=d.id;assert d.form_values['recipient_en']=='Draft Student'
 assert 'Draft Student' in c.get(f'/certificates/drafts/{did}/edit').text
 # Modify and save draft before issuing; editing an unissued draft does not make a registry certificate.
 post(c,'/certificates/drafts/save',{'draft_id':str(did),'template_id':str(tid),'recipient_en':'Edited Student','award':'AI Workshop','issue_date':'2026-11-23','language':'en'})
 with SessionLocal() as db:assert db.query(Certificate).count()==0
 # Issue saved draft as an actual signed certificate.
 r=post(c,'/certificates/new',{'draft_id':str(did),'source_certificate_id':'0','template_id':str(tid),'recipient_en':'Edited Student','award':'AI Workshop','issue_date':'2026-11-23','language':'en'})
 assert 'Edited Student' in r.text,r.text[:400]
 with SessionLocal() as db:
  assert db.query(CertificateDraft).count()==0
  orig=db.query(Certificate).one();oldid=orig.id;oldtoken=orig.public_token
  assert integrity_ok(orig)
 assert c.get(f'/api/verify/{oldtoken}').json()['status']=='valid'
 # Create a draft correction and issue replacement.
 correction=c.get(f'/certificates/{oldid}/correct');assert correction.status_code==200
 assert 'Edited Student' in correction.text
 post(c,'/certificates/drafts/save',{'source_certificate_id':str(oldid),'template_id':str(tid),'recipient_en':'Corrected Student','award':'AI Workshop','issue_date':'2026-11-23','language':'en'})
 with SessionLocal() as db:
  correction_draft=db.query(CertificateDraft).one();correction_id=correction_draft.id
 r=post(c,'/certificates/new',{'draft_id':str(correction_id),'source_certificate_id':str(oldid),'template_id':str(tid),'recipient_en':'Corrected Student','award':'AI Workshop','issue_date':'2026-11-23','language':'en'})
 assert 'Corrected Student' in r.text
 with SessionLocal() as db:
  old=db.get(Certificate,oldid);new=db.query(Certificate).filter(Certificate.id!=oldid).one()
  assert old.status=='revoked' and integrity_ok(old) and integrity_ok(new)
  state=db.get(CertificateRecordState,oldid);assert state and state.replacement_certificate_id==new.id
  assert old.pdf_sha256 and new.pdf_sha256
  newid=new.id;newtoken=new.public_token
 assert c.get(f'/api/verify/{oldtoken}').json()['status']=='revoked'
 assert c.get(f'/api/verify/{newtoken}').json()['status']=='valid'
 assert 'Verify corrected certificate' in c.get(f'/verify/{oldtoken}').text
 # Duplicating an issued certificate produces an editable draft only.
 duplicate=post(c,f'/certificates/{newid}/duplicate')
 assert 'Edit certificate draft' in duplicate.text
 with SessionLocal() as db:
  duplicate_draft=db.query(CertificateDraft).one()
  assert duplicate_draft.source_certificate_id is None
  assert duplicate_draft.form_values['recipient_en']=='Corrected Student'
  copy_id=duplicate_draft.id
 post(c,f'/certificates/drafts/{copy_id}/delete')
 with SessionLocal() as db:assert db.query(CertificateDraft).count()==0
 # Reissuing the revoked original is forbidden.
 assert c.get(f'/certificates/{oldid}/correct').status_code==409
 post(c,f'/certificates/{newid}/archive',{'status':'archive'})
 assert 'Corrected Student' not in c.get('/certificates').text
 assert 'Corrected Student' in c.get('/certificates?archived=yes').text
 assert c.get(f'/api/verify/{newtoken}').json()['status']=='valid'
 post(c,f'/certificates/{newid}/archive',{'status':'restore'})
 assert 'Corrected Student' in c.get('/certificates').text
 # The issued item must have no destructive delete route.
 assert c.post(f'/certificates/{newid}/delete',data={'csrf':csrf(c)}).status_code in (404,405)
 # Other tenant isolation
 post(c,'/logout')
 post(c,'/login',{'email':'outside@v6.example','password':'V6-Test-Outside-Passphrase'})
 assert c.get(f'/certificates/{newid}/correct').status_code==404
 assert c.get(f'/certificates/{newid}').status_code==404
 assert c.get(f'/certificates/drafts/{did}/edit').status_code==404
 assert c.post(f'/certificates/{newid}/archive',data={'status':'archive','csrf':csrf(c)}).status_code==404
 # Role restriction: issuer cannot correct/archive.
 post(c,'/logout')
 post(c,'/login',{'email':'issuer@v6.example','password':'V6-Test-Issuer-Password'})
 assert c.get(f'/certificates/{newid}/correct').status_code==403
 assert c.post(f'/certificates/{newid}/archive',data={'status':'archive','csrf':csrf(c)}).status_code==403
 print('V6 WORKFLOW PASSED: save/edit/delete drafts; correct-and-reissue; immutable original; revoke/verify QR; archive/restore; tenant and role isolation')
