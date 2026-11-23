/* CertiGov v5 — organization-owned interactive certificate design studio.
   Structural only: no injected HTML, no external network templates, no executable user code. */
(()=>{'use strict';
const data=document.getElementById('design-data'), canvas=document.getElementById('certificate-canvas'), props=document.getElementById('element-properties');
if(!data||!canvas||!props)return;
let config;try{config=JSON.parse(data.textContent)}catch(e){return}
config.elements=config.elements||[];config.variables=config.variables||[];
const ctl=id=>document.getElementById(id);
const paper=ctl('paper'),primary=ctl('primary'),accent=ctl('accent'),orientation=ctl('orientation'),frame=ctl('frame'),pattern=ctl('pattern'),fit=ctl('background-fit');
const bgInput=document.querySelector('input[name=background]');
const initialBg=canvas.dataset.background||'';
const organizationLogo=canvas.dataset.logo||'';
let imageUrl=initialBg,selected=null,drag=null,undo=[];
const labels={en:{recipient:'Student Name',org:'Organization Name',award:'Award description',program:'Program or course',date:'2026-11-23',serial:'BAK-2026-00001',valid_until:'—',category:'Certificate category',certificate_title:'Certificate of Achievement',certifies:'This certifies that',signer:'Authorized signature'},ps:{recipient:'د زده کوونکي نوم',org:'د ادارې نوم',award:'د سند موخه',program:'د پروګرام نوم',date:'۱۴۰۵-۰۹-۰۲',serial:'BAK-2026-00001',category:'د سند کټګوري'},fa:{recipient:'نام دانشجو',org:'نام اداره',award:'موضوع سند',program:'نام برنامه',date:'۱۴۰۵-۰۹-۰۲',serial:'BAK-2026-00001',category:'دسته سند'}};
const clamp=(v,min,max)=>Math.min(max,Math.max(min,Number(v)||0));
function remember(){undo.push(JSON.stringify(config));if(undo.length>25)undo.shift()}
function elem(kind,text='',x=35,y=38,w=35,h=12,size=25){return {id:'element_'+Date.now()+'_'+Math.random().toString(36).slice(2,6),kind,text,x,y,w,h,size,rotate:0,opacity:1,font:'sans',color:config.primary,weight:'normal',align:'center',visible:true}}
function add(kind,text='',x=35,y=38,w=35,h=12,size=25){remember();config.elements.push(elem(kind,text,x,y,w,h,size));selected=config.elements.length-1;paint();properties()}
function resolved(value){const lang=labels[config.language]||labels.en;return String(value||'').replace(/\{\{([^{}]+)\}\}/g,(m,k)=>{k=k.trim();if(k.startsWith('field:'))return (config.variables.find(v=>v.key===k.slice(6))?.label||k.slice(6))+' (dynamic)';return lang[k]||labels.en[k]||m})}
function canvasStyle(){const portrait=config.orientation==='portrait';canvas.classList.toggle('portrait',portrait);canvas.style.backgroundColor=config.paper;
 const border=['10px double '+config.accent,'11px solid '+config.primary,'6px solid '+config.accent,'12px solid '+config.primary,'10px ridge '+config.accent];
 canvas.style.border=(imageUrl&&config.artwork_mode)?'0':(border[config.frame]||border[0]);
 canvas.style.backgroundPosition='center';canvas.style.backgroundRepeat='no-repeat';canvas.style.backgroundSize=({contain:'contain',cover:'cover',stretch:'100% 100%'})[config.background_fit||'contain'];
 const motifs=['none',`linear-gradient(115deg, ${config.paper} 75%, ${config.accent}22 75%)`,`radial-gradient(circle at 85% 10%, ${config.accent}28 0%, transparent 32%)`,`linear-gradient(90deg, ${config.primary} 0 4%, ${config.paper} 4% 100%)`,`linear-gradient(135deg, ${config.paper} 85%, ${config.accent}33 85%)`];
 canvas.style.backgroundImage=imageUrl?`url("${imageUrl}")`:motifs[config.pattern||0];
 paper.value=config.paper;primary.value=config.primary;accent.value=config.accent;orientation.value=config.orientation;frame.value=String(config.frame);pattern.value=String(config.pattern||0);fit.value=config.background_fit||'contain';
}
function paint(){canvasStyle();canvas.replaceChildren();const scale=canvas.clientWidth/(config.orientation==='portrait'?794:1122);
 config.elements.forEach((e,i)=>{
  if(e.visible===false)return;
  const div=document.createElement('div');div.className='canvas-element '+e.kind+(i===selected?' active':'');div.dataset.index=i;
  Object.assign(div.style,{left:e.x+'%',top:e.y+'%',width:e.w+'%',height:(e.h||10)+'%',fontSize:Math.max(7,e.size*scale)+'px',color:e.color,textAlign:e.align,fontWeight:e.weight,fontFamily:({sans:'Arial,sans-serif',serif:'Georgia,serif',mono:'monospace',arabic:'Tahoma,sans-serif'}[e.font]||'sans-serif'),opacity:e.opacity??1,transform:`rotate(${e.rotate||0}deg)`,direction:config.language==='en'?'ltr':'rtl',touchAction:'none'});
  if(e.kind==='qr'){div.textContent='▦ SCAN TO VERIFY';div.style.background='#fff';div.style.color='#152d43';div.style.fontSize='12px';div.style.padding='5px';div.style.minWidth='44px';}
  else if(e.kind==='mask'){div.style.background=e.color;div.title='Mask covers old printed text'}
  else if(e.kind==='line'){div.style.height='2px';div.style.background=e.color}
  else if(e.kind==='logo'||e.kind==='signature'){if(e.kind==='logo'&&organizationLogo){const image=document.createElement('img');image.src=organizationLogo;image.alt='Organization logo';div.append(image)}else div.textContent=e.kind==='logo'?'Institution Logo':'Authorized signature'}
  else if(e.kind==='photo'){div.textContent='STUDENT PHOTO (uploaded during issuance)'}
  else{div.textContent=resolved(e.text)}
  div.addEventListener('pointerdown',ev=>{if(ev.button!==0)return;ev.stopPropagation();selected=i;drag={id:ev.pointerId,x:ev.clientX,y:ev.clientY,ox:e.x,oy:e.y};div.setPointerCapture(ev.pointerId);properties();canvas.querySelectorAll('.canvas-element').forEach(el=>el.classList.toggle('active',+el.dataset.index===i))});
  div.addEventListener('pointermove',ev=>{if(!drag||drag.id!==ev.pointerId||selected!==i)return;const r=canvas.getBoundingClientRect();e.x=clamp(drag.ox+(ev.clientX-drag.x)/r.width*100,0,100-e.w);e.y=clamp(drag.oy+(ev.clientY-drag.y)/r.height*100,0,100-e.h);div.style.left=e.x.toFixed(1)+'%';div.style.top=e.y.toFixed(1)+'%'});
  div.addEventListener('pointerup',()=>{drag=null;properties()});div.addEventListener('pointercancel',()=>drag=null);
  canvas.append(div);
 });
}
function control(label,value,callback,type='text',options=null){const wrap=document.createElement('label');wrap.textContent=label;let input;
 if(options){input=document.createElement('select');for(const [value,label] of options){const option=document.createElement('option');option.value=value;option.textContent=label;input.append(option)}}
 else{input=document.createElement('input');input.type=type;if(type==='number')input.step='0.5'}input.value=value;
 input.addEventListener('input',()=>{callback(input.value);paint()});wrap.append(input);return wrap}
function properties(){props.replaceChildren();if(selected===null||!config.elements[selected]){props.textContent='Click any element in the canvas to edit its position, size, font, color or layer.';return}const e=config.elements[selected];
 const heading=document.createElement('h4');heading.textContent=e.kind.toUpperCase()+' · ELEMENT '+(selected+1);props.append(heading);
 if(e.kind==='text')props.append(control('Text or dynamic placeholder',e.text,v=>e.text=v));
 const grid=document.createElement('div');grid.className='property-grid';
 for(const [key,name,max] of [['x','Left (%)',99],['y','Top (%)',99],['w','Width (%)',100],['h','Height (%)',85],['size','Font size (px)',90],['rotate','Rotation (°)',180]]){
  grid.append(control(name,e[key]??(key==='h'?12:0),v=>{if(key==='rotate')e[key]=clamp(v,-180,180);else e[key]=clamp(v,key==='w'?2:0,max)},'number'))}
 props.append(grid);
 const stylegrid=document.createElement('div');stylegrid.className='property-grid';
 stylegrid.append(control('Color',e.color||config.primary,v=>e.color=v,'color'));
 stylegrid.append(control('Opacity (0.1–1)',e.opacity??1,v=>e.opacity=clamp(v,.1,1),'number'));
 stylegrid.append(control('Alignment',e.align||'center',v=>e.align=v,'text',[['left','Left'],['center','Center'],['right','Right']]));
 stylegrid.append(control('Weight',e.weight||'normal',v=>e.weight=v,'text',[['normal','Normal'],['bold','Bold']]));
 stylegrid.append(control('Font',e.font||'sans',v=>e.font=v,'text',[['sans','Modern'],['serif','Classic serif'],['mono','Monospace'],['arabic','Pashto/Dari']]));props.append(stylegrid);
 const visible=document.createElement('label');const chk=document.createElement('input');chk.type='checkbox';chk.checked=e.visible!==false;chk.addEventListener('change',()=>{e.visible=chk.checked;paint()});visible.append(chk,document.createTextNode(' Visible'));props.append(visible);
 const actions=document.createElement('div');actions.className='designer-feature-grid';
 const button=(label,fn,cls='btn btn-sm btn-outline')=>{const b=document.createElement('button');b.type='button';b.className=cls;b.textContent=label;b.addEventListener('click',fn);actions.append(b)};
 button('Duplicate',()=>{remember();const clone=JSON.parse(JSON.stringify(e));clone.x=clamp(clone.x+3,0,90);clone.y=clamp(clone.y+3,0,90);config.elements.push(clone);selected=config.elements.length-1;paint();properties()});
 button('Bring forward',()=>{if(selected>=config.elements.length-1)return;remember();[config.elements[selected],config.elements[selected+1]]=[config.elements[selected+1],config.elements[selected]];selected++;paint();properties()});
 button('Send backward',()=>{if(selected<1)return;remember();[config.elements[selected],config.elements[selected-1]]=[config.elements[selected-1],config.elements[selected]];selected--;paint();properties()});
 button('Delete element',()=>{if(config.elements.length<=1)return alert('Keep at least one design element');remember();config.elements.splice(selected,1);selected=null;paint();properties()},'btn btn-sm btn-danger');props.append(actions);
}
function addButton(id,cb){const target=ctl(id);if(target)target.addEventListener('click',cb)}
addButton('add-text',()=>add('text','Your text',30,48,40,12,22));
addButton('add-field',()=>{const keys=['recipient','org','certificate_title','certifies','award','program','date','serial','valid_until','signer','category'];const choice=prompt('Select dynamic field:\n'+keys.join(', '),'recipient');if(!choice)return;if(!keys.includes(choice.trim()))return alert('Use one of the listed field names');add('text','{{'+choice.trim()+'}}',27,48,46,12,25)});
addButton('add-variable',()=>{const key=prompt('Create variable code (lowercase letters, digits, underscore). Example: student_id','student_id');if(!key)return;const normalized=key.trim().toLowerCase();if(!/^[a-z][a-z0-9_]{0,31}$/.test(normalized))return alert('Invalid code. Use student_id format');if(config.variables.some(v=>v.key===normalized))return alert('Already exists; use the variable list');const label=prompt('Label shown on the issue form','Student ID')||normalized;remember();config.variables.push({key:normalized,label:label.slice(0,70),required:false});add('text','{{field:'+normalized+'}}',25,58,50,10,20);variables()});
addButton('add-photo',()=>add('photo','',75,25,16,26,12));
addButton('add-logo',()=>add('logo','',8,8,14,16,12));
addButton('add-signature',()=>add('signature','',70,77,18,10,17));
addButton('add-qr',()=>add('qr','',81,73,14,20,16));
addButton('add-mask',()=>{remember();config.elements.unshift(elem('mask','',24,42,52,13,13));selected=0;paint();properties()});
addButton('add-line',()=>add('line','',22,78,56,2,2));
addButton('undo-design',()=>{if(!undo.length)return;config=JSON.parse(undo.pop());selected=null;paint();properties();variables()});
function variables(){const list=ctl('variable-list');if(!list)return;list.replaceChildren();
 for(const [i,v] of config.variables.entries()){const row=document.createElement('div');row.className='variable-row';const label=document.createElement('span');label.textContent=v.label+' · {{field:'+v.key+'}}';row.append(label);
 const required=document.createElement('label');const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.checked=!!v.required;checkbox.addEventListener('change',()=>{v.required=checkbox.checked});required.append(checkbox,document.createTextNode(' Required'));row.append(required);
 const del=document.createElement('button');del.type='button';del.className='btn btn-sm btn-outline';del.textContent='Remove';del.addEventListener('click',()=>{remember();config.variables.splice(i,1);config.elements=config.elements.filter(e=>e.text!=='{{field:'+v.key+'}}');selected=null;paint();properties();variables()});row.append(del);list.append(row)}
 if(!config.variables.length)list.textContent='No extra variables yet. Use “+ Custom variable” to add Student ID, Grade, Faculty, etc.'}
for(const [id,key,conv] of [['paper','paper',v=>v],['primary','primary',v=>v],['accent','accent',v=>v],['orientation','orientation',v=>v],['frame','frame',Number],['pattern','pattern',Number],['background-fit','background_fit',v=>v]]){
 const el=ctl(id);if(el)el.addEventListener('input',()=>{config[key]=conv(el.value);paint()})}
const reset=ctl('reset-artwork');if(reset)reset.addEventListener('click',()=>{if(!confirm('Reset to the original uploaded art and QR only? Your template edits will be replaced.'))return;const form=document.createElement('form');form.method='post';form.action=reset.dataset.endpoint;const token=document.createElement('input');token.type='hidden';token.name='csrf';token.value=reset.dataset.csrf;form.append(token);document.body.append(form);form.requestSubmit()});
if(bgInput)bgInput.addEventListener('change',()=>{const file=bgInput.files[0];if(!file)return;if(imageUrl.startsWith('blob:'))URL.revokeObjectURL(imageUrl);if(file.type.startsWith('image/')){imageUrl=URL.createObjectURL(file)}else{imageUrl='';const m=document.createElement('p');m.className='hint';m.textContent='PDF backgrounds are rendered after saving. Save and reopen for a precise preview.';canvas.parentNode.append(m)}config.artwork_mode=true;paint()});
const form=ctl('design-form');form.addEventListener('submit',()=>{ctl('design-json').value=JSON.stringify(config)});
if(window.ResizeObserver)new ResizeObserver(()=>paint()).observe(canvas.parentElement);
paint();properties();variables();
})();
