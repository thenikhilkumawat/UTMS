'use strict';
var lang=localStorage.getItem('ut_lang')||'en';
if(lang==='hi')applyLang('hi');
function toggleLang(){lang=lang==='en'?'hi':'en';localStorage.setItem('ut_lang',lang);applyLang(lang);}
function applyLang(l){document.documentElement.setAttribute('data-lang',l);document.querySelectorAll('[data-en]').forEach(function(el){var t=el.getAttribute('data-'+l);if(!t)return;if(t.indexOf('<br>')!==-1)el.innerHTML=t;else el.textContent=t;});}
var nav=document.getElementById('mainNav');
if(nav){
  window.addEventListener('scroll',function(){nav.classList.toggle('scrolled',window.scrollY>10);},{passive:true});
  nav.classList.toggle('scrolled',window.scrollY>10);
}
// Drawer - defined here as fallback (base.html also defines these)
if(typeof openDrawer==='undefined'){
  window.openDrawer=function(){
    var d=document.getElementById('navDrawer'),o=document.getElementById('navOverlay');
    if(d)d.classList.add('open');if(o)o.classList.add('open');
    document.body.style.overflow='hidden';
  };
  window.closeDrawer=function(){
    var d=document.getElementById('navDrawer'),o=document.getElementById('navOverlay');
    if(d)d.classList.remove('open');if(o)o.classList.remove('open');
    document.body.style.overflow='';
  };
}
// Legacy fallback
function toggleMenu(){if(typeof openDrawer!=='undefined')openDrawer();}
function scrollRev(dir){var t=document.getElementById('reviewTrack');if(t)t.scrollBy({left:dir*360,behavior:'smooth'});}
// Reviews now scroll via smooth CSS transform marquee (.reviews-track animation) — no JS scroll needed.