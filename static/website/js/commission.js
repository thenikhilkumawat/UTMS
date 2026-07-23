'use strict';
var PRICES={shirt:450,pant:550,suit:2900,suit3pc:3600,blazer:2400,kurta:500,kurtaset:900,pathani:550,safari:1200,jeans:650,pajama:450};
var TURNAROUND={shirt:7,pant:7,suit:14,suit3pc:14,blazer:10,kurta:7,kurtaset:7,pathani:7,safari:10,jeans:7,pajama:5};
var URGENT_BLOCKED={suit:1,suit3pc:1,blazer:1,safari:1};
var GARMENT_NAMES={shirt:'Formal Shirt',pant:'Pant',suit:'Suit 2-Piece',suit3pc:'Suit 3-Piece',blazer:'Blazer',kurta:'Kurta only',kurtaset:'Kurta + Pajama',pathani:'Pathani Suit',safari:'Safari Suit',jeans:'Jeans',pajama:'Pajama'};
var DETAILS={
  shirt:[{k:'collar',l:'Collar',o:['Regular','Button-down','Mandarin','Cut-away']},{k:'pocket',l:'Pocket',o:['One pocket','No pocket']},{k:'sleeve',l:'Sleeve',o:['Full sleeve','Half sleeve']},{k:'cuff',l:'Cuff',o:['Single button','Double button']},{k:'bottom',l:'Bottom hem',o:['Rounded','Straight']}],
  pant:[{k:'pleat',l:'Pleat style',o:['Flat front','Single pleat','Double pleat']},{k:'fit',l:'Fit',o:['Regular','Slim','Wide leg']},{k:'hem',l:'Hem',o:['Plain','Cuffed']}],
  suit:[{k:'lapel',l:'Lapel',o:['Notch lapel','Peak lapel','Shawl lapel']},{k:'buttons',l:'Buttons',o:['2 buttons','3 buttons','Double-breasted']},{k:'vent',l:'Back vent',o:['Single vent','Double vent','No vent']},{k:'lining',l:'Lining',o:['Full lining','Half lining']}],
  suit3pc:[{k:'lapel',l:'Lapel',o:['Notch lapel','Peak lapel']},{k:'buttons',l:'Buttons',o:['2 buttons','3 buttons']},{k:'lining',l:'Lining',o:['Full lining','Half lining']}],
  blazer:[{k:'lapel',l:'Lapel',o:['Notch lapel','Peak lapel']},{k:'buttons',l:'Buttons',o:['1 button','2 buttons']},{k:'lining',l:'Lining',o:['Full lining','Half lining','No lining']}],
  kurta:[{k:'neck',l:'Neck style',o:['Mandarin','V-neck','Round neck','Nehru']},{k:'sleeve',l:'Sleeve',o:['Full sleeve','Half sleeve','3/4 sleeve']},{k:'pocket',l:'Pocket',o:['Chest pocket','No pocket']},{k:'bottom',l:'Bottom',o:['Straight','Side slits']}],
  kurtaset:[{k:'neck',l:'Neck style',o:['Mandarin','V-neck','Round neck']},{k:'sleeve',l:'Sleeve',o:['Full sleeve','Half sleeve']},{k:'pajama_fit',l:'Pajama style',o:['Regular','Churidar','Straight']}],
  pathani:[{k:'collar',l:'Collar',o:['Round neck','Mandarin','V-neck']},{k:'sleeve',l:'Sleeve',o:['Full sleeve','Half sleeve']}],
  safari:[{k:'pocket',l:'Pockets',o:['4 pockets','2 pockets']},{k:'sleeve',l:'Sleeve',o:['Half sleeve','Full sleeve']}],
  jeans:[{k:'fit',l:'Fit',o:['Regular','Slim','Straight','Bootcut']},{k:'waist',l:'Waist',o:['Mid rise','High rise']}],
  pajama:[{k:'waist',l:'Waist',o:['Elastic waist','Drawstring','Both']},{k:'fit',l:'Fit',o:['Regular','Wide','Slim']}]
};
var MANUAL={
  shirt:[['chest','Chest'],['waist','Waist'],['shoulder','Shoulder'],['shirt_length','Shirt length'],['sleeve','Sleeve'],['collar','Collar size']],
  pant:[['waist','Waist'],['hip','Hip'],['thigh','Thigh'],['pant_length','Pant length'],['inseam','Inseam'],['bottom','Bottom width']],
  suit:[['chest','Chest'],['waist','Waist'],['shoulder','Shoulder'],['jacket_length','Jacket length'],['sleeve','Sleeve'],['pant_length','Pant length']],
  suit3pc:[['chest','Chest'],['waist','Waist'],['shoulder','Shoulder'],['jacket_length','Jacket length'],['sleeve','Sleeve'],['pant_length','Pant length']],
  blazer:[['chest','Chest'],['shoulder','Shoulder'],['blazer_length','Blazer length'],['sleeve','Sleeve']],
  kurta:[['chest','Chest'],['waist','Waist'],['shoulder','Shoulder'],['kurta_length','Kurta length'],['sleeve','Sleeve']],
  kurtaset:[['chest','Chest'],['waist','Waist'],['shoulder','Shoulder'],['kurta_length','Kurta length'],['sleeve','Sleeve'],['pajama_waist','Pajama waist']],
  pathani:[['chest','Chest'],['waist','Waist'],['shoulder','Shoulder'],['length','Length'],['sleeve','Sleeve']],
  safari:[['chest','Chest'],['waist','Waist'],['shoulder','Shoulder'],['length','Length'],['sleeve','Sleeve']],
  jeans:[['waist','Waist'],['hip','Hip'],['thigh','Thigh'],['length','Length'],['inseam','Inseam']],
  pajama:[['waist','Waist'],['hip','Hip'],['length','Length']]
};
var SIZES={S:{chest:'35-36"',waist:'29-30"',shoulder:'15.5"',shirt:'27"',pant:'38"',hip:'35-36"'},M:{chest:'37-38"',waist:'31-32"',shoulder:'16.5"',shirt:'28"',pant:'39"',hip:'37-38"'},L:{chest:'39-40"',waist:'33-34"',shoulder:'17.5"',shirt:'29"',pant:'40"',hip:'39-40"'},XL:{chest:'41-42"',waist:'35-36"',shoulder:'18.5"',shirt:'30"',pant:'41"',hip:'41-42"'},XXL:{chest:'43-44"',waist:'37-38"',shoulder:'19.5"',shirt:'31"',pant:'42"',hip:'43-44"'}};

