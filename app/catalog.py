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
    # Real composition families: each changes the placement and hierarchy, not just colors.
    def pos(key,x=None,y=None,w=None,size=None,align=None):
        e=next(z for z in elements if z['id']==key)
        for field,value in (('x',x),('y',y),('w',w),('size',size),('align',align)):
            if value is not None:e[field]=value
    if layout==1:  # modern left editorial
        pos('logo',8,7,12);pos('org',24,9,70,20,'left');pos('line',9,27,22)
        pos('title',9,32,82,42,'left');pos('subtitle',9,50,80,18,'left')
        pos('recipient',9,58,80,36,'left');pos('description',9,70,76,19,'left')
        pos('program',9,78,67,15,'left');pos('signature',66,83,15)
    elif layout==2: # dramatic center seal
        pos('logo',46,6,8);pos('title',10,19,80,47);pos('org',12,37,76,22)
        pos('subtitle',16,50,68,17);pos('recipient',10,56,80,42);pos('description',13,69,74,20)
        pos('line',31,47,38)
    elif layout==3: # asymmetric modern right
        pos('logo',78,7,12);pos('org',7,8,65,19,'left');pos('title',7,27,74,43,'left')
        pos('subtitle',7,44,70,17,'left');pos('recipient',7,52,77,43,'left')
        pos('description',7,68,75,21,'left');pos('program',7,79,65,16,'left');pos('line',7,21,27)
    elif layout==4: # stacked compact minimal
        pos('logo',8,9,10);pos('org',22,10,68,19,'left');pos('title',15,29,70,46)
        pos('subtitle',25,48,50,18);pos('recipient',13,56,74,41);pos('description',13,72,74,17)
        pos('line',30,26,40);pos('serial',16,91,40,12,'left')
    elif layout==5: # luxury upper left
        pos('logo',9,7,11);pos('org',23,9,70,21,'left');pos('title',7,31,80,51,'left')
        pos('subtitle',7,51,75,17,'left');pos('recipient',7,59,75,41,'left')
        pos('description',7,74,77,21,'left');pos('line',7,27,78)
    elif layout==6: # academic top banner
        pos('logo',8,5,12);pos('org',24,8,65,25,'left');pos('title',12,32,76,38)
        pos('line',25,46,50);pos('subtitle',25,52,50,18)
        pos('recipient',12,60,76,36);pos('description',12,73,76,18)
    elif layout==7: # art deco side balance
        pos('logo',45,9,10);pos('org',14,23,72,23);pos('title',13,36,74,44)
        pos('subtitle',20,52,60,19);pos('recipient',15,61,70,39)
        pos('description',19,74,62,17);pos('line',42,31,16)
    elif layout==8: # clean corporate letterhead
        pos('logo',9,10,10);pos('org',23,10,68,21,'left');pos('line',9,26,82)
        pos('title',9,36,80,39,'left');pos('subtitle',9,49,75,19,'left')
        pos('recipient',9,58,80,36,'left');pos('description',9,72,75,19,'left')
        pos('program',9,80,72,15,'left')
    elif layout==9: # bold centered cover
        pos('logo',45,6,10);pos('org',15,18,70,22);pos('title',9,33,82,49)
        pos('subtitle',20,51,60,17);pos('recipient',13,60,74,44)
        pos('description',18,76,64,18);pos('line',28,29,44)
    return {'version': 2,'catalog_index': index,'category':category, 'language':language,
       'composition':layout,'pattern':p%5,
       'paper':paper,'primary':primary,'accent':accent,'frame':frame,
       'orientation':'landscape', 'elements':elements}


def sanitize_design(obj):
    """Accept only structural, bounded editor JSON; no HTML/CSS/URLs from users."""
    if not isinstance(obj, dict): raise ValueError('Invalid design JSON')
    allowed_kind = {'text','qr','logo','signature','line','mask'}
    out = {k: obj.get(k) for k in ('version','catalog_index','category','language')}
    for prop in ('paper','primary','accent'):
        value = obj.get(prop, '#ffffff')
        if not isinstance(value,str) or len(value)!=7 or value[0]!='#' or any(c not in '0123456789abcdefABCDEF' for c in value[1:]):
            raise ValueError('Invalid design color')
        out[prop] = value
    out['frame'] = min(4,max(0,int(obj.get('frame',0))))
    out['composition']=min(9,max(0,int(obj.get('composition',0))))
    out['pattern']=min(4,max(0,int(obj.get('pattern',0))))
    out['orientation'] = obj.get('orientation') if obj.get('orientation') in ('portrait','landscape') else 'landscape'
    out['artwork_mode'] = bool(obj.get('artwork_mode',False))
    out['background_fit'] = obj.get('background_fit') if obj.get('background_fit') in ('contain','cover','stretch') else 'contain'
    arr = obj.get('elements', [])
    if not isinstance(arr,list) or len(arr)>45: raise ValueError('Too many fields')
    out['elements'] = []
    for i,e in enumerate(arr):
        if not isinstance(e,dict) or e.get('kind') not in allowed_kind: continue
        def num(name, maximum, default):
            try: return max(0, min(maximum, float(e.get(name,default))))
            except (ValueError,TypeError): return default
        out['elements'].append({'id': f'field_{i}', 'kind':e['kind'],
          'text':str(e.get('text',''))[:400], 'x':min(87,num('x',99,5)) if e['kind']=='qr' else num('x',99,5),
          'y':num('y',99,5),'w':max(13 if e['kind']=='qr' else 2,num('w',100,30)),
          'size':max(7,num('size',90,18)), 'h':max(2,num('h',70,10)),
          'color':e['color'] if isinstance(e.get('color'),str) and len(e['color'])==7 and e['color'].startswith('#') and all(c in '0123456789abcdefABCDEF' for c in e['color'][1:]) else out['primary'],
          'weight':'bold' if e.get('weight')=='bold' else 'normal',
          'align':e.get('align') if e.get('align') in ('left','right','center') else 'center',
          'visible':bool(e.get('visible',True))})
    if not out['elements']: raise ValueError('Design requires at least one element')
    return out
