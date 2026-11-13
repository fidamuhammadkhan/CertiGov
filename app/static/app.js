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