var selGarment=null,selDelivery='pickup',selQty=1,isUrgent=false;

document.querySelectorAll('input[name="garment_type"]').forEach(function(r){
  r.addEventListener('change',function(){selGarment=r.value;buildDetails(r.value);buildManual(r.value);updateSummary();updatePrice();updateBtn();});
});
var p=document.querySelector('input[name="garment_type"]:checked');
if(p){selGarment=p.value;buildDetails(p.value);buildManual(p.value);updatePrice();}

function changeQty(d){selQty=Math.max(1,Math.min(20,selQty+d));document.getElementById('qty-display').textContent=selQty;document.getElementById('qty_val').value=selQty;updatePrice();updateSummary();}

function toggleUrgent(cb){
  isUrgent=cb.checked;
  var note=document.getElementById('urgentNote');
  if(isUrgent&&selGarment&&URGENT_BLOCKED[selGarment]){note.textContent='Urgent delivery is not possible for this garment. It requires more time.';note.style.display='block';cb.checked=false;isUrgent=false;return;}
  note.textContent=isUrgent?'Your order will be prioritised. Ready in 1-3 days for simple garments.':'';
  note.style.display=isUrgent?'block':'none';
  var ur=document.getElementById('sp-urg-row');if(ur)ur.style.display=isUrgent?'flex':'none';
  updatePrice();updateSummary();
}

function pickSz(sz,btn){
  document.querySelectorAll('.sz-btn').forEach(function(b){b.classList.remove('active');});btn.classList.add('active');document.getElementById('sz_val').value=sz;
  var d=SIZES[sz];if(d){document.getElementById('sizeDetail').innerHTML='<div class="sdg"><div class="sdg-item">Chest <span>'+d.chest+'</span></div><div class="sdg-item">Waist <span>'+d.waist+'</span></div><div class="sdg-item">Shoulder <span>'+d.shoulder+'</span></div><div class="sdg-item">Shirt <span>'+d.shirt+'</span></div><div class="sdg-item">Pant <span>'+d.pant+'</span></div><div class="sdg-item">Hip <span>'+d.hip+'</span></div></div>';}
  updateSummary();updatePrice();updateBtn();
}
function pickFit(fit,btn){document.querySelectorAll('.fit-btn').forEach(function(b){b.classList.remove('active');});btn.classList.add('active');document.getElementById('fit_val').value=fit;updateSummary();}

