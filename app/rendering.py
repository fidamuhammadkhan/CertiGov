import base64, html, io, hashlib, os
from pathlib import Path
import qrcode
from weasyprint import HTML

DATA_DIR = Path(os.getenv('DATA_DIR', './data')).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
FILES_DIR = DATA_DIR / 'files'
FILES_DIR.mkdir(exist_ok=True)
CERT_DIR = DATA_DIR / 'certificates'
CERT_DIR.mkdir(exist_ok=True)


def data_image(path, db=None):
    if not path: return ''
    if os.getenv('STORAGE_BACKEND', 'filesystem') == 'database':
        if db is None: return ''
        from .models import StoredFile
        stored = db.get(StoredFile, Path(path).name)
        if not stored or stored.media_type != 'image/png': return ''
        data = stored.payload
    else:
        file = (FILES_DIR / Path(path).name).resolve()
        if file.parent != FILES_DIR or not file.exists(): return ''
        data = file.read_bytes()
    return 'data:image/png;base64,' + base64.b64encode(data).decode('ascii')


def qr_image(url):
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=16, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(fill_color='black', back_color='white').convert('RGB')
    buf = io.BytesIO()
    image.save(buf, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def cert_text(cert, org, key):
    lang = cert.language
    name = getattr(cert, 'recipient_'+lang, '') or cert.recipient_en
    orgname = getattr(org, 'name_'+lang, '') or org.name
    from .catalog import LABELS
    mapping = {
      '{{certificate_title}}': LABELS.get(cert.snapshot.get('config', {}).get('category','university'), LABELS['university']).get(lang, LABELS['university']['en']),
      '{{certifies}}': {'en':'This certifies that','ps':'دا تصدیق کوي چې','fa':'بدینوسیله تصدیق می‌شود که'}.get(lang,'This certifies that'),
      '{{org}}': orgname, '{{recipient}}': name,
      '{{award}}': cert.award, '{{program}}': cert.program,
      '{{date}}': cert.issue_date.isoformat(),
      '{{serial}}': cert.serial,
      '{{valid_until}}': cert.valid_until.isoformat() if cert.valid_until else '',
      '{{signer}}': 'Authorized signature',
    }
    result = key
    for a,b in mapping.items(): result = result.replace(a, b or '')
    return result


def certificate_html(cert, org, config, background_path, logo_path, signature_path, verify_url, db=None):
    # Validate that the immutable snapshot contains only constrained structural content.
    from .catalog import sanitize_design
    c = sanitize_design(config)
    bg = data_image(background_path, db)
    logo = data_image(logo_path, db)
    signature = data_image(signature_path, db)
    qr = qr_image(verify_url)
    portrait = c['orientation'] == 'portrait'
    paper_size = '210mm 297mm' if portrait else '297mm 210mm'
    width = '210mm' if portrait else '297mm'
    height = '297mm' if portrait else '210mm'
    frame_styles = [
      'border: 12px double '+c['accent']+'; outline:3px solid '+c['primary']+';outline-offset:-24px;',
      'border: 11px solid '+c['primary']+'; outline:2px solid '+c['accent']+';outline-offset:-23px;',
      'border: 7px solid '+c['accent']+';outline:5px solid '+c['primary']+';outline-offset:-18px;',
      'border-top:15px solid '+c['primary']+';border-bottom:15px solid '+c['primary']+';border-left:4px solid '+c['accent']+';border-right:4px solid '+c['accent']+';',
      'border:10px ridge '+c['accent']+'; outline:2px solid '+c['primary']+';outline-offset:-19px;',
    ][c['frame']]
    # Decorative presentation changes by family without granting arbitrary CSS/HTML input.
    motifs=[
        '',
        f'background-image:linear-gradient(115deg,{c["paper"]} 75%,{c["accent"]}22 75%);',
        f'background-image:radial-gradient(circle at 85% 10%,{c["accent"]}28 0%,transparent 32%);',
        f'background-image:linear-gradient(90deg,{c["primary"]} 0 4%,{c["paper"]} 4% 100%);',
        f'background-image:linear-gradient(135deg,{c["paper"]} 85%,{c["accent"]}33 85%);',
    ]
    if bg and c['artwork_mode']:
        frame_styles = '' # Full imported art remains unchanged by platform borders.
    motif=motifs[c['pattern']] if not bg else ''
    rtl = cert.language in ('ps','fa')
    rendered=[]
    for item in c['elements']:
        if not item['visible']: continue
        kind=item['kind']
        css=(f"left:{item['x']}%;top:{item['y']}%;width:{item['w']}%;"
             f"font-size:{item['size']}px;color:{item['color']};text-align:{item['align']};"
             f"font-weight:{item['weight']};")
        content=''
        if kind == 'mask':
            css += f"height:{item['h']}%;background-color:{item['color']};"
        if kind == 'line':
            content=f'<div style="width:100%;border-top:2px solid {c["accent"]}"></div>'
        elif kind == 'mask':
            content = ''
        elif kind == 'logo':
            content=f'<img alt="logo" src="{logo}" style="max-width:100%;max-height:100%;height:auto;object-fit:contain">' if logo else '<span>◆</span>'
        elif kind == 'signature':
            content=f'<img alt="signature" src="{signature}" style="max-width:100%;max-height:100%;object-fit:contain">' if signature else '_________________'
        elif kind == 'qr':
            content=f'<img alt="verification QR" src="{qr}" style="width:100%;height:auto;object-fit:contain">'
        else:
            txt = html.escape(cert_text(cert,org,item['text']))
            content=f'<span>{txt}</span>'
        rendered.append(f'<div class="element {kind}" dir="{"rtl" if rtl else "ltr"}" style="{css}">{content}</div>')
    background_fit={'contain':'contain','cover':'cover','stretch':'100% 100%'}[c['background_fit']]
    bg_css = f'background-image:url("{bg}");background-size:{background_fit};background-position:center;background-repeat:no-repeat;' if bg else ''
    return f'''<!doctype html><html lang="{html.escape(cert.language)}"><head><meta charset="utf-8">
    <style>@page{{size:{paper_size};margin:0}}html,body{{margin:0;padding:0}}
    body{{font-family:'Noto Sans Arabic','Noto Naskh Arabic','DejaVu Sans',sans-serif}}
    .sheet{{box-sizing:border-box;position:relative;width:{width};height:{height};overflow:hidden;
      background-color:{c['paper']};{frame_styles}{motif}{bg_css}}}
    .element{{position:absolute;box-sizing:border-box;line-height:1.36;word-break:normal;overflow-wrap:anywhere;}}
    .element.qr img{{display:block}}.element.logo,.element.signature{{height:14%}}
    .element.qr{{height:20%;background:#fff;padding:3px}}.element.line{{height:1%}}
    </style></head><body><div class="sheet">{''.join(rendered)}</div></body></html>'''


def save_certificate_pdf(cert, org, snapshot, public_base_url, db=None):
    url = f'{public_base_url.rstrip("/")}/verify/{cert.public_token}'
    markup = certificate_html(cert,org,snapshot['config'],snapshot.get('background_path',''),
                              snapshot.get('logo_path',''),snapshot.get('signature_path',''),url, db=db)
    pdf = HTML(string=markup).write_pdf()
    filename = f'{cert.public_token}.pdf'
    if os.getenv('STORAGE_BACKEND', 'filesystem') == 'database':
        if db is None: raise RuntimeError('A database session is required')
        from .models import StoredFile
        db.merge(StoredFile(name=filename, organization_id=cert.organization_id,
                            media_type='application/pdf', payload=pdf))
    else:
        target = CERT_DIR / filename
        target.write_bytes(pdf)
    return filename, hashlib.sha256(pdf).hexdigest()
