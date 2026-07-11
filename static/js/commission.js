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
  pajama:[{k:'waist',l:'Waist',o:['Elastic waist','Drawstring','Both']},{k:'fit',l:'Fit',o:['Regular','Wide','Slim']}],
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

// Approx. fabric metres required per garment type, by size (S/M/L/XL/XXL)
var FABRIC_METERS={
  shirt:{S:1.3,M:1.4,L:1.5,XL:1.6,XXL:1.7},
  pant:{S:1.2,M:1.3,L:1.4,XL:1.5,XXL:1.6},
  jeans:{S:1.2,M:1.3,L:1.4,XL:1.5,XXL:1.6},
  pajama:{S:1.5,M:1.6,L:1.7,XL:1.8,XXL:1.9},
  kurta:{S:2.2,M:2.4,L:2.6,XL:2.8,XXL:3.0},
  kurtaset:{S:3.7,M:4.0,L:4.3,XL:4.6,XXL:4.9},
  pathani:{S:2.5,M:2.7,L:2.9,XL:3.1,XXL:3.3},
  safari:{S:3.0,M:3.2,L:3.4,XL:3.6,XXL:3.8},
  blazer:{S:1.8,M:2.0,L:2.2,XL:2.4,XXL:2.6},
  suit:{S:3.2,M:3.5,L:3.8,XL:4.1,XXL:4.4},
  suit3pc:{S:3.8,M:4.1,L:4.4,XL:4.7,XXL:5.0},
};
// Admin-configured overrides loaded from /website/api/fabric-metres (Sizes panel in admin).
// Shape: {category: {size: metres}}. Falls back to the built-in FABRIC_METERS estimates.
var ADMIN_FABRIC_METERS = null;
function fabricMetersFor(typeKey, size){
  if (ADMIN_FABRIC_METERS && ADMIN_FABRIC_METERS[typeKey] && ADMIN_FABRIC_METERS[typeKey][size] != null) {
    return ADMIN_FABRIC_METERS[typeKey][size];
  }
  var m = FABRIC_METERS[typeKey] || FABRIC_METERS.pant;
  return (m && m[size] != null) ? m[size] : null;
}

var selDelivery='pickup', isUrgent=false;

// Convert full garment name (from DB) to the key used in DETAILS / MANUAL / TURNAROUND maps
function nameToKey(n){
  n=(n||'').toLowerCase();
  if(n.indexOf('3-piece')>-1||n.indexOf('3 piece')>-1||n.indexOf('three')>-1) return 'suit3pc';
  if(n.indexOf('safari')>-1) return 'safari';
  // "Suit Shirt" / "Suit-Shirt" is a SHIRT style (~1.3-1.7m of fabric), not a
  // full suit (~3.2-4.4m) — match it as a shirt before the generic 'suit' check
  // so its fabric estimate (and admin overrides keyed under "shirt") apply correctly.
  if(n.indexOf('shirt')>-1) return 'shirt';
  if(n.indexOf('suit')>-1) return 'suit';
  if(n.indexOf('blazer')>-1||n.indexOf('waistcoat')>-1) return 'blazer';
  if(n.indexOf('kurta')>-1&&n.indexOf('pajama')>-1) return 'kurtaset';
  if(n.indexOf('kurta')>-1) return 'kurta';
  if(n.indexOf('pathani')>-1) return 'pathani';
  if(n.indexOf('pajama')>-1) return 'pajama';
  if(n.indexOf('jean')>-1) return 'jeans';
  if(n.indexOf('alteration')>-1||n.indexOf('repair')>-1) return 'shirt';
  // pants / fits / cuts / pleats
  return 'pant';
}

// ── Per-garment quantity store ─────────────────────────────────────────────────
var garmentQtys={};

function getCheckedInputs(){
  return Array.from(document.querySelectorAll('input[name="garment_type[]"]:checked'));
}

// ── Main garment changed handler (renamed — commission.html defines the active garmentChanged with style-popup support; this duplicate was overriding it) ──
function _legacyGarmentChanged(inp){
  // Update card visual
  if(inp){
    var card=inp.closest('.g-card');
    if(card) card.classList.toggle('selected', inp.checked);
    if(!inp.checked) delete garmentQtys[inp.value];
    else if(!garmentQtys[inp.value]) garmentQtys[inp.value]=1;
  }
  buildQtyRows();
  // Show style details for last selected
  var checked=getCheckedInputs();
  if(checked.length>0) buildDetails(nameToKey(checked[checked.length-1].value));
  rebuildManualPanels();
  updatePrice();
  updateSummary();
  updateBtn();
}