function setMeth(m,btn){
  document.querySelectorAll('.meth-tab').forEach(function(t){t.classList.remove('active');});
  document.querySelectorAll('.meth-panel').forEach(function(p){p.classList.remove('active');});
  btn.classList.add('active');var panel=document.getElementById('mp-'+m);if(panel)panel.classList.add('active');
  document.getElementById('meth_val').value=m;updateSummary();updateBtn();
}

function buildManual(g){
  var fields=MANUAL[g]||MANUAL.shirt;var grid=document.getElementById('manualGrid');if(!grid)return;
  grid.innerHTML=fields.map(function(f){return '<div class="field-group"><label class="field-label">'+f[1]+' (inches)</label><input type="number" name="manual_'+f[0]+'" class="field-input" step="0.5" min="10" max="80" placeholder="e.g. 38"></div>';}).join('');
}
buildManual('shirt');

function buildDetails(g){
  var groups=DETAILS[g]||DETAILS.shirt;var grid=document.getElementById('detailsGrid');if(!grid)return;
  grid.innerHTML=groups.map(function(gr){
    var opts=gr.o.map(function(opt,i){return '<button type="button" class="det-opt'+(i===0?' active':'')+'" data-k="'+gr.k+'" onclick="pickDet(\''+gr.k+'\',\''+opt+'\',this)">'+opt+'</button>'+(i===0?'<input type="hidden" name="detail_'+gr.k+'" id="dv_'+gr.k+'" value="'+opt+'">':'');}).join('');
    return '<div class="det-group"><span class="det-label">'+gr.l+'</span><div class="det-opts">'+opts+'</div></div>';
  }).join('');
}
function pickDet(k,v,btn){btn.closest('.det-opts').querySelectorAll('[data-k="'+k+'"]').forEach(function(b){b.classList.remove('active');});btn.classList.add('active');var hid=document.getElementById('dv_'+k);if(hid)hid.value=v;}

function setFab(choice,btn){document.querySelectorAll('.fab-tab').forEach(function(t){t.classList.remove('active');});btn.classList.add('active');document.getElementById('fab_choice').value=choice;document.getElementById('fab-own').style.display=choice==='own'?'block':'none';document.getElementById('fab-catalog').style.display=choice==='catalog'?'block':'none';updateSummary();}
function selFab(id,name,card){document.querySelectorAll('.fab-card').forEach(function(c){c.classList.remove('sel');});card.classList.add('sel');document.getElementById('fab_selected').value=id;updateSummary();}
var fabEl=document.getElementById('fabSearch');if(fabEl){fabEl.addEventListener('input',function(){var q=this.value.toLowerCase();document.querySelectorAll('.fab-card').forEach(function(c){c.style.display=(!q||(c.dataset.name||'').includes(q))?'':'none';});});}

document.querySelectorAll('input[name="ref_dropoff"]').forEach(function(r){r.addEventListener('change',function(){var el=document.getElementById('ref-pickup-addr');if(el)el.style.display=r.value==='pickup'?'block':'none';});});

function delChange(v){selDelivery=v;var el=document.getElementById('del-addr');if(el)el.style.display=v==='home'?'block':'none';updatePrice();updateSummary();}

// ── Measurement Locker ───────────────────────────────────────────────────────
function _lockerMode(){
  var codeRow=document.getElementById('locker-code-row');
  return (codeRow && codeRow.style.display!=='none') ? 'code' : 'phone';
}
function setLockerMode(mode,btn){
  document.querySelectorAll('.locker-mode-btn').forEach(function(b){b.classList.remove('active');});
  if(btn) btn.classList.add('active');
  var pr=document.getElementById('locker-phone-row'),cr=document.getElementById('locker-code-row');
  if(pr) pr.style.display = mode==='phone'?'flex':'none';
  if(cr) cr.style.display = mode==='code' ?'flex':'none';
  _lockerClearMsg();
}
function _lockerMsg(msg,type){
  var el=document.getElementById('locker-msg');if(!el)return;
  el.style.display='block';
  el.style.cssText='margin-top:8px;font-size:12.5px;padding:7px 10px;border-radius:7px;display:block;'+(type==='error'?'color:#8b2222;background:#fff0f0;':'color:#5a3e1b;background:#fff8ee;');
  el.textContent=msg;
}
function _lockerClearMsg(){var el=document.getElementById('locker-msg');if(el)el.style.display='none';}

