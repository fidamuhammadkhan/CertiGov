import os
import tempfile
import io
import json
import pypdfium2 as pdfium
from pathlib import Path

# Keep test data separate from any real installation; set before importing app modules.
_TMP = tempfile.TemporaryDirectory()
os.environ['DATABASE_URL']='sqlite:///'+str(Path(_TMP.name)/'test.db')
os.environ['DATA_DIR']=str(Path(_TMP.name)/'assets')
os.environ['APP_SECRET']='test_app_secret_'+'x'*46
os.environ['CERT_SIGNING_KEY']='test_signing_key_'+'y'*46
os.environ['PUBLIC_BASE_URL']='http://testserver'

from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app, SessionLocal, password_hash, integrity_ok, verification_state, make_design
from app.models import Organization, User, Certificate, Subscription, CertificateTemplate, Plan


def csrf(client):
    # HTML is intentionally public to the local test client.
    import re
    body=client.get('/login').text
    return re.search(r'name="csrf" value="([^"]+)"',body).group(1)


def login(client,email,password,token):
    return client.post('/login',data={'csrf':token,'email':email,'password':password},follow_redirects=True)


def test_end_to_end():
  with TestClient(app) as c:
    with SessionLocal() as db:
      db.add(User(email='root@certigov.test',full_name='Root',role='superadmin',password_hash=password_hash('Temporary-Root-Pass-2026')))
      db.commit()
    token=csrf(c)
    r=login(c,'root@certigov.test','Temporary-Root-Pass-2026',token)
    assert 'Platform Control' in r.text
    token=csrf(c)
    r=c.post('/admin/organizations',data={'csrf':token,'name':'Bakhtar University','name_ps':'باختر پوهنتون',
       'name_fa':'دانشگاه باختر','slug':'bakhtar','code':'BAK','category':'university',
       'admin_name':'University Admin','admin_email':'admin@bakhtar.test','admin_password':'Temporary-University-2026'},follow_redirects=True)
    assert 'Bakhtar University' in r.text
    with SessionLocal() as db:
      org=db.query(Organization).filter_by(code='BAK').one()
      assert org.id>0
    c.post('/logout',data={'csrf':token})
    token=csrf(c)
    r=login(c,'admin@bakhtar.test','Temporary-University-2026',token)
    assert 'Organization Workspace' in r.text
    r=c.get('/language/ps',follow_redirects=True)
    assert 'dir="rtl"' in r.text and 'ډشبورډ' in r.text
    token=csrf(c)
    r=c.post('/templates/catalog/create',data={'csrf':token,'category':'university','number':'234',
        'language':'ps','name':'Official Test Template'},follow_redirects=True)
    assert 'د سند ژوندی سمونګر' in r.text
    with SessionLocal() as db:
      tmpl=db.query(CertificateTemplate).filter_by(organization_id=org.id).one()
    # The visual editor saves validated JSON and rasterizes a user-supplied PDF background.
    from weasyprint import HTML
    pdf_background=HTML(string='<html><body><h1>Background</h1></body></html>').write_pdf()
    r=c.post(f'/templates/{tmpl.id}/edit', data={'csrf':token,'name':'Official Test Template',
       'design_json':json.dumps(tmpl.config)},
       files={'background':('template.pdf',pdf_background,'application/pdf')},follow_redirects=True)
    assert r.status_code==200 and ('قالب' in r.text), r.text[-500:]
    with SessionLocal() as db:
       tmp=db.get(CertificateTemplate,tmpl.id)
       assert tmp.background_path.endswith('.png')
       assert c.get('/assets/'+tmp.background_path).status_code==200
    # Issuing before payment approval must not generate a certificate.
    r=c.post('/certificates/new',data={'csrf':token,'template_id':tmpl.id,'recipient_en':'Amin',
      'recipient_ps':'امین','recipient_fa':'امین','award':'Completed AI','program':'AI','issue_date':'2026-11-12',
      'valid_until':'','language':'ps'},follow_redirects=True)
    with SessionLocal() as db:assert db.query(Certificate).count()==0
    r=c.post('/billing/request',data={'csrf':token,'plan_id':2,'payment_reference':'BANK-2026-123'},follow_redirects=True)
    assert 'BANK-2026-123' in r.text
    c.post('/logout',data={'csrf':token})
    token=csrf(c)
    login(c,'root@certigov.test','Temporary-Root-Pass-2026',token)
    token=csrf(c)
    with SessionLocal() as db:sub=db.query(Subscription).filter_by(organization_id=org.id).one()
    r=c.post(f'/admin/subscriptions/{sub.id}/review',data={'csrf':token,'decision':'approve'},follow_redirects=True)
    assert 'active' in r.text
    c.post('/logout',data={'csrf':token})
    token=csrf(c)
    login(c,'admin@bakhtar.test','Temporary-University-2026',token)
    token=csrf(c)
    r=c.post('/certificates/new',data={'csrf':token,'template_id':tmpl.id,'recipient_en':'Amin Safi',
      'recipient_ps':'امین صافی','recipient_fa':'امین صافی','award':'Completed AI Research Workshop',
      'program':'Research','issue_date':'2026-11-12','valid_until':'2027-11-12','language':'ps'},follow_redirects=True)
    assert 'BAK-2026-0000001' in r.text, r.text[-1000:]
    with SessionLocal() as db:
      cert=db.query(Certificate).one()
      assert integrity_ok(cert)
      assert cert.pdf_sha256 and cert.pdf_path.endswith('.pdf')
      token_public=cert.public_token
      cert_id=cert.id
    pdf=c.get(f'/certificates/{cert_id}/pdf')
    assert pdf.status_code==200 and pdf.content[:4]==b'%PDF'
    assert len(pdf.content)>8000
    doc=pdfium.PdfDocument(io.BytesIO(pdf.content))
    assert len(doc)==1, f'Expected one A4 page, got {len(doc)}'
    extracted=doc[0].get_textpage().get_text_range()
    assert 'امین' in extracted, f'Pashto content not available in extracted PDF text: {extracted[:400]!r}'
    demo_dir=Path(__file__).resolve().parents[1]/'docs'
    demo_dir.mkdir(exist_ok=True)
    doc[0].render(scale=1.4).to_pil().save(demo_dir/'sample_pashto_certificate.png')
    qr=c.get(f'/certificates/{cert_id}/qr.png')
    assert qr.status_code==200 and qr.content[:8]==b'\x89PNG\r\n\x1a\n'
    r=c.get('/verify/'+token_public)
    assert 'Authentic certificate' in r.text or 'اصلي سند' in r.text
    info=c.get('/api/verify/'+token_public).json()
    assert info['status']=='valid' and info['recipient_ps']=='امین صافی'
    # Rebuild a document issued with a private URL to use a public HTTPS QR link.
    from unittest.mock import patch
    with patch.dict(os.environ, {'PUBLIC_BASE_URL':'https://certigov-example.onrender.com'}):
      r=c.post(f'/certificates/{cert_id}/regenerate-pdf',data={'csrf':token},follow_redirects=True)
      assert r.status_code==200 and 'regenerated' in r.text
      regenerated=c.get(f'/certificates/{cert_id}/pdf').content
      new_doc=pdfium.PdfDocument(io.BytesIO(regenerated))
      assert len(new_doc)==1
      # The public QR route responds with a real, printable image.
      renewed_qr=c.get(f'/certificates/{cert_id}/qr.png')
      assert renewed_qr.status_code==200
      try:
        import cv2
      except ImportError:
        pass
      else:
        import numpy as np
        image = cv2.imdecode(np.frombuffer(renewed_qr.content, dtype=np.uint8), cv2.IMREAD_COLOR)
        decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(image)
        assert decoded == f'https://certigov-example.onrender.com/verify/{token_public}'
        # Crucial check: the QR still scans after being embedded into an A4 PDF.
        pdf_page = np.asarray(new_doc[0].render(scale=2).to_pil().convert('RGB'))
        actual_pdf_url, _, _ = cv2.QRCodeDetector().detectAndDecode(
          cv2.cvtColor(pdf_page, cv2.COLOR_RGB2BGR))
        assert actual_pdf_url == decoded
      with SessionLocal() as db:
        assert integrity_ok(db.get(Certificate,cert_id))
    # A database mutation of an issued field must cause integrity failure.
    with SessionLocal() as db:
      modified=db.get(Certificate,cert_id);modified.recipient_en='Altered!';db.commit()
    assert c.get('/api/verify/'+token_public).json()['status']=='integrity_failed'
    with SessionLocal() as db:
      modified=db.get(Certificate,cert_id);modified.recipient_en='Amin Safi';db.commit()
    r=c.post(f'/certificates/{cert_id}/revoke',data={'csrf':token,'reason':'Credential withdrawn'},follow_redirects=True)
    assert 'revoked' in r.text
    assert c.get('/api/verify/'+token_public).json()['status']=='revoked'
    # Bulk CSV: all rows validate first, and a quota cap applies to the whole import.
    with SessionLocal() as db:
      plan=db.get(Plan,2)
      plan.max_certificates=3
      db.commit()
    content='recipient_en,recipient_ps,recipient_fa,award,program,issue_date,valid_until,language\n'
    content+='Zarmina,زرمنه,زرمنه,Academic Merit,Mathematics,2026-11-12,,ps\n'
    content+='Safi,صافي,صافی,Research Attendance,Computing,2026-11-12,,fa\n'
    r=c.post('/certificates/bulk',data={'csrf':token,'template_id':tmpl.id},
        files={'csv_file':('batch.csv',content.encode('utf-8'),'text/csv')},follow_redirects=True)
    with SessionLocal() as db:
      assert db.query(Certificate).count()==3, r.text[-800:]
      sub=db.query(Subscription).one()
      assert sub.issued_count==3
    r=c.post('/certificates/new',data={'csrf':token,'template_id':tmpl.id,'recipient_en':'Over limit',
      'award':'Test','program':'Test','issue_date':'2026-11-12','valid_until':'','language':'en'},follow_redirects=True)
    with SessionLocal() as db: assert db.query(Certificate).count()==3
    export=c.get('/certificates/export.csv')
    assert export.status_code==200 and export.text.count('Academic Merit')==1
    # An unrelated tenant must not read certificates or uploaded design files.
    with SessionLocal() as db:
      other=Organization(name='Unrelated School',slug='other-school',code='OTHER',category='school')
      db.add(other);db.flush()
      db.add(User(email='other@example.test',full_name='Other Admin',
          password_hash=password_hash('Other-Admin-Strong-2026'),role='org_admin',organization_id=other.id))
      db.commit()
    c.post('/logout',data={'csrf':token})
    token=csrf(c)
    login(c,'other@example.test','Other-Admin-Strong-2026',token)
    assert c.get(f'/certificates/{cert_id}/pdf').status_code==404
    assert c.get(f'/certificates/{cert_id}').status_code==404
    assert c.get('/assets/'+tmp.background_path).status_code==404
    assert c.get('/verify/'+token_public).status_code==200
    # Cookie-authenticated state changes require CSRF token.
    assert c.post('/billing/request',data={'plan_id':1,'payment_reference':'test'}).status_code==403
    token=csrf(c)
    assert c.get('/profile').status_code==200
    changed=c.post('/profile/password',data={'csrf':token,
      'old_password':'Other-Admin-Strong-2026','new_password':'Other-Admin-New-Strong-2026'},follow_redirects=True)
    assert changed.status_code==200
    c.post('/logout',data={'csrf':token})
    token=csrf(c)
    assert 'Organization Workspace' in login(c,'other@example.test','Other-Admin-New-Strong-2026',token).text
    # Issuer cannot visit superadmin UI.
    assert c.get('/admin/organizations').status_code==403
    # Logo background upload and limited CSV path.
    assert c.get('/certificates/sample.csv').status_code==200
    assert make_design('school',500)['catalog_index']==500
