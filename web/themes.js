/* Temavelger: bygger menyen «Tema» i hamburgermenyen (mobil) og som knapp i toppen (PC).
   Legg til nye temaer i T og i themes.css (regler under html[data-style="id"]). */
(function(){
  var T=[['standard','Standard'],['verksted','Verksted'],['glass','Glass'],['rolig','Rolig'],['y2005','2005'],['y1999','1999']];
  var de=document.documentElement;
  function cur(){var s=de.getAttribute('data-style');return s||'standard'}
  function mark(){[].forEach.call(document.querySelectorAll('.tpick button'),function(b){b.setAttribute('aria-checked',b.dataset.s===cur())})}
  function set(id){
    if(id==='standard')de.removeAttribute('data-style');else de.setAttribute('data-style',id);
    try{localStorage.setItem('style',id)}catch(e){}
    mark()}
  function html(){return '<b id="tpl">Tema</b>'+T.map(function(t){return '<button type="button" role="menuitemradio" aria-checked="false" data-s="'+t[0]+'">'+t[1]+'</button>'}).join('')}
  var nav=document.getElementById('mainnav'),hdr=document.querySelector('header.top'),tg=document.getElementById('tgl');
  if(nav){var d=document.createElement('div');d.className='tpick';d.setAttribute('role','group');d.setAttribute('aria-labelledby','tpl');d.innerHTML=html();nav.appendChild(d)}
  var pop=document.createElement('div');pop.className='tpop';pop.hidden=true;pop.setAttribute('role','menu');pop.setAttribute('aria-label','Velg tema');
  var inner=document.createElement('div');inner.className='tpick';inner.innerHTML=html().replace('id="tpl"','');pop.appendChild(inner);document.body.appendChild(pop);
  var btn=document.createElement('button');btn.type='button';btn.className='tgl';btn.id='thb';btn.title='Velg tema';btn.setAttribute('aria-label','Velg tema');btn.setAttribute('aria-haspopup','menu');btn.setAttribute('aria-expanded','false');
  btn.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3a9 9 0 1 0 0 18c1.2 0 2-.8 2-1.8 0-.6-.3-1-.6-1.4-.3-.4-.5-.8-.5-1.3 0-1 .8-1.7 1.8-1.7H17a4 4 0 0 0 4-4c0-4.4-4-8-9-8z"/><circle cx="7.5" cy="11" r="1"/><circle cx="10.5" cy="7" r="1"/><circle cx="15" cy="7.5" r="1"/></svg>';
  if(hdr){if(tg)hdr.insertBefore(btn,tg);else hdr.appendChild(btn)}
  function close(){pop.hidden=true;btn.setAttribute('aria-expanded','false')}
  function open(){var r=btn.getBoundingClientRect();pop.hidden=false;pop.style.top=(r.bottom+8)+'px';pop.style.left=Math.max(8,Math.min(innerWidth-pop.offsetWidth-8,r.right-pop.offsetWidth))+'px';btn.setAttribute('aria-expanded','true')}
  btn.addEventListener('click',function(e){e.stopPropagation();pop.hidden?open():close()});
  document.addEventListener('click',function(e){if(!pop.hidden&&!e.target.closest('.tpop'))close()});
  document.addEventListener('keydown',function(e){if(e.key==='Escape')close()});
  addEventListener('resize',close);addEventListener('scroll',close,{passive:true});
  document.addEventListener('click',function(e){var b=e.target.closest('.tpick button');if(!b)return;set(b.dataset.s);if(e.target.closest('.tpop'))close()});
  mark();
})();
