'use strict';
document.addEventListener('click',async(e)=>{
  const copy=e.target.closest('[data-copy]');
  if(copy){
    try{await navigator.clipboard.writeText(copy.dataset.copy);const orig=copy.textContent;copy.textContent='✓ Copied';setTimeout(()=>{copy.textContent=orig},1800)}
    catch(err){window.prompt('Copy verification URL:',copy.dataset.copy)}
  }
  const confirmButton=e.target.closest('[data-confirm]');
  if(confirmButton&&!window.confirm(confirmButton.dataset.confirm))e.preventDefault();
});


/* CertiGov theme v4: visible on public pages and every authenticated dashboard. */
(()=>{
 'use strict';
 const root=document.body;
 const selector=document.getElementById('ui-theme');
 const toggle=document.getElementById('theme-mode-toggle');
 if(!root||!selector||!toggle)return;
 const themes=['ocean','midnight','emerald','rose','violet','sand','sunset','forest','slate','azure','copper','graphite'];
 const get=(key)=>{try{return window.localStorage.getItem(key)}catch(_){return null}};
 const set=(key,value)=>{try{window.localStorage.setItem(key,value)}catch(_){}};
 const modeKey='certigov_ui_mode_v4',themeKey='certigov_ui_theme_v4';
 const storedTheme=get(themeKey),storedMode=get(modeKey);
 const defaultTheme=root.dataset.defaultTheme||'ocean', defaultMode=root.dataset.defaultMode||'light';
 let theme=themes.includes(storedTheme)?storedTheme:defaultTheme;
 let mode=['light','dark'].includes(storedMode)?storedMode:defaultMode;
 const labels={en:['Light mode','Dark mode'],ps:['روښانه بڼه','تیاره بڼه'],fa:['حالت روشن','حالت تاریک']};
 function apply(){
   root.dataset.theme=themes.includes(theme)?theme:'ocean';
   root.dataset.mode=mode==='dark'?'dark':'light';
   selector.value=root.dataset.theme;
   toggle.setAttribute('aria-pressed',String(mode==='dark'));
   toggle.firstChild.textContent=mode==='dark'?'☀ ':'☾ ';
   const localized=labels[root.dataset.lang]||labels.en;
   const name=mode==='dark'?localized[0]:localized[1];
   toggle.querySelector('span').textContent=name;
   toggle.setAttribute('aria-label',name);toggle.title=name;
   const meta=document.querySelector('meta[name="theme-color"]');
   if(meta)meta.setAttribute('content',mode==='dark'?'#0b1420':'#f7f9fc');
 }
 selector.addEventListener('change',()=>{theme=selector.value;set(themeKey,theme);apply()});
 toggle.addEventListener('click',()=>{mode=mode==='dark'?'light':'dark';set(modeKey,mode);apply()});
 apply();
})();

/* v5: renew a session-bound CSRF token just before a real form submission.
   The server still validates every POST; this avoids stale-form failures in tabs
   left open through login or navigation and preserves clicked approve/reject values. */
(()=>{'use strict';
 document.addEventListener('submit',async(event)=>{
   const form=event.target;
   if(!(form instanceof HTMLFormElement)||form.method.toLowerCase()!=='post'||form.dataset.csrfRenewed==='yes'){
     if(form?.dataset?.csrfRenewed==='yes')delete form.dataset.csrfRenewed;
     return;
   }
   const csrf=form.querySelector('input[name="csrf"]');if(!csrf)return;
   event.preventDefault();const submitter=event.submitter||null;
   try{
     const resp=await fetch('/api/session/csrf',{credentials:'same-origin',cache:'no-store',headers:{'Accept':'application/json'}});
     if(!resp.ok)throw new Error('Cannot update form session');
     const obj=await resp.json();if(!obj.csrf)throw new Error('Missing form token');
     csrf.value=obj.csrf;form.dataset.csrfRenewed='yes';form.requestSubmit(submitter||undefined);
   }catch(error){alert('Your form session could not be renewed. Reload the page and try again.');}
 },true);
})();
