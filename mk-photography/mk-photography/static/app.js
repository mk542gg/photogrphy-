document.addEventListener('click',e=>{
  const img=e.target.closest('.grid img, .zoom');
  if(img){const lb=document.getElementById('lb');lb.querySelector('img').src=img.dataset.full||img.src;lb.classList.add('open');}
  if(e.target.closest('#lb')) e.target.closest('#lb').classList.remove('open');
  const fav=e.target.closest('.fav');
  if(fav){fetch('/client/favorite/'+fav.dataset.id,{method:'POST'}).then(r=>r.json()).then(d=>{
    fav.classList.toggle('on',!!d.favorite);fav.textContent=d.favorite?'♥':'♡';
    const c=document.getElementById('favcount');if(c)c.textContent=document.querySelectorAll('.fav.on').length;});}
});
document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('lb')?.classList.remove('open')});