// ── Per-garment qty rows ───────────────────────────────────────────────────────
function buildQtyRows(){
  var wrap=document.getElementById('garmentQtyRows');
  if(!wrap) return;
  var checked=getCheckedInputs();
  if(!checked.length){wrap.innerHTML='';return;}
  wrap.innerHTML=checked.map(function(inp){
    var qty=garmentQtys[inp.value]||1;
    var price=PRICES[inp.value]||parseInt(inp.dataset.price)||0;
    return '<div style="display:flex;align-items:center;justify-content:space-between;padding:10px 14px;background:var(--bg2);border:1px solid var(--border);border-radius:10px;">'
      +'<div style="font-size:14px;font-weight:500;color:var(--dark);">'+inp.dataset.label+'</div>'
      +'<div style="display:flex;align-items:center;gap:10px;">'
      +'<div style="display:flex;align-items:center;border:1px solid var(--border);border-radius:8px;overflow:hidden;">'
      +'<button type="button" onclick="changeGarmentQty(\''+inp.value+'\',-1)" style="background:var(--bg3);border:none;width:32px;height:32px;font-size:16px;cursor:pointer;color:var(--dark);">−</button>'
      +'<span id="gqty_'+inp.value+'" style="width:36px;text-align:center;font-size:14px;font-weight:600;color:var(--dark);">'+qty+'</span>'
      +'<button type="button" onclick="changeGarmentQty(\''+inp.value+'\',1)" style="background:var(--bg3);border:none;width:32px;height:32px;font-size:16px;cursor:pointer;color:var(--dark);">+</button>'
      +'</div>'
      +'<span style="font-size:13px;color:var(--gold);font-weight:600;min-width:70px;text-align:right;">Rs. '+(price*qty).toLocaleString('en-IN')+'</span>'
      +'<input type="hidden" name="qty_'+inp.value+'" value="'+qty+'">'
      +'</div>'
      +'</div>';
  }).join('');
}

function changeGarmentQty(val, d){
  garmentQtys[val]=Math.max(1,Math.min(20,(garmentQtys[val]||1)+d));
  // Update display
  var el=document.getElementById('gqty_'+val);
  if(el) el.textContent=garmentQtys[val];
  // Update price display in row
  buildQtyRows();
  updatePrice();
  updateSummary();
}

// ── Price & Summary ───────────────────────────────────────────────────────────
function updatePrice(){
  var pe=document.getElementById('summary-price');
  var de=document.getElementById('summary-date');
  var checked=getCheckedInputs();
  if(!pe||!checked.length){if(pe)pe.style.display='none';if(de)de.style.display='none';return;}
  pe.style.display='block';
  var stitch=0;
  checked.forEach(function(inp){
    var qty=garmentQtys[inp.value]||1;
    stitch+=(PRICES[inp.value]||parseInt(inp.dataset.price)||0)*qty;
  });
  var urgent=isUrgent?99:0;
  var freeDelivery=stitch>=1499;
  var delivery=selDelivery==='home'?(freeDelivery?0:49):0;
  var total=stitch+urgent+delivery;
  var advance=Math.round(total*0.3);
  var su=document.getElementById('sp-unit');if(su)su.textContent='Rs. '+stitch.toLocaleString('en-IN');
  var ur=document.getElementById('sp-urg-row');if(ur)ur.style.display=isUrgent?'flex':'none';
  var dr=document.getElementById('sp-del-row');if(dr)dr.style.display=selDelivery==='home'?'flex':'none';
  var da=document.getElementById('sp-del-amt');if(da)da.textContent=freeDelivery?'Free':'Rs. 49';
  var sa=document.getElementById('sp-adv');if(sa)sa.textContent='Rs. '+advance.toLocaleString('en-IN');
  if(de){
    de.style.display='block';
    var maxDays=Math.max.apply(null,checked.map(function(inp){return isUrgent?2:(TURNAROUND[inp.value]||7);}));
    var dt=new Date();dt.setDate(dt.getDate()+maxDays);
    var sdv=document.getElementById('sd-val');if(sdv)sdv.textContent=dt.toLocaleDateString('en-IN',{day:'numeric',month:'long',year:'numeric'});
  }
}