async function fetchLocker(){
  _lockerClearMsg();
  if(_lockerMode()==='code'){
    // Order-code path — no OTP needed
    var code=(document.getElementById('locker_code')||{}).value;
    code=(code||'').trim().toUpperCase();
    if(!code){_lockerMsg('Enter your order code.','error');return;}
    var btn=document.querySelector('#locker-code-row .fetch-btn');
    btn.textContent='Searching…';btn.disabled=true;
    try{
      var r=await fetch('/api/locker/verify-otp',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf()},body:JSON.stringify({order_code:code,otp:'skip'})});
      var d=await r.json();
      if(d.success){_applyLockerResult(d.customer);}
      else{_lockerMsg(d.message||'Order not found.','error');}
    }catch(e){_lockerMsg('Connection error. Try again.','error');}
    btn.textContent='Search';btn.disabled=false;
    return;
  }
  // Phone path
  var phone=(document.getElementById('locker_phone')||{value:''}).value.trim().replace(/\D/g,'').replace(/^91/,'');
  if(phone.length!==10){_lockerMsg('Enter a valid 10-digit mobile number.','error');return;}
  var btn=document.querySelector('#locker-phone-row .fetch-btn');
  btn.textContent='Sending…';btn.disabled=true;
  try{
    var r=await fetch('/api/locker/send-otp',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf()},body:JSON.stringify({phone:phone})});
    var d=await r.json();
    if(d.success){
      document.getElementById('locker-otp').style.display='block';
      if(d.hint)_lockerMsg(d.hint,'info');
      btn.textContent='Resend OTP';btn.disabled=false;
    }else{
      _lockerMsg(d.message||'Number not found.','error');
      btn.textContent='Search';btn.disabled=false;
    }
  }catch(e){_lockerMsg('Connection error. Try again.','error');btn.textContent='Search';btn.disabled=false;}
}
async function verifyLocker(){
  var phone=(document.getElementById('locker_phone')||{value:''}).value.trim().replace(/\D/g,'').replace(/^91/,'');
  var otp=(document.getElementById('locker_otp')||{value:''}).value.trim();
  var btn=document.querySelector('#locker-otp .fetch-btn');btn.textContent='Verifying…';btn.disabled=true;
  try{
    var r=await fetch('/api/locker/verify-otp',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf()},body:JSON.stringify({phone:phone,otp:otp})});
    var d=await r.json();
    if(d.success){_applyLockerResult(d.customer);}
    else{_lockerMsg(d.message||'Wrong OTP.','error');btn.textContent='Verify';btn.disabled=false;}
  }catch(e){_lockerMsg('Connection error.','error');btn.textContent='Verify';btn.disabled=false;}
}
function _applyLockerResult(cust){
  // Store customer id + fill name/phone
  var cidEl=document.getElementById('locker_cid');if(cidEl)cidEl.value=cust.id||'';
  if(cust.name){var n=document.getElementById('cust_name');if(n&&!n.value)n.value=cust.name;}
  if(cust.phone){var p=document.getElementById('cust_phone');if(p&&!p.value)p.value=cust.phone;}
  // Fill fine-tune measurement fields
  var m=cust.measurements||{};
  var fieldMap={adj_chest:m.chest,adj_waist:m.waist,adj_shoulder:m.shoulder,adj_length:m.length||m.shirt_length,adj_trouser:m.trouser||m.pant_length||m.inseam};
  Object.keys(fieldMap).forEach(function(fname){
    var val=fieldMap[fname];if(val==null||val==='')return;
    var inp=document.querySelector('input[name="'+fname+'"]');
    if(inp&&!inp.dataset.userEdited){inp.value=val;inp.dataset.fromLocker='1';}
  });
  // Show summary in locker-found panel
  var fd=document.getElementById('locker-found');if(!fd)return;
  var labels={chest:'Chest',waist:'Waist',shoulder:'Shoulder',sleeve:'Sleeve',neck:'Neck',hip:'Hip',inseam:'Inseam',thigh:'Thigh',height:'Height″',weight:'Weight(kg)'};
  var chips=Object.keys(m).filter(function(k){return m[k]!=null&&labels[k];}).map(function(k){return '<span class="lkr-chip"><b>'+labels[k]+'</b> '+m[k]+'"</span>';}).join('');
  var note=chips?'<div class="lkr-chips">'+chips+'</div><p class="lkr-hint">Fine-tune section above has been pre-filled — adjust if needed.</p>':'<p class="lkr-hint">No body measurements on file. Please enter manually.</p>';
  fd.innerHTML='<div class="lkr-ok">✅ '+cust.name+' — measurements loaded</div>'+note;
  fd.style.display='block';
  document.getElementById('locker-otp').style.display='none';
  _lockerClearMsg();updateSummary();updateBtn();
}

