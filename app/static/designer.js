'use strict';
(()=>{
 const source=document.getElementById('design-data');
 if(!source)return;
 const config=JSON.parse(source.textContent);
 const canvas=document.getElementById('certificate-canvas');
 const paper=document.getElementById('paper'),primary=document.getElementById('primary'),accent=document.getElementById('accent');
 const orientation=document.getElementById('orientation'),frame=document.getElementById('frame'),pattern=document.getElementById('pattern');
 const backgroundFit=document.getElementById('background-fit');
 const props=document.getElementById('element-properties');
 let selected=null;let drag=null;
 const labels={en:{certificate_title:'Certificate of Achievement',certifies:'This certifies that',org:'Your Organization',recipient:'Student Name',award:'Successfully completed the program',program:'Program Title',date:'12 November 2026'},ps:{certificate_title:'د لاسته راوړنې سند',certifies:'دا تصدیق کوي چې',org:'ستاسو اداره',recipient:'د زده کوونکي نوم',award:'پروګرام یې بشپړ کړی دی',program:'د پروګرام نوم',date:'۱۲ نومبر ۲۰۲۶'},fa:{certificate_title:'تصدیق‌نامه دستاورد',certifies:'بدینوسیله تصدیق می‌شود که',org:'نهاد شما',recipient:'نام دانشجو',award:'برنامه را موفقانه تکمیل کرده است',program:'نام برنامه',date:'۱۲ نوامبر ۲۰۲۶'}};
 const l=labels[config.language]||labels.en;
 const bg=canvas.dataset.background;
 if(bg)canvas.style.backgroundImage=`url("${bg}")`;
 canvas.style.backgroundSize=({contain:'contain',cover:'cover',stretch:'100% 100%'})[config.background_fit||'contain'];
 canvas.style.backgroundPosition='center';canvas.style.backgroundRepeat='no-repeat';
 function resolve(text){return String(text||'').replace(/\{\{(.*?)\}\}/g,(m,key)=>{
   return ({org:l.org,recipient:l.recipient,certificate_title:l.certificate_title,certifies:l.certifies,
      award:l.award,program:l.program,date:l.date,serial:'CERT-2026-00001',valid_until:'—',signer:'Authorized signature'}[key.trim()])??m;
 });}
 function updateStyle(){
   canvas.style.backgroundColor=config.paper;
   const b=['10px double '+config.accent,'11px solid '+config.primary,'6px solid '+config.accent,
      '12px solid '+config.primary,'10px ridge '+config.accent];
   canvas.style.border=(bg||document.querySelector('input[name=background]').files.length) && config.artwork_mode ? '0' : b[config.frame]||b[0];
   canvas.style.backgroundSize=({contain:'contain',cover:'cover',stretch:'100% 100%'})[config.background_fit||'contain'];
   canvas.classList.toggle('portrait',config.orientation==='portrait');
   paper.value=config.paper;primary.value=config.primary;accent.value=config.accent;
   orientation.value=config.orientation;frame.value=String(config.frame);
   pattern.value=String(config.pattern||0);backgroundFit.value=config.background_fit||'contain';
   const accent=config.accent,paper=config.paper,primary=config.primary;
   const motifs=['none',`linear-gradient(115deg, ${paper} 75%, ${accent}22 75%)`,
      `radial-gradient(circle at 85% 10%, ${accent}28 0%, transparent 32%)`,
      `linear-gradient(90deg, ${primary} 0 4%, ${paper} 4% 100%)`,
      `linear-gradient(135deg, ${paper} 85%, ${accent}33 85%)`];
   if(!bg && !document.querySelector('input[name=background]').files.length)canvas.style.backgroundImage=motifs[config.pattern||0];
 }
 function redraw(){
   updateStyle();canvas.replaceChildren();
   const scale=canvas.clientWidth/(config.orientation==='portrait'?794:1122);
   config.elements.forEach((e,i)=>{
     if(!e.visible)return;
     const div=document.createElement('div');div.className='canvas-element '+e.kind+(selected===i?' active':'');div.dataset.index=i;
     Object.assign(div.style,{left:e.x+'%',top:e.y+'%',width:e.w+'%',fontSize:Math.max(7,e.size*scale)+'px',
       color:e.color,textAlign:e.align,fontWeight:e.weight,direction:config.language==='en'?'ltr':'rtl'});
     if(e.kind==='qr'){div.textContent='▦';div.style.minHeight='10%';div.style.backgroundColor='#ffffff';div.style.padding='3px'}
     else if(e.kind==='mask'){div.textContent='';div.style.height=(e.h||10)+'%';div.style.backgroundColor=e.color;div.title='Background cover / mask'}
     else if(e.kind==='logo'){div.textContent='✦'}
     else if(e.kind==='signature'){div.textContent='Signature';div.style.fontStyle='italic'}
     else if(e.kind==='line'){div.style.backgroundColor=config.accent;div.textContent='';div.style.minHeight='2px'}
     else div.textContent=resolve(e.text);
     div.addEventListener('pointerdown',(ev)=>{
       ev.stopPropagation();selected=i;drag={x:ev.clientX,y:ev.clientY,ox:e.x,oy:e.y,id:ev.pointerId};
       div.setPointerCapture(ev.pointerId);redrawProperties();
       canvas.querySelectorAll('.canvas-element').forEach(x=>x.classList.toggle('active',Number(x.dataset.index)===selected));
     });
     div.addEventListener('pointermove',(ev)=>{
       if(!drag||drag.id!==ev.pointerId||selected!==i)return;
       const bounds=canvas.getBoundingClientRect();
       e.x=Math.min(99,Math.max(0,Math.round((drag.ox+(ev.clientX-drag.x)/bounds.width*100)*10)/10));
       e.y=Math.min(99,Math.max(0,Math.round((drag.oy+(ev.clientY-drag.y)/bounds.height*100)*10)/10));
       div.style.left=e.x+'%';div.style.top=e.y+'%';
     });
     div.addEventListener('pointerup',()=>{drag=null;redrawProperties()});
     div.addEventListener('pointercancel',()=>{drag=null});
     canvas.appendChild(div);
   });
 }
 function control(label,value,onChange,type='text',options=null){
   const box=document.createElement('label');box.textContent=label;
   let input;if(options){input=document.createElement('select');options.forEach(opt=>{const o=document.createElement('option');o.value=opt;o.textContent=opt;input.appendChild(o)})}
   else{input=document.createElement('input');input.type=type;if(type==='number'){input.step='1';input.min='0'} }
   input.value=value;
   input.addEventListener(type==='checkbox'?'change':'input',()=>onChange(type==='checkbox'?input.checked:input.value));
   box.appendChild(input);return box;
 }
 function redrawProperties(){
   props.replaceChildren();
   if(selected===null||!config.elements[selected]){props.textContent='Select a field to change its properties.';return}
   const e=config.elements[selected];
   if(e.kind==='text')props.appendChild(control('Text / placeholder',e.text,v=>{e.text=v;redraw()}));
   const two=document.createElement('div');two.className='form-row';
   two.append(control('X %',e.x,v=>{e.x=Math.min(99,Math.max(0,Number(v)||0));redraw()}),
              control('Y %',e.y,v=>{e.y=Math.min(99,Math.max(0,Number(v)||0));redraw()}));props.appendChild(two);
   const two2=document.createElement('div');two2.className='form-row';
   two2.append(control('Width %',e.w,v=>{e.w=Math.min(100,Math.max(2,Number(v)||2));redraw()},'number'),
               control('Size',e.size,v=>{e.size=Math.min(90,Math.max(7,Number(v)||7));redraw()},'number'));props.appendChild(two2);
   const two3=document.createElement('div');two3.className='form-row';
   two3.append(control('Color',e.color,v=>{e.color=v;redraw()},'color'),
               control('Alignment',e.align,v=>{e.align=v;redraw()},'text',['left','center','right']));props.appendChild(two3);
   if(['mask','qr','logo','signature'].includes(e.kind))props.appendChild(control('Height %',e.h||10,v=>{e.h=Math.min(70,Math.max(2,Number(v)||10));redraw()},'number'));
   props.appendChild(control('Font weight',e.weight,v=>{e.weight=v;redraw()},'text',['normal','bold']));
   const visible=document.createElement('label');visible.className='property-check';
   const chk=document.createElement('input');chk.type='checkbox';chk.checked=e.visible;
   chk.addEventListener('change',()=>{e.visible=chk.checked;redraw()});visible.append(chk,document.createTextNode(' Visible'));props.appendChild(visible);
   const del=document.createElement('button');del.type='button';del.className='btn btn-danger';del.textContent='Remove element';
   del.addEventListener('click',()=>{if(config.elements.length<=1){alert('Keep at least one element.');return}config.elements.splice(selected,1);selected=null;redraw();redrawProperties()});props.appendChild(del);
 }
 const bind=(element,key,convert=v=>v)=>element.addEventListener('input',e=>{config[key]=convert(e.target.value);redraw()});
 bind(paper,'paper');bind(primary,'primary');bind(accent,'accent');
 bind(orientation,'orientation');bind(frame,'frame',v=>Number(v));bind(pattern,'pattern',v=>Number(v));bind(backgroundFit,'background_fit');
 document.getElementById('add-text').addEventListener('click',()=>{
   config.elements.push({id:'new_'+Date.now(),kind:'text',text:'Your text here',x:25,y:55,w:50,size:23,color:config.primary,weight:'normal',align:'center',visible:true});
   selected=config.elements.length-1;redraw();redrawProperties();
 });
 document.getElementById('add-mask').addEventListener('click',()=>{
   config.elements.unshift({id:'mask_'+Date.now(),kind:'mask',text:'',x:21,y:39,w:58,h:12,size:12,color:config.paper,weight:'normal',align:'center',visible:true});
   selected=0;redraw();redrawProperties();
 });
 document.getElementById('add-field').addEventListener('click',()=>{
   const choices=['recipient','org','certificate_title','certifies','award','program','date','serial','valid_until','signer'];
   const promptText=window.prompt('Field to insert: '+choices.join(', '),'recipient');
   if(!promptText)return;
   const field=promptText.trim();if(!choices.includes(field)){window.alert('Choose one of the listed placeholders.');return;}
   config.elements.push({id:'field_'+Date.now(),kind:'text',text:'{{'+field+'}}',x:25,y:52,w:50,h:10,size:24,color:config.primary,weight:'bold',align:'center',visible:true});
   selected=config.elements.length-1;redraw();redrawProperties();
 });
 const reset=document.getElementById('reset-artwork');
 if(reset)reset.addEventListener('click',()=>{
   if(!window.confirm('Remove template overlays and keep only the verification QR? The background design will be preserved.'))return;
   const f=document.createElement('form');f.method='post';f.action=reset.dataset.endpoint;
   const input=document.createElement('input');input.type='hidden';input.name='csrf';input.value=reset.dataset.csrf;f.append(input);document.body.append(f);f.submit();
 });
 document.getElementById('add-line').addEventListener('click',()=>{
   config.elements.push({id:'line_'+Date.now(),kind:'line',text:'',x:20,y:67,w:60,size:2,color:config.accent,weight:'normal',align:'center',visible:true});
   selected=config.elements.length-1;redraw();redrawProperties();
 });
 document.getElementById('design-form').addEventListener('submit',()=>{
   document.getElementById('design-json').value=JSON.stringify(config);
 });
 const bgInput=document.querySelector('input[name=background]');
 bgInput.addEventListener('change',()=>{
   const f=bgInput.files[0];if(f&&f.type.startsWith('image/')){
     canvas.style.backgroundImage=`url("${URL.createObjectURL(f)}")`;
   }else if(f){canvas.style.backgroundImage='none';}
 });
 if(window.ResizeObserver)new ResizeObserver(redraw).observe(canvas.parentElement);
 redraw();redrawProperties();
})();
