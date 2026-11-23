"""Standalone browser validation of the authenticated designer. Uses fictional credentials and SQLite."""
from pathlib import Path
import os,sys,re,tempfile
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
work=tempfile.TemporaryDirectory()
os.environ.update({'DATABASE_URL':'sqlite:///'+str(Path(work.name)/'v7.db'),'DATA_DIR':str(Path(work.name)/'files'),'STORAGE_BACKEND':'database','PRODUCTION':'false','APP_SECRET':'V7-TEST-SESSION-'+'X'*45,'CERT_SIGNING_KEY':'V7-TEST-SIGNING-'+'Y'*45,'PUBLIC_BASE_URL':'http://testserver'})
from fastapi.testclient import TestClient
from app.main import app,SessionLocal
from app.models import Organization,User,CertificateTemplate
from app.catalog import make_design,sanitize_design
from app.security import password_hash
with TestClient(app) as client:
 with SessionLocal() as db:
  org=Organization(name='Demo Learning Institute',slug='demo-learning',code='DLI',category='university');db.add(org);db.flush()
  user=User(email='v7-qa@example.invalid',full_name='Demo Designer',role='org_admin',organization_id=org.id,password_hash=password_hash('Temporary-V7-Demo-12345'));db.add(user);db.flush()
  tmpl=CertificateTemplate(organization_id=org.id,name='Demo University Certificate',category='university',config=make_design('university',1,'en'),created_by=user.id);db.add(tmpl);db.commit();template_id=tmpl.id
 login=client.get('/login');token=re.search('name="csrf" value="([^"]+)"',login.text).group(1)
 client.post('/login',data={'csrf':token,'email':'v7-qa@example.invalid','password':'Temporary-V7-Demo-12345'})
 html=client.get(f'/templates/{template_id}/edit').text
 assert 'designer.js?v=7' in html and 'Sample data for live preview' in html
 soup=BeautifulSoup(html,'html.parser')
 for node in soup.select('link[href],script[src]'):node.decompose()
 style=soup.new_tag('style');style.string=(ROOT/'app/static/style.css').read_text();soup.head.append(style)
 markup=str(soup)
 with sync_playwright() as browser_api:
  b=browser_api.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  for viewport in [{'width':1580,'height':950},{'width':420,'height':880}]:
   pg=b.new_page(viewport=viewport)
   issues=[];pg.on('pageerror',lambda e:issues.append(str(e)))
   pg.set_content(markup,wait_until='load')
   pg.add_script_tag(content=(ROOT/'app/static/designer.js').read_text())
   pg.wait_for_timeout(120)
   assert pg.locator('#designer-status').inner_text().startswith('Editor ready'),pg.locator('#designer-status').inner_text()
   assert pg.locator('#certificate-canvas .canvas-element').count()==12
   assert pg.locator('#layer-list button').count()==12
   # The selected field changes the preview immediately.
   pg.locator('#preview-recipient').fill('Fatima Demo Student')
   assert 'Fatima Demo Student' in pg.locator('#certificate-canvas').inner_text()
   pg.locator('#preview-program').fill('Diploma in Computing')
   assert 'Diploma in Computing' in pg.locator('#certificate-canvas').inner_text()
   before=pg.locator('#certificate-canvas .canvas-element').count()
   pg.locator('#preset-field').select_option('program');pg.locator('#add-field').click()
   assert pg.locator('#certificate-canvas .canvas-element').count()==before
   assert 'already exists' in pg.locator('#designer-status').inner_text()
   # Add an actual new free-text element; existing presets should not duplicate.
   pg.locator('#add-text').click()
   assert pg.locator('#certificate-canvas .canvas-element').count()==before+1
   pg.locator('#new-variable-key').fill('student_id');pg.locator('#new-variable-label').fill('Student ID')
   pg.locator('#add-variable').click()
   assert pg.locator('#variable-list input.variable-example').count()==1
   pg.locator('#variable-list input.variable-example').fill('DEMO-042')
   assert 'DEMO-042' in pg.locator('#certificate-canvas').inner_text()
   # Save stores placeholders, never sample student data.
   pg.evaluate('''() => document.getElementById('design-form').addEventListener('submit', e => e.preventDefault())''')
   pg.locator('.designer-toolbar button[type=submit]').click()
   saved=pg.locator('#design-json').input_value()
   assert '{{field:student_id}}' in saved and '{{program}}' in saved
   assert 'Fatima Demo Student' not in saved and 'DEMO-042' not in saved
   conf=sanitize_design(__import__('json').loads(saved))
   assert len(conf['elements'])==14
   assert conf['variables'][0]['key']=='student_id'
   # Page does not horizontally overflow viewport (sidebar may scroll).
   assert not issues, issues
   print('V7 BROWSER PASSED',viewport['width'],'canvas objects',len(conf['elements']))
   pg.close()
  b.close()
print('V7 SAMPLE DATA NOT PERSISTED; ALL CONTROLS TESTED')