function updateSummary(){
  var rows=document.getElementById('summaryRows');if(!rows)return;
  var items=[];
  if(selGarment)items.push({l:'Garment',v:GARMENT_NAMES[selGarment]||selGarment});
  items.push({l:'Quantity',v:selQty+'x'});
  var m=document.getElementById('meth_val').value;var mmap={size:'Standard size',manual:'Manual measurements',reference:'Reference garment',locker:'Saved measurements',homevisit:'Home visit'};
  items.push({l:'Measurement',v:mmap[m]||m});
  var sz=document.getElementById('sz_val').value;if(sz&&m==='size')items.push({l:'Size',v:sz+' ('+document.getElementById('fit_val').value+')'});
  if(isUrgent)items.push({l:'Priority',v:'Urgent delivery'});
  var fc=document.getElementById('fab_choice').value;if(fc==='own')items.push({l:'Fabric',v:'Bringing own'});else{var sel=document.querySelector('.fab-card.sel');if(sel)items.push({l:'Fabric',v:sel.querySelector('.fab-name').textContent});}
  rows.innerHTML=items.length?items.map(function(i){return '<div class="summary-row"><span>'+i.l+'</span><span>'+i.v+'</span></div>';}).join(''):'<p class="summary-empty">Select a garment to begin.</p>';
}

function updatePrice(){
  var pe=document.getElementById('summary-price');var de=document.getElementById('summary-date');
  if(!pe||!de||!selGarment){if(pe)pe.style.display='none';if(de)de.style.display='none';return;}
  pe.style.display='block';de.style.display='block';
  var unit=PRICES[selGarment]||450;var stitch=unit*selQty;var urgent=isUrgent?99:0;var freeDelivery=stitch>=1499;var delivery=selDelivery==='home'?(freeDelivery?0:49):0;
  var total=stitch+urgent+delivery;var advance=Math.round(total*0.3);
  document.getElementById('sp-unit').textContent='Rs. '+unit;
  var qr=document.getElementById('sp-qty-row');if(qr)qr.style.display=selQty>1?'flex':'none';
  var qv=document.getElementById('sp-qty-val');if(qv)qv.textContent=selQty+'x = Rs. '+stitch;
  var ur=document.getElementById('sp-urg-row');if(ur)ur.style.display=isUrgent?'flex':'none';
  var dr=document.getElementById('sp-del-row');if(dr)dr.style.display=selDelivery==='home'?'flex':'none';
  var da=document.getElementById('sp-del-amt');if(da)da.textContent=freeDelivery?'Free':'Rs. 49';
  document.getElementById('sp-adv').textContent='Rs. '+advance;
  var days=isUrgent?2:(TURNAROUND[selGarment]||7);var dt=new Date();dt.setDate(dt.getDate()+days);
  document.getElementById('sd-val').textContent=dt.toLocaleDateString('en-IN',{day:'numeric',month:'long',year:'numeric'});
}

function updateBtn(){
  var hasG=!!document.querySelector('input[name="garment_type"]:checked');
  var name=(document.getElementById('cust_name')||{}).value||'';
  var phone=(document.getElementById('cust_phone')||{}).value||'';
  var btn=document.getElementById('reserveBtn');if(btn)btn.disabled=!(hasG&&name.trim().length>1&&phone.trim().length===10);
}

var form=document.getElementById('commissionForm');
if(form){form.addEventListener('submit',function(e){
  e.preventDefault();
  var btn=document.getElementById('reserveBtn');
  btn.disabled=true;btn.querySelector('span').textContent='Processing...';
  this.submit();
});}

function openSizeGuide(e){e.preventDefault();var m=document.getElementById('sizeGuideModal');if(m)m.style.display='flex';}
function csrf(){var el=document.querySelector('input[name="csrf_token"]');return el?el.value:'';}