function updateSummary(){
  // Delegate to refreshSummary if available (commission.html)
  if(typeof refreshSummary==='function'){refreshSummary();}
  // Also update price which includes homevisit charge
  if(typeof refreshPrice==='function'){refreshPrice();}
}

function updateBtn(){
  var checked=getCheckedInputs();
  var name=(document.getElementById('cust_name')||{}).value||'';
  var phone=(document.getElementById('cust_phone')||{}).value||'';
  var dateVal=(document.getElementById('delivery_date_input')||{}).value||'';
  var btn=document.getElementById('reserveBtn');
  if(btn)btn.disabled=!(checked.length>0&&name.trim().length>1&&phone.trim().length===10&&dateVal);
}

// ── Preselect from URL (from services page popup) ─────────────────────────────
window.addEventListener('load', function(){
  var params=new URLSearchParams(window.location.search);
  var garmentName=(params.get('garment')||'').toLowerCase().trim();
  var qty=parseInt(params.get('qty'))||1;
  if(!garmentName) return;

  var matched=null;
  // First try: match by checkbox VALUE directly (e.g. "shirt", "pant")
  document.querySelectorAll('input[name="garment_type[]"]').forEach(function(inp){
    if(matched) return;
    if(inp.value.toLowerCase()===garmentName) matched=inp;
  });
  // Second try: match by data-label exact
  if(!matched){
    document.querySelectorAll('input[name="garment_type[]"]').forEach(function(inp){
      if(matched) return;
      if((inp.dataset.label||'').toLowerCase()===garmentName) matched=inp;
    });
  }
  // Third try: fuzzy prefix match
  if(!matched){
    document.querySelectorAll('input[name="garment_type[]"]').forEach(function(inp){
      if(matched) return;
      var label=(inp.dataset.label||'').toLowerCase();
      if(garmentName.startsWith(label)||label.startsWith(garmentName)) matched=inp;
    });
  }

  if(matched){
    matched.checked=true;
    garmentQtys[matched.value]=qty;
    var card=matched.closest('.g-card');
    if(card) card.classList.add('selected');
    buildQtyRows();
    buildDetails(nameToKey(matched.value));
    rebuildManualPanels();
    updatePrice();
    updateSummary();
    updateBtn();
  }
});

// ── Urgent ────────────────────────────────────────────────────────────────────
function toggleUrgent(cb){
  isUrgent=cb.checked;
  var checked=getCheckedInputs();
  var note=document.getElementById('urgentNote');
  if(isUrgent){
    var blocked=checked.some(function(inp){return URGENT_BLOCKED[inp.value];});
    if(blocked){if(note){note.textContent='Urgent not possible for one or more selected garments.';note.style.display='block';}cb.checked=false;isUrgent=false;return;}
  }
  if(note){note.textContent=isUrgent?'Prioritised. Ready in 1-3 days for simple garments.':'';note.style.display=isUrgent?'block':'none';}
  updatePrice();updateSummary();
}

// ── Size ──────────────────────────────────────────────────────────────────────
function pickSz(sz,btn){
  document.querySelectorAll('.sz-btn').forEach(function(b){b.classList.remove('active');});btn.classList.add('active');document.getElementById('sz_val').value=sz;
  var d=SIZES[sz];if(d&&document.getElementById('sizeDetail')){document.getElementById('sizeDetail').innerHTML='<div class="sdg"><div class="sdg-item">Chest <span>'+d.chest+'</span></div><div class="sdg-item">Waist <span>'+d.waist+'</span></div><div class="sdg-item">Shoulder <span>'+d.shoulder+'</span></div><div class="sdg-item">Shirt <span>'+d.shirt+'</span></div><div class="sdg-item">Pant <span>'+d.pant+'</span></div><div class="sdg-item">Hip <span>'+d.hip+'</span></div></div>';}
  updateSummary();updatePrice();updateBtn();
}
function pickFit(fit,btn){document.querySelectorAll('.fit-btn').forEach(function(b){b.classList.remove('active');});btn.classList.add('active');document.getElementById('fit_val').value=fit;}

