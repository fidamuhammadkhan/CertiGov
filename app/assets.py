import io, secrets, os
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError
from fastapi import HTTPException
from .rendering import FILES_DIR

MAX_SIZE = 10*1024*1024
Image.MAX_IMAGE_PIXELS = 20_000_000


def safe_upload(up, allow_pdf=False, db=None, organization_id=None):
    name = (up.filename or '').lower()
    if not (name.endswith('.png') or name.endswith('.jpg') or name.endswith('.jpeg') or (allow_pdf and name.endswith('.pdf'))):
        raise HTTPException(400, 'Allowed formats: PNG, JPG'+(', PDF' if allow_pdf else ''))
    raw = up.file.read(MAX_SIZE+1)
    if not raw or len(raw)>MAX_SIZE:
        raise HTTPException(400,'Upload must be between 1 byte and 10 MB')
    is_pdf = raw.startswith(b'%PDF-')
    if is_pdf and not (allow_pdf and name.endswith('.pdf')):
        raise HTTPException(400, 'PDF is not allowed for this image')
    try:
        if is_pdf:
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(io.BytesIO(raw))
            if len(doc)<1 or len(doc)>50: raise ValueError('PDF must have 1–50 pages')
            page=doc[0]
            bitmap=page.render(scale=min(2.0, 4000.0/max(page.get_size())),rev_byteorder=True)
            img=bitmap.to_pil()
        else:
            # Do not rely on the claimed MIME type; decode & re-encode safe raster.
            img=Image.open(io.BytesIO(raw))
            if img.format not in ('PNG','JPEG'): raise ValueError('Not a PNG or JPEG')
            img.load()
        img=ImageOps.exif_transpose(img)
        if img.width*img.height>20_000_000: raise ValueError('Image exceeds 20 MP')
        img.thumbnail((4000,4000))
        img=img.convert('RGBA')
        output=io.BytesIO();img.save(output,'PNG',optimize=True)
    except (ValueError, OSError, UnidentifiedImageError, Exception) as ex:
        # Image decoders are attack surfaces; production should sandbox/AV-scan as well.
        raise HTTPException(400, 'Image/PDF could not be safely decoded') from ex
    filename = secrets.token_hex(20)+'.png'
    data = output.getvalue()
    if os.getenv('STORAGE_BACKEND', 'filesystem') == 'database':
        if db is None or organization_id is None:
            raise RuntimeError('Database storage requires a database session and organization ID')
        from .models import StoredFile
        db.add(StoredFile(name=filename, organization_id=organization_id,
                          media_type='image/png', payload=data))
    else:
        (FILES_DIR / filename).write_bytes(data)
    return filename
