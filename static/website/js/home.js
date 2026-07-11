'use strict';
function setSlide(idx,btn){
  document.querySelectorAll('.fj-slide').forEach(function(s){s.classList.remove('active');});
  document.querySelectorAll('.fj-thumb').forEach(function(t){t.classList.remove('active');});
  var slide=document.querySelector('.fj-slide[data-slide="'+idx+'"]');
  if(slide)slide.classList.add('active');
  if(btn)btn.classList.add('active');
  initSlider(idx);
}
var activeSliders={};
function initSlider(idx){
  if(activeSliders[idx])return;
  var wrap=document.getElementById('cmp'+idx);
  var after=document.getElementById('after'+idx);
  var inner=document.getElementById('afterinner'+idx);
  var handle=document.getElementById('hdl'+idx);
  if(!wrap||!after||!handle)return;
  function setPos(clientX){
    var r=wrap.getBoundingClientRect();
    var pct=Math.max(5,Math.min(95,(clientX-r.left)/r.width*100));
    after.style.width=pct+'%';
    if(inner)inner.style.width=wrap.offsetWidth+'px';
    handle.style.left=pct+'%';
    handle.style.transform='translateX(-50%)';
  }
  if(inner)inner.style.width=wrap.offsetWidth+'px';
  var drag=false;
  handle.addEventListener('mousedown',function(e){drag=true;e.preventDefault();});
  wrap.addEventListener('click',function(e){setPos(e.clientX);});
  document.addEventListener('mousemove',function(e){if(drag)setPos(e.clientX);});
  document.addEventListener('mouseup',function(){drag=false;});
  handle.addEventListener('touchstart',function(){drag=true;},{passive:true});
  document.addEventListener('touchmove',function(e){if(drag)setPos(e.touches[0].clientX);},{passive:true});
  document.addEventListener('touchend',function(){drag=false;});
  window.addEventListener('resize',function(){if(inner)inner.style.width=wrap.offsetWidth+'px';});
  activeSliders[idx]=true;
}
document.addEventListener('DOMContentLoaded',function(){initSlider(0);});