// ── Method ────────────────────────────────────────────────────────────────────
function setMeth(m,btn){
  document.querySelectorAll('.meth-tab').forEach(function(t){t.classList.remove('active');});
  document.querySelectorAll('.meth-panel').forEach(function(p){p.classList.remove('active');});
  btn.classList.add('active');
  var panel=document.getElementById('mp-'+m);if(panel)panel.classList.add('active');
  document.getElementById('meth_val').value=m;updateSummary();updateBtn();
  if(typeof refreshPrice==='function')refreshPrice();
}

// ── Manual measurements ───────────────────────────────────────────────────────
function buildManual(g){
  var fields=MANUAL[g]||MANUAL.shirt;var grid=document.getElementById('manualGrid');if(!grid)return;
  grid.innerHTML=fields.map(function(f){return '<div class="field-group"><label class="field-label">'+f[1]+' (inches)</label><input type="number" name="manual_'+f[0]+'" class="field-input" step="0.5" min="10" max="80" placeholder="e.g. 38"></div>';}).join('');
}

// ── Per-garment manual measurements (one field-set per selected garment) ──────
function rebuildManualPanels(){
  var grid=document.getElementById('manualGrid');
  if(!grid) return;
  var checked=getCheckedInputs();
  var mapInput=document.getElementById('manualGarmentMapInput');
  if(!checked.length){
    grid.innerHTML='';
    if(mapInput) mapInput.value='{}';
    return;
  }
  var map={};
  var esc=(typeof sdEsc==='function')?sdEsc:function(s){return String(s||'');};
  grid.innerHTML=checked.map(function(inp,i){
    var name=inp.dataset.label||inp.value;
    map[i]=name;
    var key=nameToKey(inp.value);
    var fields=MANUAL[key]||MANUAL.shirt;
    var fieldsHtml=fields.map(function(f){
      return '<div class="field-group"><label class="field-label">'+f[1]+' (inches)</label><input type="number" name="manual_g'+i+'_'+f[0]+'" class="field-input" step="0.5" min="10" max="80" placeholder="e.g. 38"></div>';
    }).join('');
    return '<div class="manual-garment-block" style="margin-bottom:18px;">'
      + (checked.length>1 ? '<div style="font-size:13px;font-weight:700;color:var(--dark);margin-bottom:8px;">'+esc(name)+'</div>' : '')
      + '<div class="manual-grid-inner" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:12px;">'+fieldsHtml+'</div>'
      + '</div>';
  }).join('');
  if(mapInput) mapInput.value=JSON.stringify(map);
}
buildManual('shirt');

// ── Style details ─────────────────────────────────────────────────────────────
function buildDetails(g){
  var groups=DETAILS[g]||[];var grid=document.getElementById('detailsGrid');if(!grid)return;
  if(!groups.length){grid.innerHTML='<p style="font-size:13px;color:var(--muted);">No style options.</p>';return;}
  grid.innerHTML=groups.map(function(gr){
    var opts=gr.o.map(function(opt,i){return '<button type="button" class="det-opt'+(i===0?' active':'')+'" data-k="'+gr.k+'" onclick="pickDet(\''+gr.k+'\',\''+opt+'\',this)">'+opt+'</button>'+(i===0?'<input type="hidden" name="detail_'+gr.k+'" id="dv_'+gr.k+'" value="'+opt+'">':'');}).join('');
    return '<div class="det-group"><span class="det-label">'+gr.l+'</span><div class="det-opts">'+opts+'</div></div>';
  }).join('');
}
function pickDet(k,v,btn){btn.closest('.det-opts').querySelectorAll('[data-k="'+k+'"]').forEach(function(b){b.classList.remove('active');});btn.classList.add('active');var hid=document.getElementById('dv_'+k);if(hid)hid.value=v;}

// ── Fabric ────────────────────────────────────────────────────────────────────
function setFab(choice,btn){document.querySelectorAll('.fab-tab').forEach(function(t){t.classList.remove('active');});btn.classList.add('active');document.getElementById('fab_choice').value=choice;document.getElementById('fab-own').style.display=choice==='own'?'block':'none';document.getElementById('fab-catalog').style.display=choice==='catalog'?'block':'none';}
function selFab(id,name,card){document.querySelectorAll('.fab-card').forEach(function(c){c.classList.remove('sel');});card.classList.add('sel');document.getElementById('fab_selected').value=id;}
var fabEl=document.getElementById('fabSearch');if(fabEl){fabEl.addEventListener('input',function(){var q=this.value.toLowerCase();document.querySelectorAll('.fab-card').forEach(function(c){c.style.display=(!q||(c.dataset.name||'').includes(q))?'':'none';});});}

