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
function toggleMenu(){
  var nl=document.getElementById('navLinks');
  if(nl)nl.classList.toggle('open');
}
document.querySelectorAll('.nav-link').forEach(function(l){
  l.addEventListener('click',function(){var nl=document.getElementById('navLinks');if(nl)nl.classList.remove('open');});
});
function scrollRev(dir){var t=document.getElementById('reviewTrack');if(t)t.scrollBy({left:dir*360,behavior:'smooth'});}
