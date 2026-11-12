"""500 deterministic customizable templates per sector: 10 palettes × 10 layouts × 5 frame treatments."""
from copy import deepcopy

CATEGORIES = {
    'university': 'University', 'school': 'School', 'government': 'Government',
    'training': 'Training Institute', 'business': 'Private Company',
    'ngo': 'NGO / Foundation', 'hospital': 'Hospital', 'association': 'Association',
}
PALETTES = [
    ('#0e365f','#d5ae61','#f8f8f3'), ('#263c32','#b3a274','#fffdf8'),
    ('#5e2040','#d6a35a','#fcf7f6'), ('#163a4b','#76b5c5','#f5fafc'),
    ('#292d55','#dbb96b','#fafafc'), ('#492923','#c6a57b','#fff9f3'),
    ('#164b43','#8ec8b5','#f2faf6'), ('#363246','#ada1cb','#f9f7fc'),
    ('#222c35','#c9b48e','#fafafa'), ('#6a403e','#e7b99e','#fff7f4'),
]

LABELS = {
    'university': {'en':'Certificate of Achievement','ps':'د لاسته راوړنې سند','fa':'تصدیق‌نامه دستاورد'},
    'school': {'en':'Certificate of Excellence','ps':'د غوره والي سند','fa':'تصدیق‌نامه شایستگی'},
    'government': {'en':'Official Certificate','ps':'رسمي تصدیق‌پاڼه','fa':'تصدیق‌نامه رسمی'},
    'training': {'en':'Certificate of Completion','ps':'د بشپړولو سند','fa':'تصدیق‌نامه فراغت'},
    'business': {'en':'Recognition Certificate','ps':'د ستاینې سند','fa':'تصدیق‌نامه تقدیر'},
    'ngo': {'en':'Certificate of Appreciation','ps':'د مننې سند','fa':'تقدیرنامه'},
    'hospital': {'en':'Professional Certificate','ps':'مسلکي سند','fa':'تصدیق‌نامه مسلکی'},
    'association': {'en':'Membership Certificate','ps':'د غړیتوب سند','fa':'تصدیق‌نامه عضویت'},
}


def el(key, text, x, y, w, size, color='#183145', weight='normal', align='center', kind='text'):
    return {'id': key,'kind': kind,'text': text,'x': x,'y': y,'w': w,
            'size': size,'color': color,'weight':weight,'align':align,'visible':True}


def make_design(category='university', index=1, language='en'):
    if category not in CATEGORIES: category = 'university'
    if not 1 <= int(index) <= 500: raise ValueError('Catalog number must be 1–500')
    index = int(index)
    p = (index-1) // 50
    layout = ((index-1)//5) % 10
    frame = (index-1) % 5
    primary, accent, paper = PALETTES[p]
    yshift = [-2,0,2,1,-1,0,-2,2,-1,1][layout]
    title = LABELS[category].get(language, LABELS[category]['en'])
    elements = [
      el('logo','{{logo}}',46,4,8,36,kind='logo'),
      el('org','{{org}}',10,9+yshift,80,25,primary,'bold'),
      el('line','',17,20+yshift,66,2,accent,kind='line'),
      el('title','{{certificate_title}}',8,25+yshift,84,40,primary,'bold'),
      el('subtitle','{{certifies}}',14,42+yshift,72,19,primary),
      el('recipient','{{recipient}}',12,51+yshift,76,35,primary,'bold'),
      el('description','{{award}}',15,63+yshift,70,21,primary),
      el('program','{{program}}',15,72+yshift,70,16,primary),
      el('date','{{date}}',8,87,20,13,primary,align='left'),
      el('signature','{{signature}}',43,79,14,22,kind='signature'),
      el('serial','{{serial}}',33,92,34,11,primary),
      el('qr','{{qr}}',84,77,11,20,kind='qr'),
    ]
    if layout in (2,7):
        elements[0]['x'] = 8; elements[1]['y'] = 10; elements[1]['x'] = 20; elements[1]['w'] = 75
    if layout in (3,8):
        elements[3]['size'] = 36; elements[5]['size'] = 40; elements[5]['y'] += 2
    if layout in (4,9):
        elements[3]['y'] += 5; elements[4]['y'] += 4; elements[5]['y'] += 4
    if layout in (5,6):
        elements[2]['x'] = 33; elements[2]['w'] = 34
        elements[3]['y'] += 2
    return {'version': 1,'catalog_index': index,'category':category, 'language':language,
       'paper':paper,'primary':primary,'accent':accent,'frame':frame,
       'orientation':'landscape', 'elements':elements}


def sanitize_design(obj):
    """Accept only structural, bounded editor JSON; no HTML/CSS/URLs from users."""
    if not isinstance(obj, dict): raise ValueError('Invalid design JSON')
    allowed_kind = {'text','qr','logo','signature','line'}
    out = {k: obj.get(k) for k in ('version','catalog_index','category','language')}
    for prop in ('paper','primary','accent'):
        value = obj.get(prop, '#ffffff')
        if not isinstance(value,str) or len(value)!=7 or value[0]!='#' or any(c not in '0123456789abcdefABCDEF' for c in value[1:]):
            raise ValueError('Invalid design color')
        out[prop] = value
    out['frame'] = min(4,max(0,int(obj.get('frame',0))))
    out['orientation'] = obj.get('orientation') if obj.get('orientation') in ('portrait','landscape') else 'landscape'
    arr = obj.get('elements', [])
    if not isinstance(arr,list) or len(arr)>45: raise ValueError('Too many fields')
    out['elements'] = []
    for i,e in enumerate(arr):
        if not isinstance(e,dict) or e.get('kind') not in allowed_kind: continue
        def num(name, maximum, default):
            try: return max(0, min(maximum, float(e.get(name,default))))
            except (ValueError,TypeError): return default
        out['elements'].append({'id': f'field_{i}', 'kind':e['kind'],
          'text':str(e.get('text',''))[:400], 'x':num('x',99,5),
          'y':num('y',99,5),'w':max(2,num('w',100,30)),
          'size':max(7,num('size',90,18)),
          'color':e['color'] if isinstance(e.get('color'),str) and len(e['color'])==7 and e['color'].startswith('#') and all(c in '0123456789abcdefABCDEF' for c in e['color'][1:]) else out['primary'],
          'weight':'bold' if e.get('weight')=='bold' else 'normal',
          'align':e.get('align') if e.get('align') in ('left','right','center') else 'center',
          'visible':bool(e.get('visible',True))})
    if not out['elements']: raise ValueError('Design requires at least one element')
    return out