// ── Delivery ──────────────────────────────────────────────────────────────────
function delChange(v){selDelivery=v;var el=document.getElementById('del-addr');if(el)el.style.display=v==='home'?'block':'none';updatePrice();updateSummary();}

// ── Locker ────────────────────────────────────────────────────────────────────
async function fetchLocker(){
  var phone=document.getElementById('locker_phone').value.trim();if(phone.length!==10){alert('Enter valid 10-digit number.');return;}
  var btn=document.querySelector('#mp-locker .fetch-btn');btn.textContent='Sending...';btn.disabled=true;
  try{var r=await fetch('/api/locker/send-otp',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone:phone})});var d=await r.json();
  if(d.success){document.getElementById('locker-otp').style.display='block';btn.textContent='OTP sent';}else{btn.textContent=d.message||'Not found';btn.disabled=false;}}
  catch(e){btn.textContent='Error';btn.disabled=false;}
}
async function verifyLocker(){
  var phone=document.getElementById('locker_phone').value.trim();var otp=document.getElementById('locker_otp').value.trim();
  var btn=document.querySelector('#locker-otp .fetch-btn');btn.textContent='Verifying...';btn.disabled=true;
  try{var r=await fetch('/api/locker/verify-otp',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone:phone,otp:otp})});var d=await r.json();
  if(d.success){document.getElementById('locker_cid').value=d.customer.id;if(d.customer.name)document.getElementById('cust_name').value=d.customer.name;document.getElementById('locker-found').style.display='block';document.getElementById('locker-found').textContent=d.customer.name+' - loaded.';document.getElementById('locker-otp').style.display='none';updateSummary();updateBtn();}
  else{btn.textContent=d.message||'Wrong OTP';btn.disabled=false;}}
  catch(e){btn.textContent='Error';btn.disabled=false;}
}

// ── Form submit ───────────────────────────────────────────────────────────────
var form=document.getElementById('commissionForm');
if(form){form.addEventListener('submit',async function(e){
  e.preventDefault();
  var checked=getCheckedInputs();
  if(!checked.length){alert('Please select at least one garment.');return;}

  // ── Login gate: must be logged in before placing order ──
  try{
    var meRes=await fetch('/api/account/me');
    var meData=await meRes.json();
    if(!meData||!meData.ok){
      // Not logged in — show account modal, queue form submit after login
      if(typeof openAccountModal==='function'){
        window._acctPendingFormSubmit=true;
        openAccountModal('Order place karne ke liye ek free account banao — sirf 30 seconds. Aapke saare orders yahan track honge.');
        var acctBtn=document.getElementById('acctSubmitBtn');
        if(acctBtn) acctBtn.textContent='Create account & place order';
      }
      return;
    }
  }catch(err){}
  // ── Logged in — proceed with order ──

  var btn=document.getElementById('reserveBtn');btn.disabled=true;btn.querySelector('span').textContent='Processing...';
  try{
    var res=await fetch('/api/orders/create',{method:'POST',body:new FormData(this)});
    var data=await res.json();
    if(data.success&&data.payment_url)window.location.href=data.payment_url;
    else{alert(data.message||'Something went wrong.');btn.disabled=false;btn.querySelector('span').textContent='Complete Your Order';}
  }catch(err){alert('Network error. Please try again.');btn.disabled=false;btn.querySelector('span').textContent='Complete Your Order';}
});}

// ── Misc ──────────────────────────────────────────────────────────────────────
function openSizeGuide(e){e.preventDefault();var m=document.getElementById('sizeGuideModal');if(m)m.style.display='flex';}
document.querySelectorAll('input[name="ref_dropoff"]').forEach(function(r){r.addEventListener('change',function(){var el=document.getElementById('ref-pickup-addr');if(el)el.style.display=r.value==='pickup'?'block':'none';});});
document.querySelectorAll('#cust_name,#cust_phone').forEach(function(el){if(el)el.addEventListener('input',updateBtn);});
var _dateInp=document.getElementById('delivery_date_input');if(_dateInp)_dateInp.addEventListener('change',updateBtn);