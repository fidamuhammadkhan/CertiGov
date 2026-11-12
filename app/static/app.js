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
