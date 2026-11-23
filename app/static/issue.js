/* CertiGov issuance fields — definitions come from the organization's own template. */
(()=>{'use strict';const s=document.getElementById('issue-template'),area=document.getElementById('template-extra-fields'),raw=document.getElementById('template-variables');if(!s||!area||!raw)return;
let choices={};try{choices=JSON.parse(raw.textContent)}catch(e){return}
let existing={};try{existing=JSON.parse(document.getElementById('existing-issue-values')?.textContent||'{}')}catch(e){}
function redraw(){area.replaceChildren();const fields=choices[s.value]||[];if(!fields.length)return;
const h=document.createElement('h3');h.textContent='Additional certificate variables';area.append(h);
const hint=document.createElement('p');hint.className='hint';hint.textContent='These fields replace matching {{field:key}} placeholders placed in the template editor.';area.append(hint);
for(const f of fields){const label=document.createElement('label');label.textContent=f.label+(f.required?' *':'');const inp=document.createElement('input');inp.name='field__'+f.key;inp.maxLength=300;inp.required=!!f.required;inp.placeholder='Value for '+f.key;inp.value=existing['field__'+f.key]||'';label.append(inp);area.append(label)}}
s.addEventListener('change',redraw);redraw()})();
