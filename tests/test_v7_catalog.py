"""Catalog layout regression: new designs should not place text fields on top of each other."""
from app.catalog import make_design, sanitize_design

def test_all_ten_composition_families_have_non_overlapping_text_boxes():
    for layout in range(10):
        config = make_design('university', layout*5+1, 'en')
        # Reproducible server-side sanitization is the same path used at save time.
        cleaned = sanitize_design(config)
        elements = [e for e in cleaned['elements'] if e['kind'] == 'text']
        for i, a in enumerate(elements):
            for b in elements[i+1:]:
                overlap_x = max(0, min(a['x']+a['w'], b['x']+b['w']) - max(a['x'],b['x']))
                overlap_y = max(0, min(a['y']+a['h'], b['y']+b['h']) - max(a['y'],b['y']))
                assert overlap_x <= min(a['w'],b['w'])*.1 or overlap_y <= 2, (layout,a['text'],b['text'],overlap_y)
        qr = next(e for e in cleaned['elements'] if e['kind']=='qr')
        assert qr['w']>=13 and qr['h']>=20 and qr['x']+qr['w']<=100
