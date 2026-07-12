from flask import Blueprint, render_template, render_template_string, request, redirect, url_for, session, jsonify, flash
import json
from functools import wraps
from datetime import date, datetime, timedelta
from database import get_db, get_setting, set_setting

bp = Blueprint("owner", __name__, url_prefix="/owner")


ORDERS_PAGE = """{% extends 'base.html' %}
{% block title %}Orders & Progress — Owner{% endblock %}
{% block content %}
<div class="page-header">
  <div><h1>📋 Orders & Progress</h1><div class="header-sub">{{ total }} orders total</div></div>
  <div style="display:flex;gap:8px;align-items:center;">
    <a href="/owner/dashboard" class="btn btn-ghost btn-sm">← Dashboard</a>
    <button class="menu-toggle" onclick="openSidebar()">☰</button>
  </div>
</div>
{% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}<div style="padding:8px 24px 0;">{% for cat,msg in messages %}<div style="background:{{'#d1fae5' if cat=='success' else '#fee2e2'}};color:{{'#065f46' if cat=='success' else '#dc2626'}};padding:10px 16px;border-radius:10px;font-weight:700;font-size:13px;margin-bottom:4px;">{{ msg }}</div>{% endfor %}</div>{% endif %}{% endwith %}

<div class="page-body" style="padding:12px 24px;">

  <!-- ═══ TAB SWITCHER ═══ -->
  <div style="display:flex;gap:0;border-bottom:2px solid var(--border);margin-bottom:16px;">
    <button id="tab-orders-btn" onclick="switchTab('orders')"
      style="padding:10px 24px;font-size:14px;font-weight:800;border:none;background:none;border-bottom:3px solid var(--accent);color:var(--accent);cursor:pointer;margin-bottom:-2px;">
      📋 Order Management
    </button>
    <button id="tab-wp-btn" onclick="switchTab('workprogress')"
      style="padding:10px 24px;font-size:14px;font-weight:800;border:none;background:none;border-bottom:3px solid transparent;color:var(--text-muted);cursor:pointer;margin-bottom:-2px;">
      📊 Work Progress
    </button>
  </div>

  <!-- Search + Filter (always visible) -->
  <div id="orders-filter-bar" style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;align-items:center;">
    <input type="text" id="srch" placeholder="Search #code, name, mobile..." oninput="filterOrders()"
      style="flex:1;min-width:200px;padding:10px 16px;font-size:14px;border:2px solid var(--border);border-radius:12px;outline:none;">
    <span id="dues-badge" style="display:none;background:#fef3c7;color:#b45309;border:1.5px solid #fde68a;border-radius:10px;padding:6px 14px;font-size:12px;font-weight:800;">💰 Pending dues only</span>
    <div style="display:flex;gap:6px;flex-wrap:wrap;">
      {% for key,label in [('all','All'),('pending','Pending'),('ready','Ready'),('delivered','Delivered'),('cancelled','Cancelled')] %}
      <button class="ftab" data-key="{{ key }}" onclick="setTab('{{ key }}',this)"
        style="padding:7px 14px;border-radius:10px;border:2px solid {% if key=='all' %}var(--accent){% else %}var(--border){% endif %};background:{% if key=='all' %}var(--accent){% else %}#fff{% endif %};color:{% if key=='all' %}#fff{% else %}var(--text-muted){% endif %};font-size:12px;font-weight:800;cursor:pointer;">{{ label }}</button>
      {% endfor %}
    </div>
  </div>

  <!-- ═══ ORDERS TAB ═══ -->
  <div id="tab-orders">
    <div style="overflow-x:auto;">
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead><tr style="background:#f8fafc;border-bottom:2px solid var(--border);">
          <th style="padding:10px 14px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Order</th>
          <th style="padding:10px 14px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Customer</th>
          <th style="padding:10px 14px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Garments</th>
          <th style="padding:10px 14px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Dates</th>
          <th style="padding:10px 14px;text-align:right;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Amount</th>
          <th style="padding:10px 14px;text-align:center;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Status</th>
          <th style="padding:10px 14px;text-align:center;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Actions</th>
        </tr></thead>
        <tbody id="tbody">
          {% for o in orders %}
          <tr class="orow" data-status="{{ o.status }}" data-remaining="{{ o.remaining }}"
            data-s="{{ o.order_code }} {{ o.cname|lower }} {{ o.mobile }} {{ o.garments|lower }}"
            style="border-bottom:1px solid var(--border);cursor:pointer;"
            onclick="toggleDetail('{{ o.order_code }}')"
            onmouseover="this.style.background='#f8fafc'" onmouseout="this.style.background=''">
            <td style="padding:12px 14px;">
              <div style="display:flex;align-items:center;gap:6px;">
                <span id="arrow-{{ o.order_code }}" style="font-size:10px;color:var(--text-muted);transition:transform 0.2s;display:inline-block;">▶</span>
                <div style="font-size:15px;font-weight:900;color:var(--accent);">#{{ o.order_code }}</div>
                {% if o.is_urgent %}<span style="background:#fee2e2;color:#dc2626;font-size:9px;font-weight:800;padding:1px 6px;border-radius:4px;">🔥</span>{% endif %}
              </div>
              {% if o.note %}<div style="font-size:11px;color:var(--text-muted);font-style:italic;padding-left:18px;">📝 {{ o.note[:30] }}</div>{% endif %}
            </td>
            <td style="padding:12px 14px;"><div style="font-weight:700;">{{ o.cname }}</div>{% if o.mobile %}<div style="font-size:11px;color:var(--text-muted);">{{ o.mobile }}</div>{% endif %}</td>
            <td style="padding:12px 14px;color:var(--text-secondary);max-width:140px;">{{ o.garments }}</td>
            <td style="padding:12px 14px;"><div style="font-size:11px;color:var(--text-muted);">Order: {{ o.order_date }}</div><div style="font-size:11px;color:var(--text-muted);">Delivery: <strong>{{ o.delivery_date }}</strong></div></td>
            <td style="padding:12px 14px;text-align:right;"><div style="font-weight:800;">₹{{ o.payable|int }}</div>{% if o.remaining > 0 %}<div style="font-size:11px;color:var(--danger);font-weight:700;">Due ₹{{ o.remaining|int }}</div>{% else %}<div style="font-size:11px;color:var(--success);font-weight:700;">✓ Paid</div>{% endif %}</td>
            <td style="padding:12px 14px;text-align:center;"><span style="font-size:11px;padding:3px 10px;border-radius:8px;font-weight:800;background:{% if o.status=='delivered' %}#d1fae5;color:#065f46{% elif o.status=='ready' %}#ede9fe;color:#6d28d9{% elif o.status=='cancelled' %}#fee2e2;color:#dc2626{% else %}#dbeafe;color:#1e40af{% endif %};">{{ o.status|upper }}</span></td>
            <td style="padding:12px 14px;text-align:center;" onclick="event.stopPropagation()">
              <div style="display:flex;gap:4px;justify-content:center;flex-wrap:wrap;">
                <button onclick="window.open('/print-slip/{{ o.order_code }}','_blank')" style="background:var(--accent-light);color:var(--accent);border:none;border-radius:7px;padding:4px 9px;font-size:11px;font-weight:700;cursor:pointer;">🖨️</button>
                {% if o.status != 'delivered' and o.status != 'cancelled' %}
                <form action="/owner/orders/cancel/{{ o.order_code }}" method="POST" style="margin:0;" onsubmit="return confirm('Cancel #{{ o.order_code }}?')"><button type="submit" style="background:var(--danger-light);color:var(--danger);border:none;border-radius:7px;padding:4px 9px;font-size:11px;font-weight:700;cursor:pointer;">✕</button></form>
                {% endif %}
                <form action="/owner/orders/delete/{{ o.order_code }}" method="POST" style="margin:0;" onsubmit="return confirm('DELETE #{{ o.order_code }}?')"><button type="submit" style="background:#1f2937;color:#fff;border:none;border-radius:7px;padding:4px 9px;font-size:11px;font-weight:700;cursor:pointer;">🗑️</button></form>
              </div>
            </td>
          </tr>
          <!-- Expandable Detail Row -->
          <tr id="detail-{{ o.order_code }}" style="display:none;background:#f8faff;border-bottom:2px solid var(--accent);">
            <td colspan="7" style="padding:0;">
              <div id="detail-content-{{ o.order_code }}" style="padding:16px 20px;">
                <div style="color:var(--text-muted);font-size:13px;text-align:center;padding:16px;">Loading...</div>
              </div>
            </td>
          </tr>
          {% else %}
          <tr><td colspan="7" style="padding:40px;text-align:center;color:var(--text-muted);">No orders yet</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>

  <!-- ═══ WORK PROGRESS TAB ═══ -->
  <div id="tab-workprogress" style="display:none;">
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px;">
      {% for key,label in [('all','All Active'),('naap','📐 नाप Pending'),('cut','✂️ कटाई Pending'),('stitch','🪡 सिलाई Pending'),('done','✅ All Done')] %}
      <button class="wpf" data-key="{{ key }}" onclick="setWpFilter('{{ key }}',this)"
        style="padding:7px 14px;border-radius:10px;border:2px solid {% if key=='all' %}var(--accent){% else %}var(--border){% endif %};background:{% if key=='all' %}var(--accent){% else %}#fff{% endif %};color:{% if key=='all' %}#fff{% else %}var(--text-muted){% endif %};font-size:12px;font-weight:800;cursor:pointer;">{{ label }}</button>
      {% endfor %}
    </div>
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
      <thead><tr style="background:#f8fafc;border-bottom:2px solid var(--border);">
        <th style="padding:10px 14px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Order</th>
        <th style="padding:10px 14px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Customer</th>
        <th style="padding:10px 14px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Garments</th>
        <th style="padding:10px 14px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Delivery</th>
        <th style="padding:10px 14px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Progress</th>
        <th style="padding:10px 14px;text-align:center;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Pending</th>
      </tr></thead>
      <tbody id="wp-tbody">
        {% for o in wp_orders %}
        {% set all_done = o.naap_pct >= 100 and o.cut_pct >= 100 and o.stitch_pct >= 100 %}
        <tr class="wrow"
          data-naap="{{ 'done' if o.naap_pct>=100 else 'pending' }}"
          data-cut="{{ 'done' if o.cut_pct>=100 else 'pending' }}"
          data-stitch="{{ 'done' if o.stitch_pct>=100 else 'pending' }}"
          data-alldone="{{ 'yes' if all_done else 'no' }}"
          style="border-bottom:1px solid var(--border);"
          onmouseover="this.style.background='#fafbff'" onmouseout="this.style.background=''">
          <td style="padding:12px 14px;"><div style="font-size:15px;font-weight:900;color:var(--accent);">#{{ o.order_code }}</div>{% if o.is_urgent %}<span style="background:#fee2e2;color:#dc2626;font-size:9px;font-weight:800;padding:1px 6px;border-radius:4px;">🔥</span>{% endif %}</td>
          <td style="padding:12px 14px;"><div style="font-weight:700;">{{ o.cname }}</div><div style="font-size:11px;color:var(--text-muted);">{{ o.mobile }}</div></td>
          <td style="padding:12px 14px;color:var(--text-secondary);max-width:130px;font-size:12px;">{{ o.garments }}</td>
          <td style="padding:12px 14px;"><div style="font-size:13px;font-weight:700;">{{ o.delivery_date }}</div><div style="font-size:11px;color:var(--text-muted);">{{ o.status|upper }}</div></td>
          <td style="padding:12px 14px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
              <span style="font-size:9px;font-weight:800;color:{% if o.naap_pct>=100 %}#4f46e5{% else %}#9ca3af{% endif %};">नाप {% if o.naap_pct>=100 %}✓{% else %}{{ o.naap_pct }}%{% endif %}</span>
              <span style="font-size:9px;font-weight:800;color:{% if o.cut_pct>=100 %}#ea580c{% else %}#9ca3af{% endif %};">कटाई {% if o.cut_pct>=100 %}✓{% else %}{{ o.cut_pct }}%{% endif %}</span>
              <span style="font-size:9px;font-weight:800;color:{% if o.stitch_pct>=100 %}#16a34a{% else %}#9ca3af{% endif %};">सिलाई {% if o.stitch_pct>=100 %}✓{% else %}{{ o.stitch_pct }}%{% endif %}</span>
            </div>
            <div style="display:flex;gap:2px;height:10px;">
              <div style="flex:1;background:#e5e7eb;border-radius:4px;overflow:hidden;"><div style="height:100%;background:#4f46e5;width:{{ o.naap_pct }}%;"></div></div>
              <div style="flex:1;background:#e5e7eb;border-radius:4px;overflow:hidden;"><div style="height:100%;background:#ea580c;width:{{ o.cut_pct }}%;"></div></div>
              <div style="flex:1;background:#e5e7eb;border-radius:4px;overflow:hidden;"><div style="height:100%;background:#16a34a;width:{{ o.stitch_pct }}%;"></div></div>
            </div>
          </td>
          <td style="padding:12px 14px;text-align:center;">
            {% if all_done %}<span style="background:#d1fae5;color:#065f46;border-radius:8px;padding:4px 10px;font-size:11px;font-weight:800;">✅ All Done</span>
            {% else %}<div style="display:flex;flex-direction:column;gap:3px;align-items:center;">
              {% if o.naap_pct < 100 %}<span style="background:#eef2ff;color:#4f46e5;border-radius:6px;padding:2px 8px;font-size:10px;font-weight:800;">📐 नाप</span>{% endif %}
              {% if o.cut_pct < 100 %}<span style="background:#fff7ed;color:#ea580c;border-radius:6px;padding:2px 8px;font-size:10px;font-weight:800;">✂️ कटाई</span>{% endif %}
              {% if o.stitch_pct < 100 %}<span style="background:#f0fdf4;color:#16a34a;border-radius:6px;padding:2px 8px;font-size:10px;font-weight:800;">🪡 सिलाई</span>{% endif %}
            </div>{% endif %}
          </td>
        </tr>
        {% else %}
        <tr><td colspan="6" style="padding:40px;text-align:center;color:var(--text-muted);">All orders delivered! 🎉</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>

<!-- Image Overlay -->
<div id="img-overlay-orders" onclick="this.style.display='none'" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.92);z-index:9999;align-items:center;justify-content:center;">
  <img id="ov-img-orders" style="max-width:90%;max-height:90%;border-radius:12px;object-fit:contain;">
  <button onclick="document.getElementById('img-overlay-orders').style.display='none';event.stopPropagation();" style="position:absolute;top:16px;right:16px;background:rgba(255,255,255,0.15);border:none;color:#fff;width:44px;height:44px;border-radius:50%;font-size:22px;cursor:pointer;">✕</button>
</div>

{% endblock %}
{% block extra_js %}<script>
// ─── STATE ───────────────────────────────────────
var activeTab = "all";
var activeFilter = "{{filter_mode}}";
var expandedCode = null;

// ─── ON LOAD ──────────────────────────────────────
window.addEventListener("DOMContentLoaded", function() {
  if (activeFilter === "dues") {
    var badge = document.getElementById("dues-badge");
    if (badge) badge.style.display = "inline-block";
    filterOrders();
  }
});

// ─── TAB SWITCHING (Orders / Work Progress) ───────
function switchTab(tab) {
  var ordersDiv = document.getElementById("tab-orders");
  var wpDiv     = document.getElementById("tab-workprogress");
  var filterBar = document.getElementById("orders-filter-bar");
  var ordBtn    = document.getElementById("tab-orders-btn");
  var wpBtn     = document.getElementById("tab-wp-btn");
  var isOrders  = (tab === "orders");

  if (ordersDiv) ordersDiv.style.display = isOrders ? "block" : "none";
  if (wpDiv)     wpDiv.style.display     = isOrders ? "none"  : "block";
  if (filterBar) filterBar.style.display = isOrders ? "flex"  : "none";

  ordBtn.style.borderBottomColor = isOrders ? "var(--accent)" : "transparent";
  ordBtn.style.color = isOrders ? "var(--accent)" : "var(--text-muted)";
  ordBtn.style.fontWeight = "800";

  wpBtn.style.borderBottomColor = isOrders ? "transparent" : "#ea580c";
  wpBtn.style.color = isOrders ? "var(--text-muted)" : "#ea580c";
  wpBtn.style.fontWeight = "800";
}

// ─── STATUS FILTER TABS ───────────────────────────
function setTab(k, btn) {
  activeTab = k;
  document.querySelectorAll(".ftab").forEach(function(b) {
    b.style.background = "#fff";
    b.style.color = "var(--text-muted)";
    b.style.borderColor = "var(--border)";
  });
  btn.style.background = "var(--accent)";
  btn.style.color = "#fff";
  btn.style.borderColor = "var(--accent)";
  filterOrders();
}

// ─── SEARCH + FILTER ──────────────────────────────
function filterOrders() {
  var srch = document.getElementById("srch");
  var q = srch ? srch.value.toLowerCase().trim() : "";
  document.querySelectorAll("#tbody .orow").forEach(function(r) {
    var hasDue   = parseFloat(r.dataset.remaining || 0) > 0;
    var matchQ   = !q || (r.dataset.s || "").includes(q);
    var matchF   = activeTab === "all" || r.dataset.status === activeTab;
    var matchDues = activeFilter !== "dues" || (hasDue && r.dataset.status !== "delivered" && r.dataset.status !== "cancelled");
    var show = matchQ && matchF && matchDues;
    r.style.display = show ? "" : "none";
    // hide detail row if parent hidden
    var arrow = r.querySelector("[id^='arrow-']");
    if (arrow) {
      var code = arrow.id.replace("arrow-", "");
      var dr = document.getElementById("detail-" + code);
      if (dr && !show) { dr.style.display = "none"; }
    }
  });
}

// ─── EXPANDABLE ROWS ──────────────────────────────
function toggleDetail(code) {
  var dr    = document.getElementById("detail-" + code);
  var arrow = document.getElementById("arrow-" + code);
  if (!dr || !arrow) return;

  if (expandedCode && expandedCode !== code) {
    var prev      = document.getElementById("detail-" + expandedCode);
    var prevArrow = document.getElementById("arrow-" + expandedCode);
    if (prev)      prev.style.display = "none";
    if (prevArrow) prevArrow.style.transform = "rotate(0deg)";
    expandedCode = null;
  }

  if (dr.style.display === "none" || dr.style.display === "") {
    dr.style.display = "table-row";
    arrow.style.transform = "rotate(90deg)";
    expandedCode = code;
    loadDetail(code);
  } else {
    dr.style.display = "none";
    arrow.style.transform = "rotate(0deg)";
    expandedCode = null;
  }
}

function loadDetail(code) {
  var container = document.getElementById("detail-content-" + code);
  if (!container || container.dataset.loaded === "1") return;
  container.innerHTML = '<div style="color:var(--text-muted);font-size:13px;text-align:center;padding:16px;">Loading...</div>';

  fetch("/owner/api/order-detail/" + code)
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.error) { container.innerHTML = '<div style="color:red;padding:12px;">Error loading</div>'; return; }
      var o = d.order;
      var html = '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;">';

      // Col 1: Customer + Payment
      html += '<div>';
      html += '<div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);margin-bottom:8px;">👤 Customer & Payment</div>';
      html += '<div style="font-size:15px;font-weight:800;">' + o.cname + '</div>';
      html += '<div style="font-size:12px;color:var(--text-muted);">📱 ' + o.mobile + '</div>';
      html += '<div style="margin-top:10px;background:#f8fafc;border-radius:8px;padding:10px;">';
      html += '<div style="display:flex;justify-content:space-between;font-size:12px;padding:3px 0;"><span style="color:var(--text-muted);">Total Bill</span><span style="font-weight:700;">₹' + Math.round(o.payable) + '</span></div>';
      html += '<div style="display:flex;justify-content:space-between;font-size:12px;padding:3px 0;"><span style="color:var(--text-muted);">Advance</span><span style="font-weight:700;color:#16a34a;">₹' + Math.round(o.advance) + '</span></div>';
      html += '<div style="display:flex;justify-content:space-between;font-size:13px;padding:4px 0;border-top:1px solid var(--border);margin-top:3px;"><span style="font-weight:800;color:' + (o.remaining > 0 ? "#dc2626" : "#16a34a") + ';">' + (o.remaining > 0 ? "Due" : "✓ Paid") + '</span><span style="font-weight:900;color:' + (o.remaining > 0 ? "#dc2626" : "#16a34a") + ';">₹' + Math.round(o.remaining) + '</span></div>';
      html += '</div></div>';

      // Col 2: Garments
      html += '<div>';
      html += '<div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);margin-bottom:8px;">👕 Garments & Measurements</div>';
      d.garments.forEach(function(g) {
        html += '<div style="background:#fff;border:1px solid var(--border);border-radius:8px;padding:10px;margin-bottom:8px;">';
        html += '<div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span style="font-weight:800;">' + g.type + ' x' + g.qty + '</span><span style="color:var(--accent);font-weight:700;">₹' + Math.round(g.amount) + '</span></div>';
        if (g.measurements) {
          var mkeys = Object.keys(g.measurements);
          if (mkeys.length > 0) {
            html += '<div style="display:flex;flex-wrap:wrap;gap:4px;">';
            mkeys.forEach(function(k) { if (g.measurements[k]) html += '<span style="background:#f1f5f9;border-radius:5px;padding:2px 8px;font-size:11px;"><span style="color:var(--text-muted);">' + k + ':</span> <b>' + g.measurements[k] + '</b></span>'; });
            html += '</div>';
          }
        }
        html += '</div>';
      });
      html += '</div>';

      // Col 3: Progress + Photos
      html += '<div>';
      html += '<div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);margin-bottom:8px;">📊 Progress & Photos</div>';
      html += '<div style="display:flex;justify-content:space-between;margin-bottom:4px;">';
      html += '<span style="font-size:10px;font-weight:800;color:' + (o.naap_pct>=100?"#4f46e5":"#9ca3af") + ';">नाप ' + (o.naap_pct>=100?"✓":o.naap_pct+"%") + '</span>';
      html += '<span style="font-size:10px;font-weight:800;color:' + (o.cut_pct>=100?"#ea580c":"#9ca3af") + ';">कटाई ' + (o.cut_pct>=100?"✓":o.cut_pct+"%") + '</span>';
      html += '<span style="font-size:10px;font-weight:800;color:' + (o.stitch_pct>=100?"#16a34a":"#9ca3af") + ';">सिलाई ' + (o.stitch_pct>=100?"✓":o.stitch_pct+"%") + '</span>';
      html += '</div>';
      html += '<div style="display:flex;gap:2px;height:10px;margin-bottom:12px;">';
      html += '<div style="flex:1;background:#e5e7eb;border-radius:4px;overflow:hidden;"><div style="height:100%;background:#4f46e5;width:' + o.naap_pct + '%;"></div></div>';
      html += '<div style="flex:1;background:#e5e7eb;border-radius:4px;overflow:hidden;"><div style="height:100%;background:#ea580c;width:' + o.cut_pct + '%;"></div></div>';
      html += '<div style="flex:1;background:#e5e7eb;border-radius:4px;overflow:hidden;"><div style="height:100%;background:#16a34a;width:' + o.stitch_pct + '%;"></div></div>';
      html += '</div>';
      if (d.images && d.images.length > 0) {
        html += '<div style="display:flex;flex-wrap:wrap;gap:6px;">';
        d.images.forEach(function(src) {
          html += '<img src="' + src + '" onclick="openImgOverlay(this.src)" style="width:70px;height:70px;object-fit:cover;border-radius:8px;border:2px solid var(--border);cursor:zoom-in;">';
        });
        html += '</div>';
      } else {
        html += '<div style="font-size:12px;color:var(--text-muted);">No photos</div>';
      }
      html += '</div></div>';

      container.innerHTML = html;
      container.dataset.loaded = "1";
    })
    .catch(function() { container.innerHTML = '<div style="color:red;padding:12px;">Could not load details.</div>'; });
}

function openImgOverlay(src) {
  var ov = document.getElementById("img-overlay-orders");
  if (ov) { document.getElementById("ov-img-orders").src = src; ov.style.display = "flex"; }
}

// ─── WORK PROGRESS FILTER ─────────────────────────
function setWpFilter(f, btn) {
  document.querySelectorAll(".wpf").forEach(function(b) {
    b.style.background = "#fff"; b.style.color = "var(--text-muted)"; b.style.borderColor = "var(--border)";
  });
  btn.style.background = "var(--accent)"; btn.style.color = "#fff"; btn.style.borderColor = "var(--accent)";
  document.querySelectorAll(".wrow").forEach(function(r) {
    var show = f === "all"
      || (f === "naap"   && r.dataset.naap   === "pending")
      || (f === "cut"    && r.dataset.cut    === "pending")
      || (f === "stitch" && r.dataset.stitch === "pending")
      || (f === "done"   && r.dataset.alldone === "yes");
    r.style.display = show ? "" : "none";
  });
}

// ─── SESSION TIMEOUT ──────────────────────────────
const SECS = 5 * 60; let last = Date.now();
["click","keydown","mousemove","touchstart"].forEach(function(ev) {
  document.addEventListener(ev, function() { last = Date.now(); }, {passive:true});
});
setInterval(function() {
  if (Math.floor((Date.now() - last) / 1000) >= SECS) window.location.href = "/owner/login?expired=1";
}, 5000);
window.addEventListener("pageshow", function(e) {
  if (e.persisted) { fetch("/owner/logout", {method:"POST",keepalive:true}).finally(function() { window.location.href = "/owner/login"; }); }
});
</script>{% endblock %}
"""


CUSTOMERS_PAGE = """{% extends 'base.html' %}
{% block title %}Customers — Owner{% endblock %}
{% block content %}
<div class="page-header">
  <div><h1>👥 Customers</h1><div class="header-sub">{{ total }} total</div></div>
  <div style="display:flex;gap:8px;align-items:center;"><a href="/owner/export/orders" class="btn btn-ghost btn-sm" style="background:#d1fae5;color:#065f46;">📥 Export</a><a href="/owner/dashboard" class="btn btn-ghost btn-sm">← Dashboard</a><button class="menu-toggle" onclick="openSidebar()">☰</button></div>
</div>
<div class="page-body" style="padding:16px 24px;">
  <input type="text" id="srch" placeholder="Search name, mobile, order code..." oninput="filterRows()" style="padding:11px 16px;font-size:14px;border:2px solid var(--border);border-radius:12px;width:100%;max-width:400px;margin-bottom:16px;">
  <div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:13px;">
    <thead><tr style="background:#f8fafc;border-bottom:2px solid var(--border);"><th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Customer</th><th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Mobile</th><th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Address</th><th style="padding:10px 16px;text-align:center;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Orders</th><th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Codes</th><th style="padding:10px 16px;text-align:right;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Billed</th><th style="padding:10px 16px;text-align:right;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Due</th><th style="padding:10px 16px;text-align:right;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Last Order</th></tr></thead>
    <tbody id="tbody">{% for c in customers %}<tr class="crow" data-s="{{ c.name|lower }} {{ c.mobile }} {{ c.address|lower }} {{ c.order_codes }}" onclick="window.location='/owner/customers/{{ c.id }}'" style="border-bottom:1px solid var(--border);cursor:pointer;" onmouseover="this.style.background='#f8fafc'" onmouseout="this.style.background=''"><td style="padding:12px 16px;"><div style="font-size:14px;font-weight:800;">{{ c.name }}</div></td><td style="padding:12px 16px;color:var(--text-muted);">{{ c.mobile or '—' }}</td><td style="padding:12px 16px;color:var(--text-muted);max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ c.address or '—' }}</td><td style="padding:12px 16px;text-align:center;font-weight:800;color:var(--accent);">{{ c.order_count }}</td><td style="padding:12px 16px;color:var(--text-muted);font-size:11px;">{{ c.order_codes or '—' }}</td><td style="padding:12px 16px;text-align:right;font-weight:700;">₹{{ c.total_billed|int }}</td><td style="padding:12px 16px;text-align:right;font-weight:700;color:{% if c.total_due > 0 %}var(--danger){% else %}var(--success){% endif %};">{% if c.total_due > 0 %}₹{{ c.total_due|int }}{% else %}✓ Paid{% endif %}</td><td style="padding:12px 16px;text-align:right;color:var(--text-muted);font-size:12px;">{{ c.last_order_date or '—' }}</td></tr>{% else %}<tr><td colspan="8" style="padding:40px;text-align:center;color:var(--text-muted);">No customers yet</td></tr>{% endfor %}</tbody>
  </table></div>
</div>
{% endblock %}
{% block extra_js %}<script>function filterRows(){var q=document.getElementById("srch").value.toLowerCase().trim();document.querySelectorAll(".crow").forEach(function(r){r.style.display=(!q||r.dataset.s.includes(q))?"":"none";});}const SECS=5*60;let last=Date.now();["click","keydown","mousemove","touchstart"].forEach(ev=>document.addEventListener(ev,()=>{last=Date.now();},{passive:true}));setInterval(()=>{if(Math.floor((Date.now()-last)/1000)>=SECS)window.location.href="/owner/login?expired=1";},5000);window.addEventListener("pageshow",function(e){if(e.persisted){fetch("/owner/logout",{method:"POST",keepalive:true}).finally(()=>{window.location.href="/owner/login";})}});</script>{% endblock %}
"""

WORK_PROGRESS_PAGE = """{% extends 'base.html' %}
{% block title %}Work Progress — Owner{% endblock %}
{% block content %}
<div class="page-header">
  <div><h1>📊 Work Progress</h1><div class="header-sub">{{ total }} active orders</div></div>
  <div style="display:flex;gap:8px;"><a href="/owner/dashboard" class="btn btn-ghost btn-sm">← Dashboard</a><button class="menu-toggle" onclick="openSidebar()">☰</button></div>
</div>
<div class="page-body" style="padding:16px 24px;">
  <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px;">
    <button class="wtab active" onclick="setWTab('all',this)" style="padding:7px 14px;border-radius:10px;border:2px solid var(--accent);background:var(--accent);color:#fff;font-size:12px;font-weight:800;cursor:pointer;">All</button>
    <button class="wtab" onclick="setWTab('naap',this)" style="padding:7px 14px;border-radius:10px;border:2px solid var(--border);background:#fff;color:var(--text-muted);font-size:12px;font-weight:800;cursor:pointer;">📐 नाप Pending</button>
    <button class="wtab" onclick="setWTab('cut',this)" style="padding:7px 14px;border-radius:10px;border:2px solid var(--border);background:#fff;color:var(--text-muted);font-size:12px;font-weight:800;cursor:pointer;">✂️ कटाई Pending</button>
    <button class="wtab" onclick="setWTab('stitch',this)" style="padding:7px 14px;border-radius:10px;border:2px solid var(--border);background:#fff;color:var(--text-muted);font-size:12px;font-weight:800;cursor:pointer;">🪡 सिलाई Pending</button>
    <button class="wtab" onclick="setWTab('done',this)" style="padding:7px 14px;border-radius:10px;border:2px solid var(--border);background:#fff;color:var(--text-muted);font-size:12px;font-weight:800;cursor:pointer;">✅ All Done</button>
  </div>
  <div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:13px;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 8px rgba(0,0,0,0.07);">
    <thead><tr style="background:#f8fafc;border-bottom:2px solid var(--border);"><th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Order</th><th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Customer</th><th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Garments</th><th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Delivery</th><th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);min-width:180px;">Progress</th><th style="padding:10px 16px;text-align:center;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Pending</th></tr></thead>
    <tbody id="wp-tbody">{% for o in orders %}{% set all_done = o.naap_pct >= 100 and o.cut_pct >= 100 and o.stitch_pct >= 100 %}<tr class="wrow" data-naap="{{ 'pending' if o.naap_pct < 100 else 'done' }}" data-cut="{{ 'pending' if o.cut_pct < 100 else 'done' }}" data-stitch="{{ 'pending' if o.stitch_pct < 100 else 'done' }}" data-alldone="{{ 'yes' if all_done else 'no' }}" style="border-bottom:1px solid var(--border);" onmouseover="this.style.background='#fafbff'" onmouseout="this.style.background=''"><td style="padding:12px 16px;"><div style="font-size:15px;font-weight:900;color:var(--accent);">#{{ o.order_code }}</div>{% if o.is_urgent %}<span style="background:#fee2e2;color:#dc2626;font-size:9px;font-weight:800;padding:1px 6px;border-radius:4px;">🔥 URGENT</span>{% endif %}</td><td style="padding:12px 16px;"><div style="font-weight:700;">{{ o.cname }}</div>{% if o.mobile %}<div style="font-size:11px;color:var(--text-muted);">{{ o.mobile }}</div>{% endif %}</td><td style="padding:12px 16px;color:var(--text-secondary);max-width:130px;font-size:12px;">{{ o.garments }}</td><td style="padding:12px 16px;"><div style="font-size:13px;font-weight:700;">{{ o.delivery_date }}</div><div style="font-size:11px;color:var(--text-muted);">{{ o.status|upper }}</div></td><td style="padding:12px 16px;"><div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="font-size:9px;font-weight:800;color:{% if o.naap_pct>=100 %}#4f46e5{% else %}#9ca3af{% endif %};">नाप{% if o.naap_pct>=100 %} ✓{% else %} {{ o.naap_pct }}%{% endif %}</span><span style="font-size:9px;font-weight:800;color:{% if o.cut_pct>=100 %}#ea580c{% else %}#9ca3af{% endif %};">कटाई{% if o.cut_pct>=100 %} ✓{% else %} {{ o.cut_pct }}%{% endif %}</span><span style="font-size:9px;font-weight:800;color:{% if o.stitch_pct>=100 %}#16a34a{% else %}#9ca3af{% endif %};">सिलाई{% if o.stitch_pct>=100 %} ✓{% else %} {{ o.stitch_pct }}%{% endif %}</span></div><div style="display:flex;gap:2px;height:10px;"><div style="flex:1;background:#e5e7eb;border-radius:4px;overflow:hidden;"><div style="height:100%;background:#4f46e5;width:{{ o.naap_pct }}%;"></div></div><div style="flex:1;background:#e5e7eb;border-radius:4px;overflow:hidden;"><div style="height:100%;background:#ea580c;width:{{ o.cut_pct }}%;"></div></div><div style="flex:1;background:#e5e7eb;border-radius:4px;overflow:hidden;"><div style="height:100%;background:#16a34a;width:{{ o.stitch_pct }}%;"></div></div></div></td><td style="padding:12px 16px;text-align:center;">{% if all_done %}<span style="background:#d1fae5;color:#065f46;border-radius:8px;padding:4px 10px;font-size:11px;font-weight:800;">✅ All Done</span>{% else %}<div style="display:flex;flex-direction:column;gap:3px;align-items:center;">{% if o.naap_pct < 100 %}<span style="background:#eef2ff;color:#4f46e5;border-radius:6px;padding:2px 8px;font-size:10px;font-weight:800;">📐 नाप</span>{% endif %}{% if o.cut_pct < 100 %}<span style="background:#fff7ed;color:#ea580c;border-radius:6px;padding:2px 8px;font-size:10px;font-weight:800;">✂️ कटाई</span>{% endif %}{% if o.stitch_pct < 100 %}<span style="background:#f0fdf4;color:#16a34a;border-radius:6px;padding:2px 8px;font-size:10px;font-weight:800;">🪡 सिलाई</span>{% endif %}</div>{% endif %}</td></tr>{% else %}<tr><td colspan="6" style="padding:40px;text-align:center;color:var(--text-muted);">All orders delivered!</td></tr>{% endfor %}</tbody>
  </table></div>
</div>
{% endblock %}
{% block extra_js %}<script>function setWTab(key,btn){document.querySelectorAll(".wtab").forEach(function(b){b.style.background="#fff";b.style.color="var(--text-muted)";b.style.borderColor="var(--border)";});btn.style.background="var(--accent)";btn.style.color="#fff";btn.style.borderColor="var(--accent)";document.querySelectorAll(".wrow").forEach(function(r){var show=key==="all"||(key==="naap"&&r.dataset.naap==="pending")||(key==="cut"&&r.dataset.cut==="pending")||(key==="stitch"&&r.dataset.stitch==="pending")||(key==="done"&&r.dataset.alldone==="yes");r.style.display=show?"":"none";});}const SECS=5*60;let last=Date.now();["click","keydown","mousemove","touchstart"].forEach(ev=>document.addEventListener(ev,()=>{last=Date.now();},{passive:true}));setInterval(()=>{if(Math.floor((Date.now()-last)/1000)>=SECS)window.location.href="/owner/login?expired=1";},5000);window.addEventListener("pageshow",function(e){if(e.persisted){fetch("/owner/logout",{method:"POST",keepalive:true}).finally(()=>{window.location.href="/owner/login";})}});</script>{% endblock %}
"""

def fmt_d(d):
    """Format date string from YYYY-MM-DD to DD-MM-YYYY"""
    if not d: return "—"
    try:
        parts = str(d).split("-")
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except: pass
    return str(d)


def owner_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("owner_logged_in"):
            return redirect(url_for("owner.login", next=request.path))
        return f(*args, **kwargs)
    return decorated

@bp.route("/login")
def login():
    if request.args.get("expired"):
        flash("Session expired. Please login again.", "warning")
    # "next" lets callers (e.g. the employee dashboard's Website Admin button)
    # land back on the page they actually wanted after the PIN check passes,
    # instead of always dumping the user on /owner/dashboard.
    next_url = request.args.get("next", "")
    if not next_url.startswith("/owner/"):
        next_url = ""
    return render_template("owner/login.html", active_page=None, show_voice=False, urgent_count=0, next_url=next_url)

@bp.route("/verify-pin", methods=["POST"])
def verify_pin():
    data = request.get_json(silent=True) or {}
    entered = str(data.get("pin",""))
    real_pin = get_setting("owner_pin","1234")
    if entered == real_pin:
        session["owner_logged_in"] = True
        session.permanent = False
        next_url = str(data.get("next") or "")
        if not next_url.startswith("/owner/"):
            next_url = ""
        return jsonify({"ok": True, "next": next_url})
    return jsonify({"ok": False})

@bp.route("/logout", methods=["GET","POST"])
def logout():
    session.pop("owner_logged_in", None)
    return redirect(url_for("owner.login"))

@bp.route("/dashboard")
@owner_required
def dashboard():
    conn = get_db()
    today = date.today().isoformat()
    month_start = date.today().replace(day=1).isoformat()

    # Allow owner to pick a date via ?date=YYYY-MM-DD, default to most recent active date
    selected_date_str = request.args.get("date", "").strip()
    
    # If no date param, find the most recent date that has transactions
    # This fixes the server-date vs laptop-date mismatch
    if not selected_date_str:
        last_tx = conn.execute("SELECT tx_date FROM finance ORDER BY id DESC LIMIT 1").fetchone()
        if last_tx:
            # Use the date of the last transaction as "today" if it's within last 2 days
            from datetime import timedelta
            last_date = last_tx["tx_date"]
            server_today = date.today().isoformat()
            # If last transaction date is today or yesterday, show it
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            if last_date in [server_today, yesterday]:
                selected_date = last_date
            else:
                selected_date = server_today
        else:
            selected_date = today
    else:
        selected_date = selected_date_str
    
    # Recalculate month_start based on selected_date
    try:
        sel_dt = datetime.strptime(selected_date, "%Y-%m-%d").date()
    except:
        sel_dt = date.today()
    month_start = sel_dt.replace(day=1).isoformat()

    # Today income/expense totals (using selected_date)
    rows = conn.execute("SELECT tx_type, SUM(amount) as total FROM finance WHERE tx_date=? GROUP BY tx_type",(selected_date,)).fetchall()
    fin_today = {r["tx_type"]: r["total"] or 0 for r in rows}

    # Month totals
    rows_m = conn.execute("SELECT tx_type, SUM(amount) as total FROM finance WHERE tx_date >= ? GROUP BY tx_type",(month_start,)).fetchall()
    fin_month = {r["tx_type"]: r["total"] or 0 for r in rows_m}

    # Month cash/upi breakdown
    month_cash = conn.execute(
        "SELECT COALESCE(SUM(amount),0) as t FROM finance WHERE tx_date>=? AND tx_type='income' AND LOWER(mode)='cash'",(month_start,)
    ).fetchone()["t"]
    month_upi = conn.execute(
        "SELECT COALESCE(SUM(amount),0) as t FROM finance WHERE tx_date>=? AND tx_type='income' AND LOWER(mode)='upi'",(month_start,)
    ).fetchone()["t"]

    # Selected date cash/upi
    cash_today = conn.execute(
        "SELECT COALESCE(SUM(amount),0) as t FROM finance WHERE tx_date=? AND tx_type='income' AND LOWER(mode)='cash'",(selected_date,)
    ).fetchone()["t"]
    upi_today = conn.execute(
        "SELECT COALESCE(SUM(amount),0) as t FROM finance WHERE tx_date=? AND tx_type='income' AND LOWER(mode)='upi'",(selected_date,)
    ).fetchone()["t"]

    # Full transaction log for selected date
    today_transactions = conn.execute(
        "SELECT f.*, o.order_code FROM finance f LEFT JOIN orders o ON o.id=f.order_id WHERE f.tx_date=? ORDER BY f.id DESC",(selected_date,)
    ).fetchall()

    dues = conn.execute("SELECT SUM(remaining) as total, COUNT(*) as cnt FROM orders WHERE status != 'delivered' AND remaining > 0").fetchone()
    work_today = conn.execute("SELECT SUM(qty_done) as total FROM work_logs WHERE log_date=?",(today,)).fetchone()
    # If no work logs yet, count items from today's orders as a proxy
    work_today_val = (work_today["total"] or 0) if work_today else 0
    if work_today_val == 0:
        items_today = conn.execute("""SELECT COALESCE(SUM(oi.quantity),0) as total
            FROM order_items oi JOIN orders o ON o.id=oi.order_id
            WHERE o.order_date=?""",(today,)).fetchone()
        work_today_proxy = items_today["total"] or 0
    low_stock = conn.execute("SELECT * FROM inventory WHERE quantity <= low_alert_at ORDER BY quantity ASC").fetchall()
    urgent_count = conn.execute("SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status != 'delivered' AND delivery_date >= ?",(today,)).fetchone()["c"]

    # All rate settings
    custom_rates = conn.execute("SELECT key,value FROM settings WHERE key LIKE '%rate%'").fetchall()
    conn.close()

    today_str = datetime.today().strftime("%A, %d %B %Y")
    d = date.today()
    today_date = f"{d.day:02d}-{d.month:02d}-{d.year}"
    last_backup = get_setting("last_backup_at", "")

    garment_names = [
        "Shirt","Shirt Linen","Pant","Pant Double","Jeans","Suit 2pc","Suit 3pc",
        "Blazer","Kurta","Kurta Pajama","Pajama","Pathani","Safari","Waistcoat",
        "Alteration","Cutting Only"
    ]
    # Customer rates (what customers pay)
    deleted_csv = get_setting("deleted_customer_rates", "")
    deleted_set = set(x.strip() for x in deleted_csv.split(",") if x.strip())
    garment_rates = {}
    for n in garment_names:
        if n in deleted_set:
            continue
        r = get_setting("customer_rate_"+n,"") or get_setting("rate_"+n,"0")
        garment_rates[n] = r
    # Add custom customer rates
    for row in custom_rates:
        if row["key"].startswith("customer_rate_"):
            name = row["key"][14:]
            if name not in garment_rates and name not in deleted_set:
                garment_rates[name] = row["value"]

    # Stitching rates (what employees get paid)
    stitch_rates = {n: get_setting("stitch_rate_"+n,"0") for n in garment_names}
    for row in custom_rates:
        if row["key"].startswith("stitch_rate_"):
            name = row["key"][12:]
            if name not in stitch_rates:
                stitch_rates[name] = row["value"]

    return render_template("owner/dashboard.html",
        active_page="owner_dashboard", show_voice=False, urgent_count=urgent_count,
        today_str=today_str, today_date=selected_date,
        selected_date=selected_date,
        low_stock=low_stock,
        garment_rates=garment_rates,
        stitch_rates=stitch_rates,
        today_transactions=today_transactions,
        last_backup=last_backup,
        stats={
            "today_income":  fin_today.get("income",0),
            "today_expense": fin_today.get("expense",0),
            "today_cash":    cash_today,
            "today_upi":     upi_today,
            "month_income":  fin_month.get("income",0),
            "month_cash":    month_cash,
            "month_upi":     month_upi,
            "month_net":     fin_month.get("income",0) - fin_month.get("expense",0),
            "pending_dues":  dues["total"] or 0 if dues else 0,
            "pending_orders":dues["cnt"] or 0 if dues else 0,
            "work_today":    work_today_proxy if (work_today["total"] or 0)==0 else work_today["total"],
        }
    )

@bp.route("/settings")
@owner_required
def settings():
    conn = get_db()
    today = date.today().isoformat()
    urgent_count = conn.execute("SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status != 'delivered' AND delivery_date >= ?",(today,)).fetchone()["c"]
    conn.close()
    current_settings = {
        "shop_name":        get_setting("shop_name","Uttam Tailors"),
        "shop_name_hi":     get_setting("shop_name_hi","उत्तम टेलर्स"),
        "whatsapp_number":  get_setting("whatsapp_number",""),
        "default_language": get_setting("default_language","hl"),
        "order_code_start": get_setting("last_order_code","3600"),
    }
    garment_names_std = [
        "Shirt","Shirt Linen","Pant","Pant Double","Jeans","Suit 2pc","Suit 3pc",
        "Blazer","Kurta","Kurta Pajama","Pajama","Pathani","Safari",
        "Waistcoat","Alteration","Cutting Only"
    ]
    # Customer rates
    garment_rates = {}
    deleted_csv = get_setting("deleted_customer_rates", "")
    deleted_set = set(x.strip() for x in deleted_csv.split(",") if x.strip())
    for n in garment_names_std:
        if n in deleted_set:
            continue  # user deleted this garment type
        r = get_setting("customer_rate_"+n,"") or get_setting("rate_"+n,"0")
        garment_rates[n] = r
    # Add any custom customer garments
    from database import get_db as _gdb2
    _c2 = _gdb2()
    all_settings = _c2.execute("SELECT key,value FROM settings WHERE key LIKE 'customer_rate_%'").fetchall()
    _c2.close()
    for row in all_settings:
        name = row["key"][14:]
        if name not in garment_rates:
            garment_rates[name] = row["value"]

    # Stitching rates
    stitch_rates = {}
    for n in garment_names_std:
        stitch_rates[n] = get_setting("stitch_rate_"+n,"0")
    work_rates_map = {
        "work_rate_measurement": get_setting("work_rate_measurement","0"),
        "work_rate_cutting":     get_setting("work_rate_cutting","25"),
        "work_rate_alteration":  get_setting("work_rate_alteration","15"),
    }
    conn2 = get_db()
    # Garment type chips — always show all standard garment types
    ALL_GARMENTS = [
        "Shirt","Shirt Linen","Pant","Pant Double","Jeans",
        "Suit 2pc","Suit 3pc","Blazer","Kurta","Kurta Pajama",
        "Pajama","Pathani","Safari","Waistcoat",
        "Alteration","Cutting Only"
    ]
    existing_chips = {}
    for row in conn2.execute("SELECT key, value FROM settings WHERE key LIKE 'types_%'").fetchall():
        existing_chips[row["key"][6:]] = row["value"] or ""
    # Build ordered dict: standard first, then any custom
    garment_type_chips = {}
    for g in ALL_GARMENTS:
        garment_type_chips[g] = existing_chips.get(g, "")
    for g, v in existing_chips.items():
        if g not in garment_type_chips:
            garment_type_chips[g] = v
    try:
        conn2.execute("ALTER TABLE employees ADD COLUMN skills TEXT DEFAULT 'stitch'")
        conn2.execute("UPDATE employees SET skills='all' WHERE name='Kamal' AND (skills IS NULL OR skills='stitch')")
        conn2.commit()
    except Exception:
        try: conn2._conn.rollback()
        except Exception: pass
    all_employees = conn2.execute(
        "SELECT id, name, COALESCE(skills,'stitch') as skills FROM employees WHERE active=1 ORDER BY name"
    ).fetchall()
    conn2.close()
    return render_template("owner/settings.html",
        active_page="settings", show_voice=True, urgent_count=urgent_count,
        settings=current_settings, garment_rates=garment_rates,
        stitch_rates=stitch_rates, work_rates_map=work_rates_map,
        all_employees=all_employees,
        garment_type_chips=garment_type_chips,
        last_backup=get_setting("last_backup_at","")
    )

@bp.route("/settings/save", methods=["POST"])
@owner_required
def settings_save():
    section = request.form.get("section")
    if section == "shop":
        # Handle logo upload
        import base64
        logo_file = request.files.get("shop_logo")
        if logo_file and logo_file.filename:
            data = logo_file.read()
            ext = logo_file.filename.rsplit(".",1)[-1].lower()
            b64 = base64.b64encode(data).decode()
            set_setting("shop_logo", f"data:image/{ext};base64,{b64}")
            flash("Logo updated!", "success")
        set_setting("shop_name",        request.form.get("shop_name","").strip())
        set_setting("shop_name_hi",     request.form.get("shop_name_hi","").strip())
        set_setting("whatsapp_number",  request.form.get("whatsapp_number","").strip())
        set_setting("default_language", request.form.get("default_language","hl"))
        # Order code start - only update last_order_code if value given and valid
        new_code = request.form.get("order_code_start","").strip()
        if new_code.isdigit():
            set_setting("last_order_code", str(int(new_code) - 1))  # next call will increment to this
        from database import invalidate_settings_cache; invalidate_settings_cache()
        flash("Shop settings saved!", "success")
    elif section == "pin":
        current = request.form.get("current_pin","")
        new_pin = request.form.get("new_pin","")
        confirm = request.form.get("confirm_pin","")
        real_pin = get_setting("owner_pin","1234")
        if current != real_pin:
            flash("Current PIN is wrong.", "error")
        elif len(new_pin) != 4 or not new_pin.isdigit():
            flash("New PIN must be exactly 4 digits.", "error")
        elif new_pin != confirm:
            flash("PINs do not match.", "error")
        else:
            set_setting("owner_pin", new_pin)
            flash("PIN changed successfully!", "success")
    elif section == "customer_rates":
        # Load currently deleted garments list
        deleted_csv = get_setting("deleted_customer_rates", "")
        deleted_names = set(x.strip() for x in deleted_csv.split(",") if x.strip())
        # Process new deletes
        for name in request.form.getlist("delete_rate"):
            deleted_names.add(name)
            conn2 = get_db()
            conn2.execute("DELETE FROM settings WHERE key=?",("customer_rate_"+name,))
            conn2.execute("DELETE FROM settings WHERE key=?",("rate_"+name,))
            conn2.commit(); conn2.close()
        # Save deleted list
        set_setting("deleted_customer_rates", ",".join(sorted(deleted_names)))
        from database import invalidate_settings_cache; invalidate_settings_cache()
        # Then: save remaining rates (skip deleted ones)
        for key, val in request.form.items():
            if key.startswith("customer_rate_"):
                name = key[14:]
                if name in deleted_names:
                    continue  # skip re-saving deleted items
                if val.strip():
                    set_setting(key, val)
                    # Also sync to rate_X so new_order picks it up
                    set_setting("rate_"+name, val)
                    # If user re-adds a previously deleted garment, remove from deleted list
                    deleted_names.discard(name)
        set_setting("deleted_customer_rates", ",".join(sorted(deleted_names)))
        from database import invalidate_settings_cache; invalidate_settings_cache()
        flash("Customer rates saved!", "success")
    elif section == "stitch_rates":
        for key, val in request.form.items():
            if key.startswith("stitch_rate_") and val.strip():
                set_setting(key, val)
        from database import invalidate_settings_cache; invalidate_settings_cache()
        flash("Stitching rates saved!", "success")
    elif section == "rate_image":
        import base64
        img = request.files.get("rate_list_image")
        if img and img.filename:
            data = img.read()
            ext = img.filename.rsplit(".",1)[-1].lower()
            b64 = base64.b64encode(data).decode()
            set_setting("rate_list_image", f"data:image/{ext};base64,{b64}")
            flash("Rate list image uploaded!", "success")
    elif section == "add_employee":
        name  = request.form.get("emp_name","").strip()
        phone = request.form.get("emp_phone","").strip()
        if name:
            conn2 = get_db()
            try:
                conn2.execute("INSERT INTO employees(name,phone) VALUES(?,?)", (name, phone))
                conn2.commit()
                flash(f"Employee '{name}' added!", "success")
            except:
                flash("Employee name already exists", "warning")
            conn2.close()
    elif section == "remove_employee":
        emp_id = request.form.get("emp_id","")
        if emp_id:
            conn2 = get_db()
            conn2.execute("UPDATE employees SET active=0 WHERE id=?", (emp_id,))
            conn2.commit(); conn2.close()
            flash("Employee removed.", "success")
    elif section == "rates":
        for name in request.form.getlist("delete_rate"):
            conn2 = get_db()
            conn2.execute("DELETE FROM settings WHERE key=?",("rate_"+name,))
            conn2.commit(); conn2.close()
        for key, val in request.form.items():
            if key.startswith("rate_") and val.strip():
                set_setting(key, val)
        from database import invalidate_settings_cache; invalidate_settings_cache()
        flash("Rates saved!", "success")
    return redirect(url_for("owner.settings"))

@bp.route("/api/owner/earnings-7days")
@owner_required
def earnings_7days():
    conn = get_db()
    labels, income_data, expense_data = [], [], []
    for i in range(6,-1,-1):
        d = (date.today() - timedelta(days=i)).isoformat()
        labels.append(d[5:])
        rows = conn.execute("SELECT tx_type, SUM(amount) as total FROM finance WHERE tx_date=? GROUP BY tx_type",(d,)).fetchall()
        fin = {r["tx_type"]: r["total"] or 0 for r in rows}
        income_data.append(fin.get("income",0))
        expense_data.append(fin.get("expense",0))
    conn.close()
    return jsonify({"labels":labels,"income":income_data,"expense":expense_data})

@bp.route("/api/settings/logo")
def api_logo():
    return jsonify({"value": get_setting("shop_logo","")})

@bp.route("/api/settings/shop_name")
def api_shop_name():
    try:
        return jsonify({"value": get_setting("shop_name","Uttam Tailors")})
    except:
        return jsonify({"value": "Uttam Tailors"})

@bp.route("/measurement-fields")
@owner_required
def measurement_fields():
    conn = get_db()
    today = date.today().isoformat()
    urgent_count = conn.execute("SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered' AND delivery_date>=?",(today,)).fetchone()["c"]
    # Get all garment types
    garment_types = [
        "Shirt","Shirt Linen","Pant","Pant Double","Jeans","Suit 2pc","Suit 3pc",
        "Blazer","Kurta","Kurta Pajama","Pajama","Pathani","Safari","Waistcoat",
        "Alteration","Cutting Only"
    ]
    # Also get any custom ones from DB
    extra = conn.execute("SELECT DISTINCT garment_type FROM measurement_fields WHERE garment_type NOT IN ({})".format(
        ",".join("?"*len(garment_types))), garment_types).fetchall()
    garment_types += [r["garment_type"] for r in extra]

    fields_by_garment = {}
    rows = conn.execute("SELECT garment_type,field_name,id FROM measurement_fields ORDER BY sort_order ASC,id ASC").fetchall()
    for r in rows:
        fields_by_garment.setdefault(r["garment_type"],[]).append({"id":r["id"],"name":r["field_name"]})
    conn.close()
    return render_template("owner/measurement_fields.html",
        active_page="settings", show_voice=False, urgent_count=urgent_count,
        garment_types=garment_types, fields_by_garment=fields_by_garment)

@bp.route("/measurement-fields/add", methods=["POST"])
@owner_required
def add_measurement_field():
    garment = request.form.get("garment_type","").strip()
    field   = request.form.get("field_name","").strip()
    if garment and field:
        conn = get_db()
        conn.execute("INSERT INTO measurement_fields (garment_type,field_name,sort_order) VALUES (?,?,99) ON CONFLICT DO NOTHING",(garment,field))
        conn.commit(); conn.close()
        flash(f"Field added to {garment}!", "success")
    return redirect(url_for("owner.measurement_fields"))

@bp.route("/measurement-fields/delete/<int:fid>")
@owner_required
def delete_measurement_field(fid):
    conn = get_db()
    conn.execute("DELETE FROM measurement_fields WHERE id=?",(fid,))
    conn.commit(); conn.close()
    flash("Field removed.", "success")
    return redirect(url_for("owner.measurement_fields"))


# ══════════════════════════════════════════════
#  EXCEL EXPORT & IMPORT
# ══════════════════════════════════════════════

@bp.route("/export/orders")
@owner_required
def export_orders():
    """Export all orders with every field to Excel."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from io import BytesIO
    import json as _json

    conn = get_db()
    orders = conn.execute("""
        SELECT o.*, c.name as cname, c.mobile, c.address
        FROM orders o LEFT JOIN customers c ON c.id=o.customer_id
        ORDER BY o.id DESC
    """).fetchall()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Orders"

    # Header style
    hdr_fill = PatternFill("solid", fgColor="6366F1")
    hdr_font = Font(bold=True, color="FFFFFF", size=11)

    headers = [
        "Order Code", "Customer Name", "Mobile", "Address",
        "Order Date", "Delivery Date", "Status", "Is Urgent",
        "Garments", "Measurements",
        "Total Amount", "Extra Charges", "Payable Amount",
        "Advance Paid", "Remaining Due", "Payment Mode",
        "Repeat Of", "Note", "Delivered At", "Created At"
    ]

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = hdr_font
        cell.fill = hdr_fill
        cell.alignment = Alignment(horizontal="center")

    ws.freeze_panes = "A2"

    def fmtd(d):
        if not d: return ""
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    for row_idx, o in enumerate(orders, 2):
        items = conn.execute(
            "SELECT garment_type, quantity, rate, amount, measurements FROM order_items WHERE order_id=?",
            (o["id"],)
        ).fetchall()

        garments_str = "; ".join(f"{i['garment_type']} x{i['quantity']} @₹{int(i['rate'])}" for i in items)
        meas_parts = []
        for it in items:
            try:
                m = _json.loads(it["measurements"] or "{}")
                if m:
                    meas_parts.append(f"{it['garment_type']}: " + ", ".join(f"{k}={v}" for k,v in m.items()))
            except: pass
        meas_str = "; ".join(meas_parts)

        delivered_at = ""
        try: delivered_at = fmtd((o["delivered_at"] or "")[:10])
        except: pass

        row = [
            o["order_code"], o["cname"] or "", o["mobile"] or "", o["address"] or "",
            fmtd(o["order_date"]), fmtd(o["delivery_date"]),
            o["status"], "Yes" if o["is_urgent"] else "No",
            garments_str, meas_str,
            o["total_amount"] or 0, o["extra_charges"] or 0, o["payable_amount"] or 0,
            o["advance_paid"] or 0, o["remaining"] or 0, o["payment_mode"] or "",
            o["repeat_of"] or "", o["note"] or "", delivered_at,
            (o["created_at"] or "")[:16]
        ]
        for col, val in enumerate(row, 1):
            ws.cell(row=row_idx, column=col, value=val)
        # Highlight urgent in red
        if o["is_urgent"]:
            for col in range(1, len(headers)+1):
                ws.cell(row=row_idx, column=col).fill = PatternFill("solid", fgColor="FEE2E2")

    # Auto column widths
    for col in ws.columns:
        max_len = max((len(str(cell.value or "")) for cell in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 3, 40)

    conn.close()
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    from flask import send_file
    from datetime import datetime as _dt
    fname = f"uttam_tailors_orders_{_dt.now().strftime('%d-%m-%Y')}.xlsx"
    return send_file(buf, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     as_attachment=True, download_name=fname)


@bp.route("/import/customers", methods=["POST"])
@owner_required
def import_customers():
    """Import customers from Excel sheet."""
    import openpyxl
    from io import BytesIO
    f = request.files.get("customer_file")
    if not f:
        flash("No file selected", "warning")
        return redirect(url_for("owner.settings"))

    try:
        wb = openpyxl.load_workbook(BytesIO(f.read()))
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            flash("File is empty", "warning")
            return redirect(url_for("owner.settings"))

        # Try to detect header row
        header = [str(c or "").lower().strip() for c in rows[0]]
        name_col   = next((i for i,h in enumerate(header) if "name" in h), None)
        mobile_col = next((i for i,h in enumerate(header) if "mobile" in h or "phone" in h), None)
        addr_col   = next((i for i,h in enumerate(header) if "address" in h or "addr" in h), None)

        if name_col is None:
            flash("Could not find 'Name' column in Excel file", "error")
            return redirect(url_for("owner.settings"))

        conn = get_db()
        added = skipped = 0
        from datetime import datetime as _dt
        now = _dt.now().strftime("%Y-%m-%d %H:%M:%S")

        for row in rows[1:]:
            name   = str(row[name_col] or "").strip() if name_col is not None else ""
            mobile = str(row[mobile_col] or "").strip() if mobile_col is not None else ""
            addr   = str(row[addr_col] or "").strip() if addr_col is not None else ""
            if not name:
                continue
            existing = conn.execute("SELECT id FROM customers WHERE name=? AND mobile=?", (name, mobile)).fetchone()
            if existing:
                skipped += 1
            else:
                conn.execute("INSERT INTO customers(name,mobile,address,created_at) VALUES(?,?,?,?)",
                             (name, mobile, addr, now))
                added += 1

        conn.commit(); conn.close()
        flash(f"Import complete: {added} customers added, {skipped} already existed.", "success")
    except Exception as e:
        flash(f"Import error: {str(e)}", "error")

    return redirect(url_for("owner.settings"))


# ══════════════════════════════════════════════
#  INVENTORY MODULE
# ══════════════════════════════════════════════

@bp.route("/inventory")
@owner_required
def inventory():
    conn = get_db()
    today = date.today().isoformat()
    items = conn.execute("SELECT * FROM inventory ORDER BY item_name").fetchall()
    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]
    conn.close()
    return render_template("owner/inventory.html",
        active_page="inventory", show_voice=False,
        urgent_count=urgent_count, items=items)


@bp.route("/inventory/save", methods=["POST"])
@owner_required
def inventory_save():
    name      = request.form.get("item_name","").strip()
    quantity  = int(request.form.get("quantity",0) or 0)
    unit      = request.form.get("unit","").strip()
    threshold = int(request.form.get("low_threshold",0) or 0)
    if name:
        conn = get_db()
        # Upsert
        existing = conn.execute("SELECT id FROM inventory WHERE item_name=?", (name,)).fetchone()
        if existing:
            conn.execute("UPDATE inventory SET quantity=?, unit=?, low_threshold=? WHERE item_name=?",
                        (quantity, unit, threshold, name))
        else:
            conn.execute("INSERT INTO inventory(item_name,quantity,unit,low_threshold) VALUES(?,?,?,?)",
                        (name, quantity, unit, threshold))
        conn.commit(); conn.close()
        flash(f"'{name}' saved!", "success")
    return redirect(url_for("owner.inventory"))


@bp.route("/inventory/delete/<int:item_id>", methods=["POST"])
@owner_required
def inventory_delete(item_id):
    conn = get_db()
    conn.execute("DELETE FROM inventory WHERE id=?", (item_id,))
    conn.commit(); conn.close()
    flash("Item deleted", "success")
    return redirect(url_for("owner.inventory"))


# ══════════════════════════════════════════════
#  OWNER CUSTOMERS MODULE
# ══════════════════════════════════════════════

@bp.route("/customers")
@owner_required
def owner_customers():
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT c.id, c.name, COALESCE(c.mobile,'') as mobile,
                   COALESCE(c.address,'') as address,
                   COUNT(o.id) as order_count,
                   COALESCE(SUM(o.payable_amount),0) as total_billed,
                   COALESCE(SUM(o.remaining),0) as total_due,
                   MAX(o.order_date) as last_order_date
            FROM customers c LEFT JOIN orders o ON o.customer_id=c.id
            GROUP BY c.id, c.name, c.mobile, c.address ORDER BY c.id DESC
        """).fetchall()
    except Exception as e:
        conn.close()
        return f"<h2>DB Error in /owner/customers</h2><pre>{e}</pre>", 500

    def fmtd(d):
        if not d: return "—"
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    # Get all order codes per customer in one query
    all_codes = conn.execute(
        "SELECT customer_id, order_code FROM orders ORDER BY id DESC"
    ).fetchall()
    codes_by_cust = {}
    for row in all_codes:
        codes_by_cust.setdefault(row["customer_id"], []).append(row["order_code"])

    customers = [{
        "id":             r["id"],
        "name":           r["name"],
        "mobile":         r["mobile"] or "",
        "address":        r["address"] or "",
        "order_count":    r["order_count"],
        "total_billed":   r["total_billed"] or 0,
        "total_due":      r["total_due"] or 0,
        "last_order_date":fmtd(r["last_order_date"]),
        "order_codes":    " ".join(codes_by_cust.get(r["id"], []))
    } for r in rows]
    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]
    conn.close()

    return render_template_string(CUSTOMERS_PAGE,
        active_page="customers", show_voice=False,
        urgent_count=urgent_count, customers=customers, total=len(customers))


# ══════════════════════════════════════════════
#  OWNER FINANCE MODULE
# ══════════════════════════════════════════════

@bp.route("/finance")
@owner_required
def owner_finance():
    today = date.today().isoformat()
    # Support ?filter=today or ?filter=month from dashboard cards
    filt = request.args.get("filter", "")
    if filt == "today":
        from_date = request.args.get("date", today)
        to_date   = from_date
    elif filt == "month":
        from_date = today[:7] + "-01"
        to_date   = today
    else:
        from_date = request.args.get("from", today[:7]+"-01")
        to_date   = request.args.get("to",   today)

    conn = get_db()
    rows = conn.execute("""
        SELECT f.*, o.order_code
        FROM finance f LEFT JOIN orders o ON o.id=f.order_id
        WHERE f.tx_date >= ? AND f.tx_date <= ?
        ORDER BY f.tx_date DESC, f.id DESC
    """, (from_date, to_date)).fetchall()

    stats_r = conn.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN tx_type='income' THEN amount ELSE 0 END),0) as income,
            COALESCE(SUM(CASE WHEN tx_type='income' AND mode='cash' THEN amount ELSE 0 END),0) as cash_i,
            COALESCE(SUM(CASE WHEN tx_type='income' AND mode='upi' THEN amount ELSE 0 END),0) as upi_i,
            COALESCE(SUM(CASE WHEN tx_type='expense' THEN amount ELSE 0 END),0) as expense,
            COUNT(CASE WHEN tx_type='expense' THEN 1 END) as exp_count
        FROM finance WHERE tx_date >= ? AND tx_date <= ?
    """, (from_date, to_date)).fetchone()

    pending_due = conn.execute(
        "SELECT COALESCE(SUM(remaining),0) as d FROM orders WHERE status!='delivered'"
    ).fetchone()["d"]
    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]
    conn.close()

    def fmtd(d):
        if not d: return "—"
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    transactions = [{
        "tx_date":     r["tx_date"],
        "tx_date_fmt": fmtd(r["tx_date"]),
        "tx_time":     (r["created_at"] or "")[11:16],
        "tx_type":     r["tx_type"],
        "category":    r["category"] or "",
        "note":        r["note"] or "",
        "mode":        r["mode"] or "",
        "amount":      r["amount"] or 0,
        "order_code":  r["order_code"] or "",
        "created_by":  r["created_by"] or ""
    } for r in rows]

    net = int((stats_r["income"] or 0) - (stats_r["expense"] or 0))
    return render_template("owner/finance.html",
        active_page="finance", show_voice=False,
        urgent_count=urgent_count,
        from_date=from_date, to_date=to_date,
        stats={
            "total_income":  int(stats_r["income"] or 0),
            "cash_income":   int(stats_r["cash_i"] or 0),
            "upi_income":    int(stats_r["upi_i"] or 0),
            "total_expense": int(stats_r["expense"] or 0),
            "expense_count": int(stats_r["exp_count"] or 0),
            "net":           net,
            "pending_due":   int(pending_due or 0)
        },
        transactions=transactions
    )


# ══════════════════════════════════════════════
#  WHATSAPP BROADCAST
# ══════════════════════════════════════════════

@bp.route("/whatsapp")
@owner_required
def whatsapp():
    conn = get_db()
    # Load all customers with due amounts and ready order flags
    rows = conn.execute("""
        SELECT c.id, c.name, c.mobile,
               COALESCE(SUM(o.remaining),0) as due,
               MAX(CASE WHEN o.status='ready' THEN 1 ELSE 0 END) as has_ready
        FROM customers c
        LEFT JOIN orders o ON o.customer_id=c.id AND o.status!='delivered'
        WHERE c.mobile IS NOT NULL AND c.mobile != ''
        GROUP BY c.id, c.name, c.mobile, c.address ORDER BY c.name
    """).fetchall()

    customers = [{"id":r["id"],"name":r["name"],"mobile":r["mobile"] or "",
                  "due":r["due"] or 0,"has_ready":r["has_ready"] or 0}
                 for r in rows]

    # Recent broadcast log
    logs_raw = conn.execute("""
        SELECT message_type, COUNT(*) as count, MAX(sent_at) as sent_at
        FROM whatsapp_log GROUP BY message_type ORDER BY MAX(sent_at) DESC LIMIT 10
    """).fetchall()

    def fmtd(d):
        if not d: return "—"
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    broadcast_log = [{"message_type":r["message_type"],"count":r["count"],
                      "sent_at_fmt":fmtd((r["sent_at"] or "")[:10])} for r in logs_raw]

    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]
    shop_name = get_setting("shop_name","Uttam Tailors")
    conn.close()

    # Template definitions (names only for Jinja, messages in JS)
    # Load saved custom order confirmation message templates from settings
    order_confirm_tpl_en = get_setting("wa_order_confirm_en",
        "*{shop}* - Order Confirmed\n\nHello {name}!\n\n---\nOrder No: *#{code}*\nCustomer: {name}\nMobile: {mobile}\nOrder Date: {order_date}\nDelivery Date: *{delivery_date}*\n\nGarments: {items}\n---\nTotal: Rs. {total}\nAdvance Paid: Rs. {advance}\nRemaining Due: Rs. {remaining}\nMode: {mode}\n\nThank you for choosing {shop}!")
    order_confirm_tpl_hi = get_setting("wa_order_confirm_hi",
        "*{shop}* - ऑर्डर पक्का हो गया\n\nनमस्ते {name} जी!\n\n---\nऑर्डर नंबर: *#{code}*\nग्राहक: {name}\nमोबाइल: {mobile}\nऑर्डर दिनांक: {order_date}\nडिलीवरी दिनांक: *{delivery_date}*\n\nकपड़े: {items}\n---\nकुल राशि: Rs. {total}\nअग्रिम: Rs. {advance}\nबकाया: Rs. {remaining}\nभुगतान: {mode}\n\n{shop} में आने का धन्यवाद!")

    templates = [
        {"name":"Order Ready",      "icon":"🟢"},
        {"name":"Payment Due",      "icon":"💰"},
        {"name":"Festival Wishes",  "icon":"🎉"},
        {"name":"Eid Mubarak",      "icon":"🌙"},
        {"name":"New Collection",   "icon":"✨"},
        {"name":"Shop Closed",      "icon":"🚪"},
        {"name":"General Reminder", "icon":"📢"},
        {"name":"Diwali Wishes",    "icon":"🪔"},
    ]

    return render_template("owner/whatsapp.html",
        active_page="whatsapp", show_voice=False,
        urgent_count=urgent_count,
        customers=customers,
        customers_json=json.dumps(customers),
        shop_name=shop_name,
        templates=templates,
        broadcast_log=broadcast_log,
        order_confirm_tpl_en=order_confirm_tpl_en,
        order_confirm_tpl_hi=order_confirm_tpl_hi,
    )


@bp.route("/api/whatsapp-log", methods=["POST"])
@owner_required
def whatsapp_log():
    data  = request.get_json(silent=True) or {}
    count = data.get("count", 1)
    btype = data.get("type", "broadcast")
    now   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn  = get_db()
    # Log one entry per send session
    conn.execute(
        "INSERT INTO whatsapp_log(order_id,mobile,message_type,sent_at) VALUES(?,?,?,?)",
        (None, f"bulk:{count}", btype, now)
    )
    conn.commit(); conn.close()
    return jsonify({"ok":True})


# ══════════════════════════════════════════════
#  FINANCE CATEGORIES MANAGEMENT
# ══════════════════════════════════════════════

@bp.route("/api/finance-categories", methods=["GET"])
@owner_required
def get_finance_categories():
    income_cats  = get_setting("finance_income_cats",  "advance,payment,alteration,other income").split(",")
    expense_cats = get_setting("finance_expense_cats", "thread,buttons,fabric,electricity,rent,salary,transport,maintenance,other expense").split(",")
    return jsonify({
        "income":  [c.strip() for c in income_cats  if c.strip()],
        "expense": [c.strip() for c in expense_cats if c.strip()]
    })

@bp.route("/api/finance-categories/save", methods=["POST"])
@owner_required
def save_finance_categories():
    data    = request.get_json(silent=True) or {}
    cat_type = data.get("type","")   # "income" or "expense"
    cats    = data.get("categories", [])
    if cat_type not in ("income","expense"):
        return jsonify({"ok":False,"error":"Invalid type"})
    key = f"finance_{cat_type}_cats"
    set_setting(key, ",".join([c.strip() for c in cats if c.strip()]))
    return jsonify({"ok":True})


# ══════════════════════════════════════════════
#  WORK PROGRESS OVERVIEW (Admin)
# ══════════════════════════════════════════════

@bp.route("/work-progress")
@owner_required
def work_progress():
    conn = get_db()
    orders = conn.execute("""
        SELECT o.order_code, o.status, o.delivery_date, o.is_urgent,
               COALESCE(c.name,'—') as cname, COALESCE(c.mobile,'') as mobile,
               GROUP_CONCAT(oi.garment_type||' x'||oi.quantity, ', ') as garments_str,
               SUM(oi.quantity) as total_qty
        FROM orders o
        LEFT JOIN customers c ON c.id=o.customer_id
        LEFT JOIN order_items oi ON oi.order_id=o.id
        WHERE o.status NOT IN ('delivered','cancelled')
        GROUP BY o.id, o.order_code, o.status, o.delivery_date, o.is_urgent, c.name, c.mobile
        ORDER BY o.delivery_date ASC, o.is_urgent DESC
    """).fetchall()

    def fmtd(d):
        if not d: return "—"
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    result = []
    for o in orders:
        wl_rows = conn.execute(
            "SELECT garment_type, qty_done, notes FROM work_logs WHERE order_code=?",
            (o["order_code"],)
        ).fetchall()
        naap_done = kataai_done = silai_done = 0
        for wl in wl_rows:
            n = (wl["notes"] or "").strip()
            q = wl["qty_done"] or 0
            if any(x in n for x in ["Measurement","Naap"]):
                naap_done += q
            elif any(x in n for x in ["Kataai","Cutting"]):
                kataai_done += q
            else:
                silai_done += q
        tq = o["total_qty"] or 1
        result.append({
            "order_code":    o["order_code"],
            "status":        o["status"],
            "cname":         o["cname"],
            "mobile":        o["mobile"],
            "delivery_date": fmtd(o["delivery_date"]),
            "is_urgent":     o["is_urgent"],
            "garments":      o["garments_str"] or "—",
            "total_qty":     tq,
            "naap_done":     min(naap_done, tq),
            "cut_done":      min(kataai_done, tq),
            "stitch_done":   min(silai_done, tq),
            "naap_pct":      min(100, int((min(naap_done,tq)/tq)*100)),
            "cut_pct":       min(100, int((min(kataai_done,tq)/tq)*100)),
            "stitch_pct":    min(100, int((min(silai_done,tq)/tq)*100)),
        })

    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]
    conn.close()
    return render_template_string(WORK_PROGRESS_PAGE,
        active_page="work_progress", show_voice=False,
        urgent_count=urgent_count, orders=result, total=len(result))



# ══════════════════════════════════════════════
#  DESIGN GALLERY (Admin)
# ══════════════════════════════════════════════

@bp.route("/gallery")
@owner_required
def gallery_admin():
    conn = get_db()
    # Tables already created by init_db
    try:
        types = conn.execute("SELECT * FROM gallery_types ORDER BY parent_id NULLS FIRST, sort_order, id").fetchall()
        images = conn.execute("SELECT * FROM gallery_images ORDER BY type_id, sort_order, id").fetchall()
    except Exception:
        types = []
        images = []
    urgent_count = conn.execute("SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'").fetchone()["c"]
    conn.close()
    return render_template("owner/gallery_admin.html",
        active_page="gallery_admin", show_voice=False,
        urgent_count=urgent_count, types=types, images=images)

@bp.route("/gallery/add-type", methods=["POST"])
@owner_required
def gallery_add_type():
    name      = request.form.get("name","").strip()
    parent_id = request.form.get("parent_id","").strip() or None
    if name:
        conn = get_db()
        conn.execute("INSERT INTO gallery_types(name,parent_id) VALUES(?,?)", (name, parent_id))
        conn.commit(); conn.close()
        flash(f"Type '{name}' added.", "success")
    return redirect(url_for("owner.gallery_admin"))

@bp.route("/gallery/delete-type/<int:tid>", methods=["POST"])
@owner_required
def gallery_delete_type(tid):
    conn = get_db()
    conn.execute("DELETE FROM gallery_images WHERE type_id=?", (tid,))
    conn.execute("DELETE FROM gallery_types WHERE id=?", (tid,))
    conn.execute("DELETE FROM gallery_types WHERE parent_id=?", (tid,))
    conn.commit(); conn.close()
    flash("Type deleted.", "success")
    return redirect(url_for("owner.gallery_admin"))

@bp.route("/gallery/upload-image", methods=["POST"])
@owner_required
def gallery_upload_image():
    import os as _os, time as _time
    try:
        type_id = request.form.get("type_id","").strip()
        caption = request.form.get("caption","").strip()
        file    = request.files.get("image")
        if not type_id or not file or not file.filename:
            flash("Please select a category and image.", "error")
            return redirect(url_for("owner.gallery_admin"))

        use_cloudinary = False
        if use_cloudinary:
            import cloudinary, cloudinary.uploader
            cloudinary.config(
                cloud_name=_os.environ.get("CLOUDINARY_CLOUD_NAME"),
                api_key=_os.environ.get("CLOUDINARY_API_KEY"),
                api_secret=_os.environ.get("CLOUDINARY_API_SECRET")
            )
            result = cloudinary.uploader.upload(
                file,
                folder="uttam_tailors/gallery",
                public_id=f"gal_{type_id}_{int(_time.time())}",
                overwrite=True
            )
            fname = result.get("secure_url","")
        else:
            ext = _os.path.splitext(file.filename)[1].lower()
            if ext not in [".jpg",".jpeg",".png",".gif",".webp"]: ext = ".jpg"
            folder = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(__file__))), "static", "order_images", "gallery")
            _os.makedirs(folder, exist_ok=True)
            fname = f"gal_{type_id}_{int(_time.time())}{ext}"
            _gp = _os.path.join(folder, fname); file.save(_gp)
            from app.utils.image_optimize import optimize_image as _oi; _gp = _oi(_gp); fname = _os.path.basename(_gp)

        conn = get_db()
        conn.execute("INSERT INTO gallery_images(type_id,filename,caption) VALUES(?,?,?)", (type_id, fname, caption))
        conn.commit(); conn.close()
        flash("Image uploaded successfully.", "success")
    except Exception as e:
        flash(f"Upload failed: {str(e)}", "error")
    return redirect(url_for("owner.gallery_admin"))

@bp.route("/gallery/delete-image/<int:iid>", methods=["POST"])
@owner_required
def gallery_delete_image(iid):
    import os as _os
    conn = get_db()
    img = conn.execute("SELECT filename FROM gallery_images WHERE id=?", (iid,)).fetchone()
    if img:
        fpath = _os.path.join(Config.UPLOAD_FOLDER, "gallery", img["filename"])
        if _os.path.exists(fpath):
            _os.remove(fpath)
        conn.execute("DELETE FROM gallery_images WHERE id=?", (iid,))
        conn.commit()
    conn.close()
    flash("Image deleted.", "success")
    return redirect(url_for("owner.gallery_admin"))

@bp.route("/api/gallery")
def api_gallery():
    """Public API for employee gallery page"""
    conn = get_db()
    try:
        types  = conn.execute("SELECT * FROM gallery_types ORDER BY parent_id NULLS FIRST, sort_order, id").fetchall()
        images = conn.execute("SELECT * FROM gallery_images ORDER BY type_id, sort_order, id").fetchall()
    except:
        conn.close()
        return jsonify({"types":[], "images":[]})
    conn.close()
    return jsonify({
        "types":  [{"id":t["id"],"name":t["name"],"parent_id":t["parent_id"]} for t in types],
        "images": [{"id":i["id"],"type_id":i["type_id"],"filename":i["filename"],"caption":i["caption"]} for i in images]
    })



# ══════════════════════════════════════════════
#  CLEANUP OLD BASE64 DATA (one-time fix)
# ══════════════════════════════════════════════

@bp.route("/cleanup-images", methods=["POST"])
@owner_required
def cleanup_images():
    """Remove old base64 image data from database - run once to fix slowness"""
    conn = get_db()
    try:
        # Delete rows where file_path starts with data: (base64) or temp:
        conn.execute("DELETE FROM order_images WHERE file_path LIKE 'data:%'")
        conn.execute("DELETE FROM order_images WHERE file_path LIKE 'temp:%'")
        conn.commit()
        deleted = conn.execute("SELECT changes() as c").fetchone()
        conn.close()
        flash("✅ Old image data cleaned up. System should be faster now.", "success")
    except Exception as e:
        try: conn.close()
        except: pass
        flash(f"Cleanup done (some errors ignored).", "success")
    return redirect(url_for("owner.settings"))

# ══════════════════════════════════════════════
#  DATABASE BACKUP / RESTORE
# ══════════════════════════════════════════════

@bp.route("/backup/download")
@owner_required
def backup_download():
    """Download database backup - exports PostgreSQL data as JSON"""
    import json as _json, os as _os, tempfile
    from flask import send_file
    try:
        conn = get_db()
        backup_data = {}
        tables = ["customers","orders","order_items","order_images","work_logs",
                  "finance","employees","settings","salary_advances","gallery_types",
                  "gallery_images","measurement_fields","notify_log"]
        for table in tables:
            try:
                rows = conn.execute(f"SELECT * FROM {table}").fetchall()
                backup_data[table] = [dict(zip(r.keys(), r.values())) for r in rows]
            except Exception:
                backup_data[table] = []
        conn.close()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w")
        _json.dump(backup_data, tmp, default=str, ensure_ascii=False)
        tmp.close()
        from datetime import datetime
        fname = f"uttam_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        set_setting("last_backup_at", datetime.now().strftime("%Y-%m-%d %H:%M"))
        return send_file(tmp.name, as_attachment=True, download_name=fname, mimetype="application/json")
    except Exception as e:
        flash(f"Backup failed: {str(e)}", "error")
        return redirect(url_for("owner.settings"))

@bp.route("/backup/restore", methods=["POST"])
@owner_required
def backup_restore():
    """Restore database from uploaded JSON backup file."""
    import json as _json, os as _os
    try:
        file = request.files.get("db_file")
        if not file or not file.filename:
            flash("Please select a backup file.", "error")
            return redirect(url_for("owner.settings"))
        if not file.filename.endswith(".json"):
            flash("Invalid file. Must be a .json backup file.", "error")
            return redirect(url_for("owner.settings"))

        backup_data = _json.load(file)
        if not isinstance(backup_data, dict):
            flash("Invalid backup format.", "error")
            return redirect(url_for("owner.settings"))

        conn = get_db()
        tables = ["customers","orders","order_items","order_images","work_logs",
                  "finance","employees","settings","salary_advances","gallery_types",
                  "gallery_images","measurement_fields","notify_log"]
        for table in tables:
            rows = backup_data.get(table, [])
            if not rows:
                continue
            # Clear existing data
            try:
                conn.execute(f"DELETE FROM {table}")
            except Exception:
                continue
            # Insert rows
            for row in rows:
                cols = list(row.keys())
                placeholders = ", ".join(["?"] * len(cols))
                col_names = ", ".join(cols)
                vals = [row[c] for c in cols]
                try:
                    conn.execute(f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})", vals)
                except Exception:
                    continue
        conn.commit()
        conn.close()
        flash("✅ Database restored successfully! All your orders and data are back.", "success")
    except Exception as e:
        flash(f"Restore failed: {str(e)}", "error")
    return redirect(url_for("owner.settings"))

# ══════════════════════════════════════════════
#  FACTORY RESET
# ══════════════════════════════════════════════

@bp.route("/reset", methods=["POST"])
@owner_required
def factory_reset():
    password = request.form.get("reset_password","").strip()
    if password != "8899":
        flash("Incorrect reset password.", "error")
        return redirect(url_for("owner.settings"))
    try:
        conn = get_db()
        conn.execute("DELETE FROM work_logs")
        conn.execute("DELETE FROM order_items")
        conn.execute("DELETE FROM finance")
        conn.execute("DELETE FROM orders")
        conn.execute("DELETE FROM customers")
        conn.execute("DELETE FROM salary_advances")
        try:
            conn.execute("DELETE FROM notify_log")
        except: pass
        # Reset order code counter using same connection
        conn.execute("UPDATE settings SET value='3599' WHERE key='last_order_code'")
        conn.execute("INSERT INTO settings (key,value) VALUES ('last_order_code','3599') ON CONFLICT DO NOTHING")
        conn.commit()
        conn.close()
        flash("✅ System reset! All orders and customers cleared. Rates and settings kept.", "success")
    except Exception as e:
        flash(f"Reset failed: {str(e)}", "error")
    return redirect(url_for("owner.settings"))




# ══════════════════════════════════════════════
#  API: ORDER DETAIL (for expandable row)
# ══════════════════════════════════════════════

@bp.route("/api/order-detail/<order_code>")
@owner_required
def api_order_detail(order_code):
    import json as _json, os as _os
    from config import Config
    conn = get_db()
    o = conn.execute("""
        SELECT o.*, c.name as cname, c.mobile, c.address
        FROM orders o LEFT JOIN customers c ON c.id=o.customer_id
        WHERE o.order_code=?
    """, (order_code,)).fetchone()
    if not o:
        conn.close()
        return jsonify({"error": "Not found"})

    items = conn.execute("SELECT * FROM order_items WHERE order_id=?", (o["id"],)).fetchall()
    wl_rows = conn.execute("SELECT qty_done, notes FROM work_logs WHERE order_code=?", (order_code,)).fetchall()

    # Progress
    naap=kataai=silai=0
    for wl in wl_rows:
        n=(wl["notes"] or "").strip(); q=wl["qty_done"] or 0
        if any(x in n for x in ["Measurement","Naap"]): naap+=q
        elif any(x in n for x in ["Kataai","Cutting"]): kataai+=q
        else: silai+=q
    tq=sum(it["quantity"] for it in items) or 1

    garments=[]
    for it in items:
        try: meas=_json.loads(it["measurements"] or "{}")
        except: meas={}
        garments.append({"type":it["garment_type"],"qty":it["quantity"],"rate":it["rate"],"amount":it["amount"],"measurements":meas,"notes":it["notes"] or ""})

    # Images - DB first (Cloudinary), then filesystem fallback
    images=[]
    img_rows=conn.execute("SELECT file_path FROM order_images WHERE order_id=? ORDER BY id",(o["id"],)).fetchall()
    images=[r["file_path"] for r in img_rows if r["file_path"] and not r["file_path"].startswith("temp:")]
    conn.close()

    if not images:
        folder=_os.path.join(Config.UPLOAD_FOLDER, order_code)
        if _os.path.isdir(folder):
            images=[f"/static/order_images/{order_code}/{f}" for f in sorted(_os.listdir(folder)) if f.lower().endswith((".jpg",".jpeg",".png",".gif",".webp"))]

    return jsonify({
        "order": {
            "order_code": o["order_code"], "status": o["status"],
            "cname": o["cname"] or "—", "mobile": o["mobile"] or "—", "address": o["address"] or "—",
            "payable": o["payable_amount"] or 0, "advance": o["advance_paid"] or 0, "remaining": o["remaining"] or 0,
            "naap_pct": min(100,int(naap/tq*100)), "cut_pct": min(100,int(kataai/tq*100)), "stitch_pct": min(100,int(silai/tq*100)),
        },
        "garments": garments,
        "images": images
    })

# ══════════════════════════════════════════════
#  ADMIN ORDER DETAIL PAGE
# ══════════════════════════════════════════════

@bp.route("/orders/detail/<order_code>")
@owner_required
def order_detail(order_code):
    conn = get_db()
    import json as _json, os as _os
    from config import Config

    o = conn.execute("""
        SELECT o.*, c.name as cname, c.mobile, c.address,
               COALESCE(o.note,'') as note
        FROM orders o
        LEFT JOIN customers c ON c.id=o.customer_id
        WHERE o.order_code=?
    """, (order_code,)).fetchone()

    if not o:
        conn.close()
        return "<h2>Order not found</h2>", 404

    items = conn.execute(
        "SELECT * FROM order_items WHERE order_id=?", (o["id"],)
    ).fetchall()

    wl_rows = conn.execute("""
        SELECT garment_type, qty_done, notes, employee_name, log_date, making_rate
        FROM work_logs WHERE order_code=? ORDER BY log_date, id
    """, (order_code,)).fetchall()

    finance = conn.execute("""
        SELECT tx_date, tx_type, category, amount, mode, note
        FROM finance WHERE order_id=? ORDER BY id
    """, (o["id"],)).fetchall()

    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]

    # Images - DB first (covers AI-generated style previews saved to order_images),
    # then filesystem fallback for older orders that only have uploaded photo files.
    img_rows = conn.execute(
        "SELECT file_path FROM order_images WHERE order_id=? ORDER BY id", (o["id"],)
    ).fetchall()
    images = [r["file_path"] for r in img_rows if r["file_path"] and not r["file_path"].startswith("temp:")]

    conn.close()

    # Work progress
    naap_done = kataai_done = silai_done = 0
    for wl in wl_rows:
        n = (wl["notes"] or "").strip()
        q = wl["qty_done"] or 0
        if any(x in n for x in ["Measurement","Naap","नाप"]):
            naap_done += q
        elif any(x in n for x in ["Kataai","Cutting","कटाई"]):
            kataai_done += q
        else:
            silai_done += q

    total_qty = sum(it["quantity"] for it in items) or 1

    def fmtd(d):
        if not d: return "—"
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    # Filesystem fallback for older orders that only have uploaded photo files
    # (the DB-backed `images` list was already populated above, before conn.close()).
    if not images:
        folder = _os.path.join(Config.UPLOAD_FOLDER, order_code)
        if _os.path.isdir(folder):
            images = [f"/static/order_images/{order_code}/{f}"
                      for f in sorted(_os.listdir(folder))
                      if f.lower().endswith((".jpg",".jpeg",".png",".gif",".webp"))]

    def _parse_style_notes(notes):
        """Turn the pipe-separated notes string the customer's order produces
        (e.g. "[WEB/SIZE] | Suit Shirt x2 | Size:M | Fabric needed ~3.0m (own fabric) |
        [Suit Shirt] Collar: Band Collar | Sleeves: Half Sleeve | ...") into a clean,
        structured layout the tailor can scan at a glance: a size/fabric summary line
        plus a labelled list of every style choice (Collar, Sleeves, Buttons, etc.)."""
        summary = []
        choices = []
        if not notes:
            return {"summary": summary, "choices": choices}
        for raw in notes.split("|"):
            part = raw.strip()
            if not part:
                continue
            # Skip bracket tags like [WEB/SIZE] / [Suit Shirt] — they're just section markers
            if part.startswith("[") and part.endswith("]"):
                continue
            # A bracket tag glued to a label, e.g. "[Suit Shirt] Collar: Band Collar"
            if part.startswith("["):
                close = part.find("]")
                if close != -1:
                    part = part[close+1:].strip()
            if not part:
                continue
            # Skip auto-generated meta lines that get their own dedicated display
            # elsewhere on the page (bill breakdown → Payment card, customer note →
            # its own box, urgent → status badge) so they don't clutter the style grid.
            low = part.lower()
            if low == "urgent" or low.startswith("bill:") or part.startswith("[NOTE]"):
                continue
            if ":" in part:
                label, _, value = part.partition(":")
                label = label.strip()
                value = value.strip()
                if label.lower() in ("size",) or label.lower().startswith("fabric"):
                    summary.append({"label": label, "value": value})
                else:
                    choices.append({"label": label, "value": value})
            else:
                # Plain segment like "Suit Shirt x2" — show as part of the summary
                summary.append({"label": "", "value": part})
        return {"summary": summary, "choices": choices}

    def _parse_bill_breakdown(bill_str):
        """Turn 'Stitching Rs.500 + Urgent Rs.99 + Home delivery Rs.49 = Rs.649'
        into structured rows + grand total for a clean line-item display."""
        rows = []
        grand = ""
        if not bill_str:
            return {"rows": rows, "total": grand}
        s = bill_str
        if "=" in s:
            s, _, grand = s.rpartition("=")
            grand = grand.strip()
        for seg in s.split("+"):
            seg = seg.strip()
            if not seg:
                continue
            # Split "Home delivery Rs.49" -> label "Home delivery", amount "Rs. 49"
            idx = seg.rfind("Rs.")
            if idx != -1:
                label = seg[:idx].strip()
                amount = seg[idx:].replace("Rs.", "Rs. ").strip()
                rows.append({"label": label, "amount": amount})
            else:
                rows.append({"label": seg, "amount": ""})
        return {"rows": rows, "total": grand}

    def _extract_note_highlights(notes):
        """Pull structured fields out of the raw pipe-separated order note.
        Handles: 'bill:', '[NOTE]', 'coupon:CODE(-Rs.X)', 'gift-for:Name'."""
        import re as _re
        bill          = ""
        customer_note = ""
        coupon_code   = ""
        coupon_amt    = 0
        gift_for      = ""
        if not notes:
            return {"bill": bill, "customer_note": customer_note,
                    "coupon_code": coupon_code, "coupon_amt": coupon_amt,
                    "gift_for": gift_for}
        for raw in notes.split("|"):
            part = raw.strip()
            if not part:
                continue
            pl = part.lower()
            if pl.startswith("bill:"):
                bill = part[len("bill:"):].strip()
            elif part.startswith("[NOTE]"):
                customer_note = part[len("[NOTE]"):].strip()
            elif pl.startswith("coupon:"):
                # format: "coupon:SAVE10(-Rs.150)"
                coupon_info = part[len("coupon:"):].strip()
                m = _re.match(r'([A-Z0-9_\-]+)\(-Rs\.(\d+)\)', coupon_info, _re.I)
                if m:
                    coupon_code = m.group(1)
                    coupon_amt  = int(m.group(2))
                else:
                    coupon_code = coupon_info
            elif pl.startswith("gift-for:"):
                gift_for = part[len("gift-for:"):].strip()
        return {"bill": bill, "customer_note": customer_note,
                "coupon_code": coupon_code, "coupon_amt": coupon_amt,
                "gift_for": gift_for}

    garments = []
    for it in items:
        try:
            meas = _json.loads(it["measurements"] or "{}")
        except:
            meas = {}
        garments.append({
            "type": it["garment_type"],
            "qty":  it["quantity"],
            "rate": it["rate"],
            "amount": it["amount"],
            "measurements": meas,
            "notes": it["notes"] or "",
            "style": _parse_style_notes(it["notes"] or "")
        })

    _note_hl = _extract_note_highlights(o["note"])
    _bill = _parse_bill_breakdown(_note_hl["bill"])

    order_data = {
        "order_code":    o["order_code"],
        "status":        o["status"],
        "is_urgent":     o["is_urgent"],
        "note":          o["note"],
        "bill_breakdown": _note_hl["bill"],
        "bill_rows":      _bill["rows"],
        "bill_total":     _bill["total"],
        "customer_note":  _note_hl["customer_note"],
        "coupon_code":    _note_hl["coupon_code"],
        "coupon_amt":     _note_hl["coupon_amt"],
        "gift_for":       _note_hl["gift_for"],
        "order_date":    fmtd(o["order_date"]),
        "delivery_date": fmtd(o["delivery_date"]),
        "delivered_at":  fmtd((o["delivered_at"] or "")[:10]),
        "cname":         o["cname"] or "—",
        "mobile":        o["mobile"] or "—",
        "address":       o["address"] or "—",
        "total_amount":  o["total_amount"] or 0,
        "extra_charges": o["extra_charges"] or 0,
        "payable":       o["payable_amount"] or 0,
        "advance":       o["advance_paid"] or 0,
        "remaining":     o["remaining"] or 0,
        "payment_mode":  o["payment_mode"] or "cash",
        "naap_pct":      min(100, int(naap_done/total_qty*100)),
        "cut_pct":       min(100, int(kataai_done/total_qty*100)),
        "stitch_pct":    min(100, int(silai_done/total_qty*100)),
        "total_qty":     total_qty,
    }

    return render_template("owner/order_detail.html",
        active_page="owner_orders", show_voice=False,
        urgent_count=urgent_count,
        order=order_data, garments=garments,
        work_logs=wl_rows, finance=finance, images=images,
        fmtd=fmtd)

# ══════════════════════════════════════════════
#  ORDER CANCEL
# ══════════════════════════════════════════════

@bp.route("/orders/cancel/<order_code>", methods=["POST"])
@owner_required
def cancel_order(order_code):
    conn = get_db()
    # Fetch before update for SMS/email/FCM
    ord_row = conn.execute(
        """SELECT o.note, o.web_account_id, c.mobile, c.name as cust_name,
                  COALESCE(c.email,'') as cust_email
           FROM orders o LEFT JOIN customers c ON c.id=o.customer_id
           WHERE o.order_code=?""", (order_code,)
    ).fetchone()
    conn.execute("UPDATE orders SET status='cancelled' WHERE order_code=?", (order_code,))
    conn.commit()
    conn.close()
    # SMS cancellation notice
    try:
        if ord_row and ord_row["mobile"]:
            from app.utils.sms import send_status_sms as _st_sms
            _st_sms(ord_row["mobile"], order_code, ord_row["cust_name"] or "Customer", "cancelled")
    except Exception:
        pass
    # Email + FCM cancellation notice
    try:
        if ord_row:
            _c_email = (ord_row["cust_email"] or "").strip()
            _c_acc   = ord_row["web_account_id"]
            if not _c_email and _c_acc:
                _cr = get_db().execute("SELECT email FROM web_accounts WHERE id=? LIMIT 1", (_c_acc,)).fetchone()
                if _cr: _c_email = (_cr["email"] or "").strip()
            _c_name = ord_row["cust_name"] or "Customer"
            if _c_email:
                from app.utils.email_notify import send_status_email as _cse
                _cse(_c_email, order_code, _c_name, "cancelled")
            if _c_acc:
                from app.utils.fcm import push_status_update as _cfcm
                _cfcm(_c_acc, order_code, "cancelled")
    except Exception:
        pass
    flash(f"Order #{order_code} cancelled.", "success")
    return redirect(request.referrer or url_for("owner.owner_dashboard"))


# ══════════════════════════════════════════════
#  WHATSAPP ORDER TEMPLATE SAVE
# ══════════════════════════════════════════════

@bp.route("/api/save-wa-template", methods=["POST"])
@owner_required
def save_wa_template():
    data = request.get_json(silent=True) or {}
    from database import set_setting
    if "en" in data:
        set_setting("wa_order_confirm_en", data["en"])
    if "hi" in data:
        set_setting("wa_order_confirm_hi", data["hi"])
    return jsonify({"ok": True})


# ══════════════════════════════════════════════
#  ORDER MANAGEMENT (Owner)
# ══════════════════════════════════════════════

@bp.route("/orders")
@owner_required
def owner_orders():
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT o.order_code, o.status, o.order_date, o.delivery_date,
                   COALESCE(o.payable_amount,0) as payable_amount,
                   COALESCE(o.remaining,0) as remaining,
                   COALESCE(o.is_urgent,0) as is_urgent,
                   COALESCE(o.note,'') as note,
                   COALESCE(o.repeat_of,'') as repeat_of,
                   COALESCE(c.name,'—') as cname, COALESCE(c.mobile,'') as mobile,
                   GROUP_CONCAT(oi.garment_type||' x'||oi.quantity, ', ') as garments_str
            FROM orders o
            LEFT JOIN customers c ON c.id=o.customer_id
            LEFT JOIN order_items oi ON oi.order_id=o.id
            GROUP BY o.id, o.order_code, o.status, o.order_date, o.delivery_date,
                     o.total_amount, o.extra_charges, o.payable_amount, o.advance_paid,
                     o.remaining, o.payment_mode, o.is_urgent, o.note, o.repeat_of,
                     o.delivered_at, o.created_at, c.name, c.mobile, c.address
            ORDER BY o.id DESC
        """).fetchall()
    except Exception as e:
        conn.close()
        return f"<h2>DB Error in /owner/orders</h2><pre>{e}</pre>", 500

    def fmtd(d):
        if not d: return "—"
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    orders = [{
        "order_code":    r["order_code"],
        "display_code":  r["repeat_of"] if r["repeat_of"] else r["order_code"],
        "entry_code":    r["order_code"] if r["repeat_of"] else "",
        "repeat_of":     r["repeat_of"] or "",
        "status":        r["status"],
        "order_date":    fmtd(r["order_date"]),
        "delivery_date": fmtd(r["delivery_date"]),
        "payable":       r["payable_amount"] or 0,
        "remaining":     r["remaining"] or 0,
        "is_urgent":     r["is_urgent"],
        "note":          r["note"] or "",
        "cname":         r["cname"] or "—",
        "mobile":        r["mobile"] or "",
        "garments":      r["garments_str"] or "—"
    } for r in rows]

    # Work progress data for combined page
    try:
        wp_rows = conn.execute("""
            SELECT o.order_code, o.status, o.delivery_date, o.is_urgent,
                   COALESCE(c.name,'—') as cname, COALESCE(c.mobile,'') as mobile,
                   GROUP_CONCAT(oi.garment_type||' x'||oi.quantity, ', ') as garments_str,
                   SUM(oi.quantity) as total_qty
            FROM orders o
            LEFT JOIN customers c ON c.id=o.customer_id
            LEFT JOIN order_items oi ON oi.order_id=o.id
            WHERE o.status NOT IN ('delivered','cancelled')
            GROUP BY o.id, o.order_code, o.status, o.delivery_date, o.is_urgent, c.name, c.mobile
            ORDER BY o.delivery_date ASC, o.is_urgent DESC
        """).fetchall()
    except:
        wp_rows = []

    wp_result = []
    for o in wp_rows:
        wl = conn.execute("SELECT qty_done, notes FROM work_logs WHERE order_code=?", (o["order_code"],)).fetchall()
        naap=kataai=silai=0
        for w in wl:
            n=(w["notes"] or "").strip(); q=w["qty_done"] or 0
            if any(x in n for x in ["Measurement","Naap"]): naap+=q
            elif any(x in n for x in ["Kataai","Cutting"]): kataai+=q
            else: silai+=q
        tq=o["total_qty"] or 1
        wp_result.append({
            "order_code": o["order_code"], "status": o["status"],
            "cname": o["cname"], "mobile": o["mobile"],
            "delivery_date": fmtd(o["delivery_date"]),
            "is_urgent": o["is_urgent"], "garments": o["garments_str"] or "—",
            "total_qty": tq,
            "naap_pct": min(100,int(min(naap,tq)/tq*100)),
            "cut_pct":  min(100,int(min(kataai,tq)/tq*100)),
            "stitch_pct": min(100,int(min(silai,tq)/tq*100)),
        })

    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]
    conn.close()

    filter_mode = request.args.get("filter", "")
    return render_template_string(ORDERS_PAGE,
        active_page="owner_orders", show_voice=False,
        urgent_count=urgent_count, orders=orders, total=len(orders),
        filter_mode=filter_mode, wp_orders=wp_result)

# ══════════════════════════════════════════════
#  ORDER DELETE (Owner)
# ══════════════════════════════════════════════

@bp.route("/orders/delete/<order_code>", methods=["POST"])
@owner_required
def delete_order(order_code):
    conn = get_db()
    order = conn.execute("SELECT id FROM orders WHERE order_code=?", (order_code,)).fetchone()
    if order:
        conn.execute("DELETE FROM work_logs WHERE order_id=?", (order["id"],))
        conn.execute("DELETE FROM work_logs WHERE order_code=?", (order_code,))
        conn.execute("DELETE FROM order_items WHERE order_id=?", (order["id"],))
        conn.execute("DELETE FROM order_images WHERE order_id=?", (order["id"],))
        conn.execute("DELETE FROM finance WHERE order_id=?", (order["id"],))
        conn.execute("DELETE FROM notify_log WHERE order_code=?", (order_code,))
        conn.execute("DELETE FROM orders WHERE id=?", (order["id"],))
        conn.commit()
        flash(f"Order #{order_code} and all related data deleted.", "success")
    else:
        flash(f"Order #{order_code} not found.", "error")
    conn.close()
    return redirect(request.referrer or url_for("owner.owner_dashboard"))


@bp.route("/customers/<int:customer_id>/delete", methods=["POST"])
@owner_required
def delete_customer(customer_id):
    """Delete a customer and ALL their orders, work logs, images, finance entries."""
    conn = get_db()
    cust = conn.execute("SELECT name FROM customers WHERE id=?", (customer_id,)).fetchone()
    if not cust:
        conn.close()
        flash("Customer not found.", "error")
        return redirect(url_for("owner.owner_dashboard"))

    cust_name = cust["name"]
    # Get all orders for this customer
    orders = conn.execute("SELECT id, order_code FROM orders WHERE customer_id=?", (customer_id,)).fetchall()
    for o in orders:
        conn.execute("DELETE FROM work_logs WHERE order_id=?", (o["id"],))
        conn.execute("DELETE FROM work_logs WHERE order_code=?", (o["order_code"],))
        conn.execute("DELETE FROM order_items WHERE order_id=?", (o["id"],))
        conn.execute("DELETE FROM order_images WHERE order_id=?", (o["id"],))
        conn.execute("DELETE FROM finance WHERE order_id=?", (o["id"],))
        conn.execute("DELETE FROM notify_log WHERE order_code=?", (o["order_code"],))
    conn.execute("DELETE FROM orders WHERE customer_id=?", (customer_id,))
    conn.execute("DELETE FROM customers WHERE id=?", (customer_id,))
    conn.commit()
    conn.close()
    flash(f"Customer '{cust_name}' and {len(orders)} order(s) deleted permanently.", "success")
    return redirect(url_for("owner.owner_customers"))


# ══════════════════════════════════════════════
#  CUSTOMER DETAIL (Owner)
# ══════════════════════════════════════════════

@bp.route("/customers/<int:customer_id>")
@owner_required
def owner_customer_detail(customer_id):
    conn = get_db()
    cust = conn.execute("SELECT * FROM customers WHERE id=?", (customer_id,)).fetchone()
    if not cust:
        conn.close()
        return "Customer not found", 404

    orders = conn.execute("""
        SELECT o.*, GROUP_CONCAT(oi.garment_type||' x'||oi.quantity, ', ') as garments_str
        FROM orders o LEFT JOIN order_items oi ON oi.order_id=o.id
        WHERE o.customer_id=? GROUP BY o.id, o.order_code, o.status, o.order_date,
                 o.delivery_date, o.payable_amount, o.advance_paid, o.remaining,
                 o.payment_mode, o.is_urgent, o.note, o.delivered_at
        ORDER BY o.id DESC
    """, (customer_id,)).fetchall()

    def fmtd(d):
        if not d: return "—"
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]
    conn.close()

    orders_list = [{
        "order_code":       o["order_code"],
        "status":           o["status"],
        "order_date_fmt":   fmtd(o["order_date"]),
        "delivery_date_fmt":fmtd(o["delivery_date"]),
        "payable_amount":   o["payable_amount"] or 0,
        "advance_paid":     o["advance_paid"] or 0,
        "remaining":        o["remaining"] or 0,
        "is_urgent":        o["is_urgent"],
        "note":             o["note"] or "",
        "garments_str":     o["garments_str"] or "",
    } for o in orders]

    total_billed = sum(o["payable_amount"] for o in orders_list)
    total_due    = sum(o["remaining"] for o in orders_list)

    return render_template("owner/customer_detail.html",
        active_page="customers", show_voice=False,
        urgent_count=urgent_count,
        cust={"id":cust["id"],"name":cust["name"],"mobile":cust["mobile"] or "",
              "address":cust["address"] or ""},
        orders=orders_list,
        total_billed=int(total_billed), total_due=int(total_due)
    )


# ══════════════════════════════════════════════
#  CUSTOMER EDIT (Owner)
# ══════════════════════════════════════════════

@bp.route("/customers/<int:customer_id>/edit", methods=["POST"])
@owner_required
def owner_customer_edit(customer_id):
    name    = request.form.get("name","").strip()
    mobile  = request.form.get("mobile","").strip()
    address = request.form.get("address","").strip()
    if not name:
        flash("Name is required", "error")
        return redirect(url_for("owner.owner_customer_detail", customer_id=customer_id))
    conn = get_db()
    conn.execute("UPDATE customers SET name=?,mobile=?,address=? WHERE id=?",
                 (name, mobile, address, customer_id))
    conn.commit()
    conn.close()
    flash("Customer updated!", "success")
    return redirect(url_for("owner.owner_customer_detail", customer_id=customer_id))


@bp.route("/notify-log")
@owner_required
def notify_log_view():
    """Owner sees all WhatsApp notifies sent."""
    conn = get_db()
    logs = conn.execute(
        "SELECT * FROM notify_log ORDER BY sent_at DESC"
    ).fetchall()
    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]
    conn.close()

    def fmtdt(d):
        if not d: return "—"
        parts = str(d).split(" ")
        dp = parts[0].split("-") if parts else []
        date_fmt = f"{dp[2]}-{dp[1]}-{dp[0]}" if len(dp)==3 else parts[0]
        time_fmt = parts[1][:5] if len(parts)>1 else ""
        return f"{date_fmt} {time_fmt}"

    log_list = [{"order_code":r["order_code"],"customer":r["customer"],
                 "mobile":r["mobile"],"lang":r["lang"].upper(),"sent_at":fmtdt(r["sent_at"])}
                for r in logs]
    return render_template("owner/notify_log.html",
        active_page="whatsapp", show_voice=False,
        urgent_count=urgent_count, logs=log_list)


# ══════════════════════════════════════════════
#  SALARY MODULE
# ══════════════════════════════════════════════

@bp.route("/salary")
@owner_required
def salary():
    conn = get_db()
    period = request.args.get("period","month")
    today  = date.today().isoformat()

    if period == "week":
        from datetime import timedelta as td
        start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
        period_label = f"This week ({start[8:]}-{start[5:7]} to {today[8:]}-{today[5:7]})"
    elif period == "all":
        start = "2000-01-01"
        period_label = "All time"
    else:
        period = "month"
        start = today[:7] + "-01"
        period_label = date.today().strftime("%B %Y")

    emps = conn.execute("SELECT name FROM employees WHERE active=1 ORDER BY name").fetchall()
    advances_all = conn.execute(
        "SELECT * FROM salary_advances ORDER BY advance_date DESC"
    ).fetchall()

    employees = []
    for emp in emps:
        name = emp["name"]
        logs = conn.execute("""
            SELECT order_code, garment_type, qty_done, making_rate, log_date,
                   CAST(qty_done AS REAL) * CAST(making_rate AS REAL) as earning
            FROM work_logs
            WHERE employee_name=? AND log_date >= ?
            ORDER BY log_date DESC, id DESC
        """, (name, start)).fetchall()

        total_earned  = sum(r["earning"] or 0 for r in logs)
        total_pieces  = sum(r["qty_done"] or 0 for r in logs)
        total_orders  = len(set(r["order_code"] for r in logs if r["order_code"]))

        adv_period = conn.execute(
            "SELECT COALESCE(SUM(amount),0) as total FROM salary_advances WHERE employee_name=? AND advance_date >= ?",
            (name, start)
        ).fetchone()["total"] or 0

        employees.append({
            "name":         name,
            "total_pieces": total_pieces,
            "total_orders": total_orders,
            "total_earned": total_earned,
            "total_advance":adv_period,
            "net_payable":  total_earned - adv_period,
            "logs": [{"order_code":r["order_code"],"garment_type":r["garment_type"],
                      "qty_done":r["qty_done"],"earning":r["earning"] or 0,
                      "log_date":r["log_date"]} for r in logs]
        })

    def fmtd(d):
        if not d: return "—"
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    advances = [{"employee_name":a["employee_name"],"amount":a["amount"],
                 "note":a["note"] or "","advance_date":fmtd(a["advance_date"])} for a in advances_all]

    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]
    conn.close()

    return render_template("owner/salary.html",
        active_page="salary", show_voice=False,
        urgent_count=urgent_count,
        employees=employees, advances=advances,
        period=period, period_label=period_label)


@bp.route("/api/salary/advance", methods=["POST"])
@owner_required
def api_salary_advance():
    data   = request.get_json(silent=True) or {}
    name   = data.get("employee_name","").strip()
    amount = float(data.get("amount",0) or 0)
    note   = data.get("note","").strip()
    if not name or amount <= 0:
        return jsonify({"ok":False,"error":"Name and amount required"})
    today = date.today().isoformat()
    now   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn  = get_db()
    conn.execute(
        "INSERT INTO salary_advances(employee_name,amount,note,advance_date,created_at) VALUES(?,?,?,?,?)",
        (name, amount, note, today, now)
    )
    conn.commit(); conn.close()
    return jsonify({"ok":True})


@bp.route("/api/save-setting", methods=["POST"])
@owner_required
def api_save_setting():
    data  = request.get_json(silent=True) or {}
    key   = data.get("key","").strip()
    value = data.get("value","").strip()
    if not key:
        return jsonify({"ok":False,"error":"No key"})
    set_setting(key, value)
    return jsonify({"ok":True})


@bp.route("/api/employee-skill", methods=["POST"])
@owner_required
def api_employee_skill():
    data   = request.get_json(silent=True) or {}
    emp_id = data.get("employee_id")
    skills = data.get("skills","stitch")
    if not emp_id:
        return jsonify({"ok":False,"error":"No employee id"})
    conn = get_db()
    conn.execute("UPDATE employees SET skills=? WHERE id=?", (skills, emp_id))
    conn.commit(); conn.close()
    return jsonify({"ok":True})


# ══════════════════════════════════════════════
#  PAST ORDERS (OLD DATA ENTRY)
# ══════════════════════════════════════════════

@bp.route("/past-orders")
@owner_required
def past_orders():
    """Page to enter old/historical delivered orders — mirrors new_order flow."""
    import json as _json
    conn = get_db()

    # Garment rates — same logic as new_order
    RATE_DEFAULTS = {
        "Shirt":"350","Shirt Linen":"450","Pant":"450","Pant Double":"550",
        "Jeans":"550","Suit 2pc":"2800","Suit 3pc":"3500","Blazer":"2300",
        "Kurta":"800","Kurta Pajama":"1000","Pajama":"300","Pathani":"800",
        "Safari":"1500","Waistcoat":"800",
        "Alteration":"100","Cutting Only":"100"
    }
    deleted_csv = get_setting("deleted_customer_rates", "")
    deleted_set = set(x.strip() for x in deleted_csv.split(",") if x.strip())
    garment_rates = {}
    for n, default_rate in RATE_DEFAULTS.items():
        if n in deleted_set:
            continue
        cr = get_setting("customer_rate_"+n, "")
        if cr and cr.strip():
            garment_rates[n] = cr
        else:
            garment_rates[n] = get_setting("rate_"+n, default_rate)
    custom_rates = conn.execute("SELECT key,value FROM settings WHERE key LIKE 'customer_rate_%'").fetchall()
    for row in custom_rates:
        name = row["key"][14:]
        if name not in garment_rates and name not in deleted_set and row["value"] and row["value"].strip() and row["value"] != "0":
            garment_rates[name] = row["value"]

    # Measurement fields
    meas_rows = conn.execute("SELECT garment_type, field_name FROM measurement_fields ORDER BY garment_type, sort_order").fetchall()
    meas_fields = {}
    for r in meas_rows:
        meas_fields.setdefault(r["garment_type"], []).append(r["field_name"])

    # Garment type chips
    garment_types = {}
    for row in conn.execute("SELECT key, value FROM settings WHERE key LIKE 'types_%'").fetchall():
        gname = row["key"][6:]
        pairs = []
        for t in (row["value"] or "").split("|"):
            if ":" in t:
                k, v = t.split(":", 1)
                pairs.append({"k": k.strip(), "v": v.strip()})
        if pairs:
            garment_types[gname] = pairs

    # Peek next order code for display
    from database import peek_order_code
    next_code = peek_order_code()

    conn.close()
    return render_template("owner/past_orders.html",
        active_page="past_orders",
        garment_rates=garment_rates,
        garment_rates_json=_json.dumps({k: float(v) for k, v in garment_rates.items()}),
        meas_fields_json=_json.dumps(meas_fields),
        garment_types_json=_json.dumps(garment_types),
        next_code=next_code,
    )

@bp.route("/past-orders/save", methods=["POST"])
@owner_required
def past_orders_save():
    """Save a past/historical order — bulletproof version."""
    import json as _json
    data = request.get_json(silent=True) or {}

    customer_name  = (data.get("customer_name") or "").strip()
    customer_mobile= (data.get("mobile") or "").strip()
    customer_address = (data.get("address") or "").strip()
    order_date     = (data.get("order_date") or "").strip()
    delivery_date  = (data.get("delivery_date") or "").strip()
    total_amount   = float(data.get("total_amount") or 0)
    advance_paid   = float(data.get("advance_paid") or 0)
    payment_mode   = (data.get("payment_mode") or "cash").strip()
    note           = (data.get("note") or "").strip()
    garments       = data.get("garments") or []
    order_code_override = (data.get("order_code") or "").strip()
    is_delivered   = data.get("is_delivered", True)

    if not customer_name:
        return jsonify({"ok": False, "error": "Customer name required"})

    payable   = total_amount
    remaining = max(0, payable - advance_paid)
    now_str   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status    = "delivered" if is_delivered else "pending"

    try:
        conn = get_db()

        # 1. Customer — find or create
        customer_id = None
        if customer_mobile:
            r = conn.execute("SELECT id FROM customers WHERE mobile=?", (customer_mobile,)).fetchone()
            if r:
                customer_id = r["id"]
                conn.execute("UPDATE customers SET name=?, address=? WHERE id=?", (customer_name, customer_address, customer_id))
        if not customer_id:
            r = conn.execute("SELECT id FROM customers WHERE name=? ORDER BY id DESC LIMIT 1", (customer_name,)).fetchone()
            if r:
                customer_id = r["id"]
                if customer_address:
                    conn.execute("UPDATE customers SET address=? WHERE id=?", (customer_address, customer_id))
        if not customer_id:
            conn.execute("INSERT INTO customers(name,mobile,address,created_at) VALUES(?,?,?,?)",
                         (customer_name, customer_mobile or "", customer_address, now_str))
            conn.commit()
            r = conn.execute("SELECT id FROM customers ORDER BY id DESC LIMIT 1").fetchone()
            customer_id = r["id"] if r else 1

        # 2. Order code — use override or auto-generate
        order_code = order_code_override or ""
        if order_code:
            clash = conn.execute("SELECT id FROM orders WHERE order_code=?", (order_code,)).fetchone()
            if clash:
                order_code = ""

        if not order_code:
            r = conn.execute("SELECT value FROM settings WHERE key='last_order_code'").fetchone()
            last = int(r["value"]) if r else 3599
            existing = set()
            for row in conn.execute("SELECT order_code FROM orders").fetchall():
                c = row["order_code"]
                if c and c.isdigit():
                    existing.add(int(c))
            candidate = last + 1
            while candidate in existing:
                candidate += 1
            order_code = str(candidate)
            conn.execute("DELETE FROM settings WHERE key='last_order_code'")
            conn.execute("INSERT INTO settings(key,value) VALUES('last_order_code',?)", (str(candidate),))

        # 3. Insert order
        delivered_at = delivery_date if is_delivered else None
        conn.execute("""
            INSERT INTO orders(order_code,customer_id,order_date,delivery_date,
                total_amount,extra_charges,payable_amount,advance_paid,remaining,
                payment_mode,status,is_urgent,note,delivered_at,created_at)
            VALUES(?,?,?,?,?,0,?,?,?,?,?,0,?,?,?)
        """, (order_code, customer_id, order_date, delivery_date,
              total_amount, payable, advance_paid, remaining,
              payment_mode, status, note, delivered_at, now_str))
        conn.commit()

        r = conn.execute("SELECT id FROM orders WHERE order_code=?", (order_code,)).fetchone()
        order_id = r["id"] if r else None
        if not order_id:
            conn.close()
            return jsonify({"ok": False, "error": "Order insert failed"})

        # 4. Items
        for g in garments:
            gtype = (g.get("type") or "").strip()
            qty   = int(g.get("qty") or 1)
            rate  = float(g.get("rate") or 0)
            if gtype:
                meas  = g.get("measurements") or {}
                notes = (g.get("notes") or "").strip()
                sel   = g.get("selectedTypes") or []
                if sel:
                    notes = (notes.split("[")[0].strip() + " [" + ",".join(sel) + "]").strip()
                conn.execute("""
                    INSERT INTO order_items(order_id,garment_type,quantity,rate,amount,measurements,notes)
                    VALUES(?,?,?,?,?,?,?)
                """, (order_id, gtype, qty, rate, qty*rate, _json.dumps(meas), notes))

        # 5. Finance (single entry only)
        finance_date = order_date or delivery_date or now_str[:10]
        if advance_paid > 0:
            conn.execute("""
                INSERT INTO finance(tx_date,tx_type,category,amount,mode,order_id,note,created_by,created_at)
                VALUES(?,'income','payment',?,?,?,?,'owner',?)
            """, (finance_date, advance_paid, payment_mode, order_id,
                  "Past order #" + order_code, now_str))

        conn.commit()
        conn.close()
        from database import invalidate_settings_cache
        invalidate_settings_cache()
        return jsonify({"ok": True, "order_code": order_code})

    except Exception as e:
        try: conn.close()
        except: pass
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)})


# ══════════════════════════════════════════════
#  AUTO-BACKUP: FULL EXCEL EXPORT (ALL TABLES)
# ══════════════════════════════════════════════

@bp.route("/backup/excel")
@owner_required
def backup_excel():
    """Full Excel backup with all tables as separate sheets."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from io import BytesIO
    import json as _json

    conn = get_db()
    wb   = openpyxl.Workbook()

    hdr_fill = PatternFill("solid", fgColor="6366F1")
    hdr_font = Font(bold=True, color="FFFFFF", size=11)

    def write_sheet(ws, rows):
        if not rows:
            ws.append(["No data"])
            return
        keys = list(rows[0].keys())
        # Header row
        for col, k in enumerate(keys, 1):
            cell = ws.cell(row=1, column=col, value=k.upper())
            cell.font = hdr_font
            cell.fill = hdr_fill
            cell.alignment = Alignment(horizontal="center")
        ws.freeze_panes = "A2"
        for r_idx, row in enumerate(rows, 2):
            for col, k in enumerate(keys, 1):
                ws.cell(row=r_idx, column=col, value=str(row[k] or "") if row[k] is not None else "")
        for col in ws.columns:
            max_len = max((len(str(c.value or "")) for c in col), default=8)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 3, 45)

    # Sheet 1: Orders (with customer name & garments)
    ws1 = wb.active
    ws1.title = "Orders"
    orders = conn.execute("""
        SELECT o.order_code, c.name as customer, c.mobile, o.order_date, o.delivery_date,
               o.status, o.total_amount, o.advance_paid, o.remaining, o.payment_mode,
               o.note, o.delivered_at, o.created_at
        FROM orders o LEFT JOIN customers c ON c.id=o.customer_id
        ORDER BY o.id DESC
    """).fetchall()
    write_sheet(ws1, orders)

    # Sheet 2: Order Items
    ws2 = wb.create_sheet("Order Items")
    items = conn.execute("""
        SELECT oi.id, o.order_code, c.name as customer, oi.garment_type,
               oi.quantity, oi.rate, oi.amount, oi.measurements, oi.notes
        FROM order_items oi
        JOIN orders o ON o.id=oi.order_id
        LEFT JOIN customers c ON c.id=o.customer_id
        ORDER BY oi.id DESC
    """).fetchall()
    write_sheet(ws2, items)

    # Sheet 3: Customers
    ws3 = wb.create_sheet("Customers")
    customers = conn.execute("SELECT * FROM customers ORDER BY id DESC").fetchall()
    write_sheet(ws3, customers)

    # Sheet 4: Finance
    ws4 = wb.create_sheet("Finance")
    finance = conn.execute("""
        SELECT f.id, f.tx_date, f.tx_type, f.category, f.amount, f.mode,
               o.order_code, f.note, f.created_by, f.created_at
        FROM finance f LEFT JOIN orders o ON o.id=f.order_id
        ORDER BY f.id DESC
    """).fetchall()
    write_sheet(ws4, finance)

    # Sheet 5: Work Logs
    ws5 = wb.create_sheet("Work Logs")
    wlogs = conn.execute("SELECT * FROM work_logs ORDER BY id DESC").fetchall()
    write_sheet(ws5, wlogs)

    # Sheet 6: Employees
    ws6 = wb.create_sheet("Employees")
    emps = conn.execute("SELECT * FROM employees ORDER BY id").fetchall()
    write_sheet(ws6, emps)

    conn.close()

    # Update last_backup_at setting
    set_setting("last_backup_at", datetime.now().strftime("%Y-%m-%d %H:%M"))

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    from flask import send_file
    fname = f"uttam_tailors_backup_{datetime.now().strftime('%d-%m-%Y_%H%M')}.xlsx"
    return send_file(buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True, download_name=fname)


# ══════════════════════════════════════════════
#  EDIT ORDER (full edit — all fields + images)
# ══════════════════════════════════════════════

@bp.route("/orders/edit/<order_code>")
@owner_required
def order_edit(order_code):
    import json as _json, os as _os
    from config import Config
    conn = get_db()

    o = conn.execute("""
        SELECT o.*, c.name as cname, c.mobile as cmobile, c.address as caddress, c.id as cid
        FROM orders o LEFT JOIN customers c ON c.id=o.customer_id
        WHERE o.order_code=?
    """, (order_code,)).fetchone()
    if not o:
        conn.close()
        return "<h2>Order not found</h2>", 404

    items = conn.execute("SELECT * FROM order_items WHERE order_id=?", (o["id"],)).fetchall()
    garments = []
    for it in items:
        try: meas = _json.loads(it["measurements"] or "{}")
        except: meas = {}
        garments.append({"type":it["garment_type"],"qty":it["quantity"],
                         "rate":it["rate"],"meas":meas,"notes":it["notes"] or ""})

    # Images
    images = []
    rows = conn.execute("SELECT file_path FROM order_images WHERE order_id=? ORDER BY id", (o["id"],)).fetchall()
    images = [r["file_path"] for r in rows if r["file_path"] and not r["file_path"].startswith("temp:")]
    if not images:
        folder = _os.path.join(Config.UPLOAD_FOLDER, order_code)
        if _os.path.isdir(folder):
            images = [f"/static/order_images/{order_code}/{f}"
                      for f in sorted(_os.listdir(folder))
                      if f.lower().endswith((".jpg",".jpeg",".png",".gif",".webp"))]

    # Garment rates + measurement fields
    garment_names = ["Shirt","Shirt Linen","Pant","Pant Double","Jeans","Suit 2pc","Suit 3pc",
        "Blazer","Kurta","Kurta Pajama","Pajama","Pathani","Safari","Waistcoat",
        "Alteration","Cutting Only"]
    garment_rates = {n: get_setting("customer_rate_"+n,"") or get_setting("rate_"+n,"0") for n in garment_names}
    custom = conn.execute("SELECT key,value FROM settings WHERE key LIKE 'customer_rate_%'").fetchall()
    for row in custom:
        name = row["key"][14:]
        if name not in garment_rates: garment_rates[name] = row["value"]

    meas_fields = {}
    for r in conn.execute("SELECT garment_type, field_name FROM measurement_fields ORDER BY garment_type, sort_order").fetchall():
        meas_fields.setdefault(r["garment_type"], []).append(r["field_name"])

    garment_types = {}
    for row in conn.execute("SELECT key, value FROM settings WHERE key LIKE 'types_%'").fetchall():
        gname = row["key"][6:]
        pairs = []
        for t in (row["value"] or "").split("|"):
            if ":" in t:
                k, v = t.split(":", 1)
                pairs.append({"k": k.strip(), "v": v.strip()})
        if pairs: garment_types[gname] = pairs

    urgent_count = conn.execute("SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'").fetchone()["c"]
    conn.close()

    return render_template("owner/order_edit.html",
        active_page="owner_orders", show_voice=False,
        urgent_count=urgent_count,
        order=dict(o),
        garments_json=_json.dumps(garments),
        images=images,
        garment_rates=garment_rates,
        garment_rates_json=_json.dumps({k: float(v) for k, v in garment_rates.items()}),
        meas_fields_json=_json.dumps(meas_fields),
        garment_types_json=_json.dumps(garment_types),
    )


@bp.route("/orders/edit/<order_code>/save", methods=["POST"])
@owner_required
def order_edit_save(order_code):
    import json as _json
    data = request.get_json(silent=True) or {}
    conn = get_db()
    try:
        o = conn.execute("SELECT id, customer_id FROM orders WHERE order_code=?", (order_code,)).fetchone()
        if not o:
            return jsonify({"ok": False, "error": "Order not found"})
        order_id    = o["id"]
        customer_id = o["customer_id"]

        # Update customer
        name    = (data.get("customer_name") or "").strip()
        mobile  = (data.get("mobile") or "").strip()
        address = (data.get("address") or "").strip()
        if name:
            conn.execute("UPDATE customers SET name=?, mobile=?, address=? WHERE id=?",
                         (name, mobile, address, customer_id))

        # Update order
        conn.execute("""
            UPDATE orders SET
                order_date=?, delivery_date=?, note=?, is_urgent=?,
                total_amount=?, extra_charges=?, payable_amount=?,
                advance_paid=?, remaining=?, payment_mode=?, status=?
            WHERE id=?
        """, (
            data.get("order_date",""),
            data.get("delivery_date",""),
            data.get("note",""),
            1 if data.get("is_urgent") else 0,
            float(data.get("total_amount",0)),
            float(data.get("extra_charges",0)),
            float(data.get("payable_amount",0)),
            float(data.get("advance_paid",0)),
            float(data.get("remaining",0)),
            data.get("payment_mode","cash"),
            data.get("status","pending"),
            order_id
        ))

        # Replace garment items
        conn.execute("DELETE FROM order_items WHERE order_id=?", (order_id,))
        for g in (data.get("garments") or []):
            gtype = (g.get("type") or "").strip()
            qty   = int(g.get("qty") or 1)
            rate  = float(g.get("rate") or 0)
            meas  = g.get("measurements") or {}
            notes = (g.get("notes") or "").strip()
            if gtype:
                conn.execute("""
                    INSERT INTO order_items(order_id,garment_type,quantity,rate,amount,measurements,notes)
                    VALUES(?,?,?,?,?,?,?)
                """, (order_id, gtype, qty, rate, qty*rate, _json.dumps(meas), notes))

        conn.commit()
        conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        try: conn.close()
        except: pass
        return jsonify({"ok": False, "error": str(e)})


# ── Website Admin ─────────────────────────────────────────────────────────────
@bp.route("/website")
def website_admin():
    if not session.get("owner_logged_in"):
        return redirect(url_for("owner.login", next=request.path))
    from database import get_db
    db = get_db()
    web_settings = {r["key"]: r["value"] for r in db.execute("SELECT key,value FROM settings").fetchall()}
    try: fabrics = db.execute("SELECT * FROM web_fabrics ORDER BY sort_order").fetchall()
    except: fabrics = []
    try:
        web_orders = db.execute("""
            SELECT o.order_code, o.status, o.order_date, o.payable_amount,
                   o.advance_paid, o.remaining, o.is_urgent, o.note,
                   COALESCE(c.name,'—') as cname, COALESCE(c.mobile,'') as mobile
            FROM orders o
            LEFT JOIN customers c ON c.id = o.customer_id
            WHERE o.note LIKE '[WEB/%' OR o.payment_mode IN ('online','razorpay')
            ORDER BY o.id DESC LIMIT 100
        """).fetchall()
    except: web_orders = []
    try: nav_items = db.execute("SELECT * FROM web_nav_items ORDER BY sort_order").fetchall()
    except: nav_items = []
    try: footer_make = db.execute("SELECT * FROM web_footer_make ORDER BY sort_order").fetchall()
    except: footer_make = []
    try: pages = db.execute("SELECT * FROM web_pages ORDER BY sort_order,id").fetchall()
    except: pages = []
    total_web = len(web_orders)
    try: today_web = db.execute("SELECT COUNT(*) FROM orders WHERE (note LIKE '[WEB/%' OR payment_mode IN ('online','razorpay')) AND DATE(order_date)=DATE('now')").fetchone()[0]
    except: today_web = 0
    try: pending_web = db.execute("SELECT COUNT(*) FROM orders WHERE (note LIKE '[WEB/%' OR payment_mode IN ('online','razorpay')) AND status NOT IN ('delivered','cancelled')").fetchone()[0]
    except: pending_web = 0
    fabric_count = len(fabrics)
    try:
        # Pull email/address/soft-delete status too, plus a live order count per
        # account (via orders.web_account_id) — the admin Accounts tab previously
        # only showed name/mobile/preview-count, so staff had no way to see a
        # customer's email, saved address, how many orders they'd placed, or
        # whether the account had been deleted.
        web_accounts = db.execute("""
            SELECT a.*,
                   (SELECT COUNT(*) FROM orders o WHERE o.web_account_id = a.id) AS order_count
            FROM web_accounts a
            ORDER BY a.id DESC
        """).fetchall()
    except: web_accounts = []
    return render_template("owner/website_admin.html",
        web_settings=web_settings, fabrics=fabrics, web_orders=web_orders,
        nav_items=nav_items, footer_make=footer_make, pages=pages,
        total_web=total_web, today_web=today_web, pending_web=pending_web, fabric_count=fabric_count,
        web_accounts=web_accounts)

@bp.route("/website/settings/save", methods=["POST"])
def website_settings_save():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    data = request.get_json() or {}
    # saveSetting sends {key: "setting_name", value: "val"}
    # saveSection sends {setting_name: "val", ...}
    if "key" in data and "value" in data:
        pairs = {data["key"]: data["value"]}
    else:
        pairs = data
    for key, val in pairs.items():
        if db.execute("SELECT 1 FROM settings WHERE key=?", (key,)).fetchone():
            db.execute("UPDATE settings SET value=? WHERE key=?", (val, key))
        else:
            db.execute("INSERT INTO settings(key,value) VALUES('commission_header_image',?)", (url,))
    db.commit()
    return jsonify({"ok": True, "url": url})


@bp.route("/website/fabrics/list")
def website_fabrics_list():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    try:
        rows = db.execute("SELECT * FROM web_fabrics ORDER BY sort_order").fetchall()
        return jsonify({"ok": True, "fabrics": [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "fabrics": []})

@bp.route("/website/fabric/add", methods=["POST"])
def website_fabric_add():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    try:
        img_url = d.get("image_url","") or ""
        db.execute("INSERT INTO web_fabrics(name,price_per_metre,stock_metres,fabric_type,image_url,active,sort_order) VALUES(?,?,?,?,?,1,(SELECT COALESCE(MAX(sort_order),0)+1 FROM web_fabrics))",
            (d.get("name",""), float(d.get("price",0)), float(d.get("stock",0)), d.get("fabric_type", d.get("type","cotton")), img_url))
        db.commit()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@bp.route("/website/fabric/upload-image/<int:fid>", methods=["POST"])
def website_fabric_upload(fid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    import os, uuid
    from database import get_db
    f_file = request.files.get("image")
    if not f_file: return jsonify({"ok":False,"error":"No file"})
    ext = os.path.splitext(f_file.filename)[1].lower() or '.jpg'
    fname = f"fab_{fid}_{uuid.uuid4().hex[:8]}{ext}"
    folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                          "static","website","img","fabrics")
    os.makedirs(folder, exist_ok=True)
    _fp = os.path.join(folder, fname); f_file.save(_fp)
    from app.utils.image_optimize import optimize_image as _oi; _fp = _oi(_fp); fname = os.path.basename(_fp)
    img_url = "/static/website/img/fabrics/" + fname
    db = get_db()
    db.execute("UPDATE web_fabrics SET image_url=? WHERE id=?", (img_url, fid))
    db.commit()
    return jsonify({"ok":True, "url": img_url})

@bp.route("/website/fabric/upload-temp-image", methods=["POST"])
def website_fabric_upload_temp():
    """Upload an image for the 'Add New Fabric' form, BEFORE the fabric exists.
    Just saves the file and returns its URL — addFabric() then sends that URL
    along with the rest of the new-fabric fields."""
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    import os, uuid
    f_file = request.files.get("image")
    if not f_file: return jsonify({"ok":False,"error":"No file"})
    ext = os.path.splitext(f_file.filename)[1].lower() or '.jpg'
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        return jsonify({"ok":False,"error":"Only JPG/PNG/WebP allowed"})
    fname = f"fab_new_{uuid.uuid4().hex[:10]}{ext}"
    folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                          "static","website","img","fabrics")
    os.makedirs(folder, exist_ok=True)
    _fp = os.path.join(folder, fname); f_file.save(_fp)
    from app.utils.image_optimize import optimize_image as _oi; _fp = _oi(_fp); fname = os.path.basename(_fp)
    img_url = "/static/website/img/fabrics/" + fname
    return jsonify({"ok":True, "url": img_url})

@bp.route("/website/fabric/media/list/<int:fid>")
def website_fabric_media_list(fid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    try:
        rows = db.execute("SELECT * FROM web_fabric_media WHERE fabric_id=? ORDER BY sort_order, id", (fid,)).fetchall()
        return jsonify({"ok": True, "media": [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "media": []})

@bp.route("/website/fabric/media/upload/<int:fid>", methods=["POST"])
def website_fabric_media_upload(fid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    import os, uuid
    from database import get_db
    f_file = request.files.get("image")
    if not f_file: return jsonify({"ok":False,"error":"No file"})
    db = get_db()
    try:
        cnt = db.execute("SELECT COUNT(*) as c FROM web_fabric_media WHERE fabric_id=?", (fid,)).fetchone()["c"]
    except Exception:
        cnt = 0
    if cnt >= 4:
        return jsonify({"ok": False, "error": "Maximum 4 gallery images per fabric. Remove one first."})
    ext = os.path.splitext(f_file.filename)[1].lower() or '.jpg'
    fname = f"fab_{fid}_{uuid.uuid4().hex[:8]}{ext}"
    folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                          "static","website","img","fabrics")
    os.makedirs(folder, exist_ok=True)
    _fp = os.path.join(folder, fname); f_file.save(_fp)
    from app.utils.image_optimize import optimize_image as _oi; _fp = _oi(_fp); fname = os.path.basename(_fp)
    img_url = "/static/website/img/fabrics/" + fname
    db.execute("INSERT INTO web_fabric_media(fabric_id, url, sort_order) VALUES(?,?,(SELECT COALESCE(MAX(sort_order),0)+1 FROM web_fabric_media WHERE fabric_id=?))",
               (fid, img_url, fid))
    db.commit()
    return jsonify({"ok": True, "url": img_url})

@bp.route("/website/fabric/media/delete/<int:mid>", methods=["POST"])
def website_fabric_media_delete(mid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    db.execute("DELETE FROM web_fabric_media WHERE id=?", (mid,))
    db.commit()
    return jsonify({"ok": True})


@bp.route("/website/fabric/delete/<int:fid>", methods=["POST"])
def website_fabric_delete(fid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    db.execute("DELETE FROM web_fabrics WHERE id=?", (fid,))
    db.commit()
    return jsonify({"ok": True})


# ── Website Services Admin ────────────────────────────────────────────────────
@bp.route("/website/services/categories")
def website_services_categories():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    try:
        cats = db.execute("SELECT * FROM web_service_categories ORDER BY sort_order, id").fetchall()
        return jsonify({"ok":True, "categories":[dict(c) for c in cats]})
    except: return jsonify({"ok":True, "categories":[]})

@bp.route("/website/services/items")
def website_services_items():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    try:
        items = db.execute("SELECT i.*, c.name as cat_name FROM web_service_items i JOIN web_service_categories c ON i.category_id=c.id ORDER BY c.sort_order, i.sort_order, i.id").fetchall()
        return jsonify({"ok":True, "items":[dict(i) for i in items]})
    except: return jsonify({"ok":True, "items":[]})

@bp.route("/website/services/category/add", methods=["POST"])
def website_services_cat_add():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    name = d.get("name","").strip()
    if not name: return jsonify({"ok":False,"error":"Name required"})
    try:
        db.execute("INSERT INTO web_service_categories(name, sort_order) VALUES(?, (SELECT COALESCE(MAX(sort_order),0)+1 FROM web_service_categories))", (name,))
        db.commit()
        cat_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        return jsonify({"ok":True, "id": cat_id})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

@bp.route("/website/services/category/delete/<int:cid>", methods=["POST"])
def website_services_cat_delete(cid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    db.execute("DELETE FROM web_service_items WHERE category_id=?", (cid,))
    db.execute("DELETE FROM web_service_categories WHERE id=?", (cid,))
    db.commit()
    return jsonify({"ok":True})

@bp.route("/website/services/item/add", methods=["POST"])
def website_services_item_add():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    cat_id = d.get("category_id")
    name = d.get("name","").strip()
    if not cat_id or not name: return jsonify({"ok":False,"error":"Category and name required"})
    try:
        # Auto-generate SEO slug from item name
        import re as _re_slug
        _slug_base = _re_slug.sub(r"[^a-z0-9\s-]", "", name.lower())
        _slug_base = _re_slug.sub(r"[\s-]+", "-", _slug_base).strip("-")
        _slug = _slug_base
        _counter = 2
        while db.execute("SELECT id FROM web_service_items WHERE slug=?", (_slug,)).fetchone():
            _slug = f"{_slug_base}-{_counter}"; _counter += 1
        db.execute("INSERT INTO web_service_items(category_id, name, subtitle, price, image_url, sort_order, slug) VALUES(?,?,?,?,?,(SELECT COALESCE(MAX(sort_order),0)+1 FROM web_service_items WHERE category_id=?),?)",
            (cat_id, name, d.get("subtitle",""), d.get("price","0"), d.get("image_url",""), cat_id, _slug))
        db.commit()
        new_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        return jsonify({"ok":True, "id": new_id})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

@bp.route("/website/services/item/delete/<int:iid>", methods=["POST"])
def website_services_item_delete(iid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    db.execute("DELETE FROM web_service_items WHERE id=?", (iid,))
    db.commit()
    return jsonify({"ok":True})

@bp.route("/website/services/seed", methods=["POST"])
def website_services_seed():
    """Seed default services from current price settings"""
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    # Only seed if empty
    existing = db.execute("SELECT COUNT(*) as c FROM web_service_categories").fetchone()["c"]
    if existing > 0: return jsonify({"ok":True, "seeded":False, "msg":"Already has data"})
    settings = {r["key"]: r["value"] for r in db.execute("SELECT key,value FROM settings").fetchall()}
    def r(k): return settings.get("customer_rate_"+k, "0")
    defaults = [
        ("Shirts", [("Formal Shirt","Regular / Linen / Cotton", r("Shirt")+" – "+r("Shirt Linen"))]),
        ("Pants & Jeans", [("Pant (Single pleat)","Standard cut",r("Pant")),("Pant (Double pleat)","Pleated formal",r("Pant Double")),("Jeans","",r("Jeans"))]),
        ("Suits", [("Suit 2-Piece","Jacket + Pant",r("Suit 2pc")),("Suit 3-Piece","Jacket + Pant + Waistcoat",r("Suit 3pc"))]),
        ("Blazers & Waistcoat", [("Blazer","",r("Blazer")),("Waistcoat","",r("Waistcoat"))]),
        ("Kurta, Pathani & Ethnic", [("Kurta (only)","",r("Kurta")),("Kurta + Pajama set","",r("Kurta Pajama")),("Pajama (only)","",r("Pajama")),("Pathani Suit","Kurta + Shalwar",r("Pathani"))]),
        ("Wedding & Occasion Wear", [("Safari Suit","",r("Safari"))]),
        ("Alterations & Repairs", [("Alteration (any garment)","Fit adjustment, shortening, etc.","50+")]),
    ]
    for sort_cat, (cat_name, items) in enumerate(defaults):
        db.execute("INSERT INTO web_service_categories(name, sort_order) VALUES(?,?)", (cat_name, sort_cat))
        cat_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        for sort_item, (iname, isub, iprice) in enumerate(items):
            db.execute("INSERT INTO web_service_items(category_id,name,subtitle,price,sort_order) VALUES(?,?,?,?,?)", (cat_id,iname,isub,iprice,sort_item))
    db.commit()
    return jsonify({"ok":True, "seeded":True})

@bp.route("/website/services/item/price/<int:iid>", methods=["POST"])
def website_services_item_price(iid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    new_price_raw = d.get("price", "0")
    try:
        new_price = float(new_price_raw)
    except (TypeError, ValueError):
        new_price = 0
    old_row = db.execute("SELECT price FROM web_service_items WHERE id=?", (iid,)).fetchone()
    old_price = old_row["price"] if old_row else None
    db.execute("UPDATE web_service_items SET price=? WHERE id=?", (new_price_raw, iid))
    db.commit()
    try:
        if old_price is not None and new_price < float(old_price):
            from app.routes.website import _notify_wishlist_price_drop
            _notify_wishlist_price_drop(db, iid, float(old_price), new_price)
    except Exception:
        pass
    return jsonify({"ok":True})


@bp.route("/website/services/item/stock/<int:iid>", methods=["POST"])
def website_services_item_stock(iid):
    """Set ready-made stock quantity for a service item. -1 = made-to-order (no stock tracking)."""
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    try:
        new_stock = int(d.get("stock_qty", -1))
    except (TypeError, ValueError):
        new_stock = -1
    old_row = db.execute("SELECT stock_qty FROM web_service_items WHERE id=?", (iid,)).fetchone()
    old_stock = old_row["stock_qty"] if old_row else None
    db.execute("UPDATE web_service_items SET stock_qty=? WHERE id=?", (new_stock, iid))
    db.commit()
    try:
        if old_stock is not None and old_stock == 0 and new_stock > 0:
            from app.routes.website import _notify_wishlist_back_in_stock
            _notify_wishlist_back_in_stock(db, iid)
    except Exception:
        pass
    return jsonify({"ok":True})


@bp.route("/website/services/item/sort/<int:iid>", methods=["POST"])
def website_services_item_sort(iid):
    """Set the display/sort order for a service item (lower = shown first in 'Default order')."""
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    try:
        new_sort = int(d.get("sort_order", 0))
    except (TypeError, ValueError):
        new_sort = 0
    db.execute("UPDATE web_service_items SET sort_order=? WHERE id=?", (new_sort, iid))
    db.commit()
    return jsonify({"ok":True})


@bp.route("/website/services/item/delivery/<int:iid>", methods=["POST"])
def website_services_item_delivery(iid):
    """Set the delivery estimate text shown on the product detail page for this item."""
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    txt = (d.get("delivery_estimate") or "").strip()[:120]
    try:
        db.execute("UPDATE web_service_items SET delivery_estimate=? WHERE id=?", (txt, iid))
        db.commit()
        return jsonify({"ok":True})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)})


@bp.route("/website/services/item/related/<int:iid>", methods=["GET"])
def website_services_item_related_get(iid):
    """Return the list of related-item ids curated for this product ('Complete the Look')."""
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    try:
        rows = db.execute(
            "SELECT related_item_id FROM web_related_items WHERE item_id=? ORDER BY sort_order, id", (iid,)
        ).fetchall()
        return jsonify({"ok": True, "related_ids": [r["related_item_id"] for r in rows]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "related_ids": []})


@bp.route("/website/services/item/related/<int:iid>", methods=["POST"])
def website_services_item_related_save(iid):
    """Save the curated 'Complete the Look' related-item picks for this product."""
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    ids = d.get("related_ids") or []
    try:
        clean_ids = []
        for x in ids:
            try:
                xi = int(x)
                if xi != iid and xi not in clean_ids:
                    clean_ids.append(xi)
            except (TypeError, ValueError):
                continue
        db.execute("DELETE FROM web_related_items WHERE item_id=?", (iid,))
        for pos, rid in enumerate(clean_ids):
            db.execute(
                "INSERT INTO web_related_items (item_id, related_item_id, sort_order) VALUES (?,?,?)",
                (iid, rid, pos)
            )
        db.commit()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@bp.route("/website/services/item/category/<int:iid>", methods=["POST"])
def website_services_item_category(iid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    db.execute("UPDATE web_service_items SET category_id=? WHERE id=?", (int(d.get("category_id",0)), iid))
    db.commit()
    return jsonify({"ok":True})


# ── Coupons ───────────────────────────────────────────────────
@bp.route("/website/coupons")
def website_coupons():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    try:
        rows = db.execute("SELECT * FROM web_coupons ORDER BY id DESC").fetchall()
        return jsonify({"ok":True,"coupons":[dict(r) for r in rows]})
    except: return jsonify({"ok":True,"coupons":[]})

@bp.route("/website/coupon/add", methods=["POST"])
def website_coupon_add():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    try:
        db.execute("""INSERT INTO web_coupons(code,discount_type,discount_value,min_order,max_uses,description,expires_on,active)
            VALUES(?,?,?,?,?,?,?,1)""",
            (d.get("code","").strip().upper(), d.get("discount_type","fixed"),
             float(d.get("discount_value",0)), float(d.get("min_order",0)),
             int(d.get("max_uses",0)), d.get("description",""), d.get("expires_on","")))
        db.commit()
        return jsonify({"ok":True})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

@bp.route("/website/coupon/toggle/<int:cid>", methods=["POST"])
def website_coupon_toggle(cid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    db.execute("UPDATE web_coupons SET active = CASE WHEN active=1 THEN 0 ELSE 1 END WHERE id=?", (cid,))
    db.commit()
    return jsonify({"ok":True})

@bp.route("/website/coupon/delete/<int:cid>", methods=["POST"])
def website_coupon_delete(cid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    db.execute("DELETE FROM web_coupons WHERE id=?", (cid,))
    db.commit()
    return jsonify({"ok":True})

# ── Default Sizes ──────────────────────────────────────────────
@bp.route("/website/sizes")
def website_sizes():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    try:
        rows = db.execute("SELECT * FROM garment_default_sizes ORDER BY garment_category,size_label").fetchall()
        return jsonify({"ok":True,"sizes":[dict(r) for r in rows]})
    except: return jsonify({"ok":True,"sizes":[]})

@bp.route("/website/sizes/save", methods=["POST"])
def website_sizes_save():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    import json
    db = get_db()
    d = request.get_json() or {}
    try:
        db.execute("""INSERT INTO garment_default_sizes(garment_category,size_label,measurements)
            VALUES(?,?,?) ON CONFLICT(garment_category,size_label)
            DO UPDATE SET measurements=excluded.measurements""",
            (d.get("garment_category"), d.get("size_label"), json.dumps(d.get("measurements",{}))))
        db.commit()
        return jsonify({"ok":True})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})


# ── Header / Footer settings ──────────────────────────────────
@bp.route("/website/nav-footer")
def website_nav_footer():
    if not session.get("owner_logged_in"): return redirect(url_for("owner.login"))
    from database import get_db
    db = get_db()
    web_settings = {r["key"]: r["value"] for r in db.execute("SELECT key,value FROM settings WHERE key LIKE 'web_%'").fetchall()}
    return render_template("owner/nav_footer_admin.html", web_settings=web_settings)

@bp.route("/website/nav-footer/save", methods=["POST"])
def website_nav_footer_save():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    for key, val in d.items():
        if key.startswith("web_"):
            db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, str(val)))
    db.commit()
    return jsonify({"ok":True})

# ── Daily Craft (Fresh From The Workshop) ─────────────────────────────────────

@bp.route("/api/daily-craft", methods=["GET"])
def admin_daily_craft_list():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    db = get_db()
    page = max(1, int(request.args.get("page", 1)))
    per = 24
    offset = (page-1)*per
    rows = db.execute("SELECT * FROM web_daily_craft ORDER BY id DESC LIMIT ? OFFSET ?", (per, offset)).fetchall()
    total = db.execute("SELECT COUNT(*) FROM web_daily_craft").fetchone()[0]
    return jsonify({"ok":True, "items":[dict(r) for r in rows], "total":total, "pages":max(1,(total+per-1)//per)})

@bp.route("/api/daily-craft/upload", methods=["POST"])
def admin_daily_craft_upload():
    if not session.get("owner_logged_in"): return jsonify({"ok":False,"error":"Unauthorized"}),403
    import os
    from werkzeug.utils import secure_filename
    file = request.files.get("image")
    if not file or not file.filename:
        return jsonify({"ok":False,"error":"No image provided"})
    ext = os.path.splitext(secure_filename(file.filename))[1].lower()
    if ext not in (".jpg",".jpeg",".png",".webp"):
        return jsonify({"ok":False,"error":"Images only (jpg/png/webp)"})
    caption = (request.form.get("caption","") or "").strip()[:200]
    tag = (request.form.get("tag","") or "").strip()[:60]
    save_dir = os.path.join(os.path.dirname(__file__), "../../static/uploads/daily_craft")
    os.makedirs(save_dir, exist_ok=True)
    import time as _t
    fname = str(int(_t.time()*1000)) + ext
    fpath = os.path.join(save_dir, fname)
    file.save(fpath)
    # Optimise — capture new path so the stored URL matches the converted file
    try:
        from app.utils.image_optimize import optimize_image
        fpath = optimize_image(fpath)
        fname = os.path.basename(fpath)
    except Exception:
        pass
    url = "/static/uploads/daily_craft/" + fname
    db = get_db()
    db.execute("INSERT INTO web_daily_craft(image_url,caption,tag,is_published) VALUES(?,?,?,1)", (url,caption,tag))
    db.commit()
    return jsonify({"ok":True,"url":url})

@bp.route("/api/daily-craft/<int:item_id>/toggle", methods=["POST"])
def admin_daily_craft_toggle(item_id):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    db = get_db()
    row = db.execute("SELECT is_published FROM web_daily_craft WHERE id=?", (item_id,)).fetchone()
    if not row: return jsonify({"ok":False,"error":"Not found"}),404
    new_val = 0 if row["is_published"] else 1
    db.execute("UPDATE web_daily_craft SET is_published=? WHERE id=?", (new_val, item_id))
    db.commit()
    return jsonify({"ok":True,"is_published":new_val})

@bp.route("/api/daily-craft/<int:item_id>/delete", methods=["POST"])
def admin_daily_craft_delete(item_id):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    db = get_db()
    row = db.execute("SELECT image_url FROM web_daily_craft WHERE id=?", (item_id,)).fetchone()
    if not row: return jsonify({"ok":False,"error":"Not found"}),404
    # Try to delete image file
    try:
        import os
        fpath = row["image_url"].lstrip("/")
        if os.path.exists(fpath): os.remove(fpath)
    except Exception:
        pass
    db.execute("DELETE FROM web_daily_craft WHERE id=?", (item_id,))
    db.commit()
    return jsonify({"ok":True})


# ── Nav items CRUD ──────────────────────────────────────────────
@bp.route("/website/nav/items")
def nav_items_list():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    try: rows = db.execute("SELECT * FROM web_nav_items ORDER BY sort_order").fetchall()
    except: rows = []
    return jsonify({"ok":True,"items":[dict(r) for r in rows]})

@bp.route("/website/nav/item/add", methods=["POST"])
def nav_item_add():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    try:
        db.execute("INSERT INTO web_nav_items(label,url,open_new_tab,sort_order,active) VALUES(?,?,?,?,1)",
                   (d.get("label",""), d.get("url",""), int(d.get("open_new_tab",0)), int(d.get("sort_order",99))))
        db.commit()
        return jsonify({"ok":True})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

@bp.route("/website/nav/item/update/<int:nid>", methods=["POST"])
def nav_item_update(nid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    db.execute("UPDATE web_nav_items SET label=?,url=?,open_new_tab=?,active=? WHERE id=?",
               (d.get("label",""), d.get("url",""), int(d.get("open_new_tab",0)), int(d.get("active",1)), nid))
    db.commit()
    return jsonify({"ok":True})

@bp.route("/website/nav/item/delete/<int:nid>", methods=["POST"])
def nav_item_delete(nid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    db.execute("DELETE FROM web_nav_items WHERE id=?", (nid,))
    db.commit()
    return jsonify({"ok":True})

# ── Footer "We Make" ──────────────────────────────────────────────
@bp.route("/website/footer/make/save", methods=["POST"])
def footer_make_save():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    items = d.get("items", [])
    try:
        db.execute("DELETE FROM web_footer_make")
        for i, item in enumerate(items):
            db.execute("INSERT INTO web_footer_make(label,url,sort_order) VALUES(?,?,?)",
                       (item.get("label",""), item.get("url",""), i))
        db.commit()
        return jsonify({"ok":True})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

# ── Custom pages ──────────────────────────────────────────────────
@bp.route("/website/pages")
def web_pages_list():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    try: rows = db.execute("SELECT * FROM web_pages ORDER BY sort_order,id").fetchall()
    except: rows = []
    return jsonify({"ok":True,"pages":[dict(r) for r in rows]})

@bp.route("/website/page/add", methods=["POST"])
def web_page_add():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    import re as _re
    db = get_db()
    d = request.get_json() or {}
    title = d.get("title","").strip()
    if not title: return jsonify({"ok":False,"error":"Title required"})
    slug = _re.sub(r"[^a-z0-9]+","-",title.lower()).strip("-")
    try:
        db.execute("INSERT INTO web_pages(title,slug,content,show_in_footer) VALUES(?,?,?,?)",
                   (title, slug, d.get("content",""), int(d.get("show_in_footer",1))))
        db.commit()
        return jsonify({"ok":True,"slug":slug})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

@bp.route("/website/page/update/<int:pid>", methods=["POST"])
def web_page_update(pid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    db.execute("UPDATE web_pages SET title=?,content=?,show_in_footer=? WHERE id=?",
               (d.get("title",""), d.get("content",""), int(d.get("show_in_footer",1)), pid))
    db.commit()
    return jsonify({"ok":True})

@bp.route("/website/page/delete/<int:pid>", methods=["POST"])
def web_page_delete(pid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    db.execute("DELETE FROM web_pages WHERE id=?", (pid,))
    db.commit()
    return jsonify({"ok":True})



# ── SEO Save Routes ───────────────────────────────────────────────────────────

@bp.route("/website/seo/item/<int:item_id>", methods=["POST"])
def website_seo_item(item_id):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    try:
        db = get_db(); d = request.get_json() or {}
        import re as _rs
        slug = _rs.sub(r"[^a-z0-9-]","", (d.get("slug","") or "").strip().lower()).strip("-")
        if slug:
            ex = db.execute("SELECT id FROM web_service_items WHERE slug=? AND id!=?", (slug, item_id)).fetchone()
            if ex: return jsonify({"ok":False,"error":"Slug already in use by another item."})
        ups, vals = [], []
        for k,v in [("slug",slug),("meta_title",(d.get("meta_title","") or "").strip()),("meta_desc",(d.get("meta_desc","") or "").strip())]:
            if k in d: ups.append(f"{k}=?"); vals.append(v)
        if ups: vals.append(item_id); db.execute(f"UPDATE web_service_items SET {', '.join(ups)} WHERE id=?", vals); db.commit()
        return jsonify({"ok":True,"slug":slug})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})


@bp.route("/website/seo/static/<page_key>", methods=["POST"])
def website_seo_static(page_key):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    try:
        db = get_db(); d = request.get_json() or {}
        mt = (d.get("meta_title","") or "").strip()
        md = (d.get("meta_desc","") or "").strip()
        og = (d.get("og_image","") or "").strip()
        rb = (d.get("robots","index,follow") or "index,follow").strip()
        try:
            db.execute("""INSERT INTO seo_static_pages(page_key,meta_title,meta_desc,og_image,robots) VALUES(?,?,?,?,?)
                ON CONFLICT(page_key) DO UPDATE SET meta_title=EXCLUDED.meta_title,meta_desc=EXCLUDED.meta_desc,og_image=EXCLUDED.og_image,robots=EXCLUDED.robots""",
                (page_key, mt, md, og, rb))
        except Exception:
            db.execute("INSERT OR REPLACE INTO seo_static_pages(page_key,meta_title,meta_desc,og_image,robots) VALUES(?,?,?,?,?)",
                (page_key, mt, md, og, rb))
        db.commit()
        return jsonify({"ok":True})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})


@bp.route("/website/seo/tracking", methods=["POST"])
def website_seo_tracking():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    try:
        db = get_db(); d = request.get_json() or {}
        keys = ["tracking_ga4_id","tracking_gtm_id","tracking_meta_pixel","tracking_gsc_meta","robots_txt"]
        for k in keys:
            if k in d:
                db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (k, d[k] or ""))
        db.commit()
        return jsonify({"ok":True})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})


@bp.route("/website/seo/all-static", methods=["GET"])
def website_seo_all_static():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    try:
        db = get_db()
        rows = db.execute("SELECT * FROM seo_static_pages").fetchall()
        return jsonify({"ok":True,"pages":[dict(r) for r in rows]})
    except Exception as e: return jsonify({"ok":False,"pages":[]})

@bp.route("/website/run-migrations", methods=["POST"])
def run_migrations():
    """One-time route to create missing tables on production DB"""
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    # Detect whether we're on SQLite (local) or PostgreSQL (server) and use the
    # right SQL dialect for each — SQLite doesn't understand SERIAL / ::text casts.
    is_sqlite = True
    try:
        is_sqlite = ("sqlite" in db.__class__.__module__.lower()) or ("sqlite" in str(type(db)).lower())
    except Exception:
        is_sqlite = True
    pk = "INTEGER PRIMARY KEY AUTOINCREMENT" if is_sqlite else "SERIAL PRIMARY KEY"
    created_at_default = "''" if is_sqlite else "NOW()::text"

    tables = [
        f"""CREATE TABLE IF NOT EXISTS home_sections (
            id {pk}, section_key TEXT NOT NULL UNIQUE,
            section_title TEXT NOT NULL, content TEXT NOT NULL DEFAULT '{{}}',
            sort_order INTEGER DEFAULT 0, active INTEGER DEFAULT 1)""",
        f"""CREATE TABLE IF NOT EXISTS web_item_tiles (
            id {pk}, item_id INTEGER NOT NULL,
            emoji TEXT DEFAULT '', text TEXT NOT NULL, sort_order INTEGER DEFAULT 0)""",
        f"""CREATE TABLE IF NOT EXISTS web_item_faq (
            id {pk}, item_id INTEGER NOT NULL,
            question TEXT NOT NULL, answer TEXT NOT NULL, sort_order INTEGER DEFAULT 0)""",
        f"""CREATE TABLE IF NOT EXISTS web_item_bullets (
            id {pk}, item_id INTEGER NOT NULL,
            bullet TEXT NOT NULL, sort_order INTEGER DEFAULT 0)""",
        f"""CREATE TABLE IF NOT EXISTS web_pages (
            id {pk}, title TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE, content TEXT DEFAULT '',
            show_in_footer INTEGER DEFAULT 1, sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT {created_at_default})""",
        f"""CREATE TABLE IF NOT EXISTS web_nav_items (
            id {pk}, label TEXT NOT NULL,
            url TEXT NOT NULL, open_new_tab INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0, active INTEGER DEFAULT 1)""",
        f"""CREATE TABLE IF NOT EXISTS web_footer_make (
            id {pk}, label TEXT NOT NULL,
            url TEXT DEFAULT '', sort_order INTEGER DEFAULT 0)""",
        f"""CREATE TABLE IF NOT EXISTS web_coupons (
            id {pk}, code TEXT NOT NULL UNIQUE,
            discount_type TEXT NOT NULL DEFAULT 'fixed',
            discount_value REAL NOT NULL DEFAULT 0,
            min_order REAL NOT NULL DEFAULT 0,
            max_uses INTEGER DEFAULT 0, used_count INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1, expires_on TEXT DEFAULT '',
            description TEXT DEFAULT '')""",
        f"""CREATE TABLE IF NOT EXISTS garment_default_sizes (
            id {pk}, garment_category TEXT NOT NULL,
            size_label TEXT NOT NULL, measurements TEXT NOT NULL DEFAULT '{{}}',
            UNIQUE(garment_category, size_label))""",
    ]
    results = []
    for sql in tables:
        try:
            db.execute(sql)
            db.commit()
            table_name = sql.split('EXISTS')[1].strip().split('(')[0].strip().split()[0]
            results.append({"table": table_name, "ok": True})
        except Exception as e:
            results.append({"error": str(e)})
    return jsonify({"ok": True, "results": results})


# ══════════════════════════════════════════════════════════════════
# HOMEPAGE ADMIN
# ══════════════════════════════════════════════════════════════════
@bp.route("/website/homepage")
def homepage_admin():
    if not session.get("owner_logged_in"): return redirect(url_for("owner.login"))
    from database import get_db
    import json
    db = get_db()

    # Auto-create table if missing (PostgreSQL)
    try:
        db.execute("""CREATE TABLE IF NOT EXISTS home_sections (
            id SERIAL PRIMARY KEY, section_key TEXT NOT NULL UNIQUE,
            section_title TEXT NOT NULL, content TEXT NOT NULL DEFAULT '{}',
            sort_order INTEGER DEFAULT 0, active INTEGER DEFAULT 1)""")
        db.commit()
    except Exception:
        try:
            db.execute("""CREATE TABLE IF NOT EXISTS home_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT, section_key TEXT NOT NULL UNIQUE,
                section_title TEXT NOT NULL, content TEXT NOT NULL DEFAULT '{}',
                sort_order INTEGER DEFAULT 0, active INTEGER DEFAULT 1)""")
            db.commit()
        except Exception:
            pass

    # Auto-seed sections if empty
    try:
        count = db.execute("SELECT COUNT(*) FROM home_sections").fetchone()[0]
    except:
        count = 0

    if count == 0:
        defaults = [
            ('hero','Hero Banner','{"eyebrow":"Subhash Chowk, Sikar · Est. 1987","title_line1":"TAILORED","title_line2":"FOR YOU.","subtitle_italic":"Since 1987.","subtext":"Three generations of master craft. Every shirt, suit and kurta cut for your exact body — your measurements, your fabric, your style.","btn1_text":"Customise Your Garment","btn1_url":"/commission","btn2_text":"See what we make","btn2_url":"/our-craft","promise1":"✂ Custom fit","promise2":"⏱ 5–7 days","promise3":"🚚 Free delivery in Sikar","promise4":"↩ Free alteration","align":"left"}',1),
            ('heritage','Heritage Stats','{"stat1_num":"1987","stat1_label":"Est. since","stat2_num":"35+","stat2_label":"Years of craft","stat3_num":"1 Lakh+","stat3_label":"Garments delivered","stat4_num":"7","stat4_label":"Day turnaround"}',2),
            ('brands','Fabric Brands Ticker','{"label":"Fabrics we work with","brands":[{"name":"Raymonds","logo_url":""},{"name":"Siyarams","logo_url":""},{"name":"Fabindia","logo_url":""},{"name":"Donear","logo_url":""},{"name":"Bombay Dyeing","logo_url":""},{"name":"Holland and Sherry","logo_url":""},{"name":"Thomas Mason","logo_url":""}]}',3),
            ('catalogue','What We Make','{"kicker":"What we make","title":"Every garment, made to your exact measure.","subtitle":"No readymade. No shortcuts. Only what fits you perfectly.","btn_text":"See all services & prices →","btn_url":"/our-services","item_ids":"1,2,5,7,9"}',4),
            ('papa_story','The Legacy','{"kicker":"The legacy","quote":"My father spent 33 years building this craft. In 2025, I am taking it to every corner of India.","attribution":"— Nikhil Kumawat, son of Late Mr. Narendra Kumawat","link_text":"Read our full story →","link_url":"/our-story","body_para1":"My father, Late Mr. Narendra Kumawat, started Uttam Tailors at Subhash Chowk in 1987 with one machine and one rule.","body_para2":"He spent 33 years mastering every garment. In 2020, we lost him.","body_para3":"I took over with one mission: to carry his standard forward and bring his craft to every home in India.","year_text":"1987 — forever in every stitch"}',5),
            ('hiw','The Process','{"kicker":"The process","title":"Order to your door in four steps.","step1_num":"01","step1_title":"You order online","step1_body":"Choose garment, size, fabric. Pay 30% advance. Done in 3 minutes.","step2_num":"02","step2_title":"We confirm on WhatsApp","step2_body":"You get order details and ready date within minutes of placing.","step3_num":"03","step3_title":"Our masters stitch it","step3_body":"Every cut, every seam by our tailors in Sikar. Never outsourced.","step4_num":"04","step4_title":"Pickup or delivery","step4_body":"Collect from Subhash Chowk, or we deliver anywhere in India.","btn_text":"Customise Your Garment →","btn_url":"/commission"}',6),
            ('fabric_journey','From Bolt to Body','{"kicker":"From bolt to body","title":"Drag to see the transformation.","subtitle":"Raw fabric becomes a garment made precisely for you.","slide1_label":"Navy → Suit","slide1_color":"#1e2540","slide1_garment":"Two-piece Suit","slide2_label":"Khaki → Pant","slide2_color":"#d4c4a0","slide2_garment":"Tailored Pant","slide3_label":"Dark → Blazer","slide3_color":"#2a1a10","slide3_garment":"Blazer"}',7),
            ('reviews','What Sikar Says','{"kicker":"What Sikar says","title":"Words from our customers.","reviews":[{"init":"RK","name":"Rakesh Kumar","loc":"Sikar","text":"Got a suit stitched here for my son wedding. Perfect fit on the first try."},{"init":"MS","name":"Mohan Sharma","loc":"Subhash Chowk","text":"I have been coming for 12 years. The quality has never dropped once."},{"init":"AV","name":"Anil Verma","loc":"Piprali Road","text":"Three shirts done. Not one alteration needed. That says everything."},{"init":"SJ","name":"Sunil Jain","loc":"Sikar","text":"I gave my old kurta as reference. They made an identical one."},{"init":"DM","name":"Dinesh Mathur","loc":"Fatehpur Road","text":"Ordered a blazer. They came home to measure. Delivered in 6 days."},{"init":"VK","name":"Vijay Kumar","loc":"Losal Road","text":"Got a suit stitched for my brother wedding. Everyone was asking where we got it from."}]}',8),
            ('big_cta','Ready? Final CTA','{"kicker":"Ready?","title":"Your perfect garment is three minutes away.","subtitle":"Pick what you want. Tell us your size. We stitch. You wear it.","btn_text":"Customise Your Garment →","btn_url":"/commission","note":"30% advance · Free alteration · Rs. 100 off first order · Delivery across India"}',9),
            ('price_estimator','Price Estimator','{"kicker":"Instant estimate","title":"How much will it cost?","subtitle":"Select your garment and fabric type — see a price range instantly.","shirt_basic":"\u20b9350\u2013500","shirt_premium":"\u20b9600\u2013900","shirt_luxury":"\u20b91,000\u20131,800","pant_basic":"\u20b9300\u2013450","pant_premium":"\u20b9500\u2013800","pant_luxury":"\u20b9900\u20131,500","kurta_basic":"\u20b9400\u2013550","kurta_premium":"\u20b9600\u2013950","kurta_luxury":"\u20b91,100\u20132,000","suit_basic":"\u20b91,800\u20132,500","suit_premium":"\u20b92,800\u20134,500","suit_luxury":"\u20b95,000\u201310,000","blazer_basic":"\u20b9900\u20131,400","blazer_premium":"\u20b91,500\u20132,500","blazer_luxury":"\u20b93,000\u20136,000","jeans_basic":"\u20b9500\u2013700","jeans_premium":"\u20b9750\u20131,100","jeans_luxury":"\u20b91,200\u20132,200","school_basic":"\u20b9280\u2013400","school_premium":"\u20b9420\u2013600","school_luxury":"\u20b9650\u2013900","alter_basic":"\u20b980\u2013200","alter_premium":"\u20b9200\u2013400","alter_luxury":"\u20b9400\u2013800"}',10),
            ('occasion_finder','Occasion Finder','{"kicker":"Occasion finder","title":"What are you dressing for?","subtitle":"Tell us the occasion — we will tell you what to get stitched."}',11),
            ('fabric_guide','Fabric Guide','{"kicker":"Fabric guide","title":"Which fabric should you choose?","subtitle":"Tap any fabric to learn more.","fabrics":[{"name":"Cotton","icon":"ti-leaf","tagline":"Everyday comfort","season":"All seasons","best_for":"Shirts, kurtas, daily wear","price":"Budget friendly","care":"Machine washable"},{"name":"Linen","icon":"ti-wind","tagline":"Light and breathable","season":"Summer","best_for":"Casual shirts, pants","price":"Mid range","care":"Gentle wash, light iron"},{"name":"Wool","icon":"ti-cloud-snow","tagline":"Warm and formal","season":"Winter","best_for":"Suits, blazers, coats","price":"Premium","care":"Dry clean recommended"},{"name":"Silk","icon":"ti-sparkles","tagline":"Luxurious finish","season":"Weddings","best_for":"Suit, formal wear","price":"Luxury","care":"Dry clean only"},{"name":"Poly blend","icon":"ti-refresh","tagline":"Durable and easy care","season":"All seasons","best_for":"Uniforms, pants","price":"Budget friendly","care":"Machine washable"}]}',12),
            ('shop_status','Live Shop Status','{"next_slot":"3\u20135 days","custom_message":""}',13),
            ('action_cards','Action Cards','{"kicker":"How can we help you?","title":"Two ways to get perfectly fitted clothes","card1_eyebrow":"Don\'t know where to start?","card1_title":"Browse our designs","card1_desc":"See 50+ ready styles \u2014 shirts, suits, kurtas, pathani and more. Like something? We stitch it in your exact measurements.","card1_f1":"Photos of every design","card1_f2":"We suggest fabric & fit for you","card1_f3":"No decisions before you see options","card1_note":"Stitching starts from \u20b9350","card1_btn":"See all designs","card1_url":"/our-craft","card2_eyebrow":"Already know what you want?","card2_title":"Custom stitching","card2_desc":"Your measurements, your fabric, your style. Share the details \u2014 we stitch and deliver in 5\u20137 days. Alteration is free if the fit is off.","card2_f1":"Bring your fabric or choose ours","card2_f2":"WhatsApp updates during stitching","card2_f3":"Free alteration if fit is off","card2_note":"Ready in 5\u20137 days","card2_btn":"Start your order","card2_url":"/commission"}',14),
            ('ai_preview','AI Style Preview','{"kicker":"AI-Powered","title":"See your garment before we even thread the needle.","subtitle":"Pick a garment below \u2014 our AI instantly renders a real preview of your style choice."}',15),
        ]
        try:
            for key, title, content_json, sort in defaults:
                db.execute("INSERT INTO home_sections(section_key,section_title,content,sort_order,active) VALUES(?,?,?,?,1)",
                           (key, title, content_json, sort))
            db.commit()
        except Exception as e:
            pass

    # Top-up: insert new sections for existing DBs that already have data
    _topup = [
        ('price_estimator','Price Estimator', 10, 1),
        ('occasion_finder','Occasion Finder', 11, 1),
        ('fabric_guide',   'Fabric Guide',    12, 1),
        ('shop_status',    'Live Shop Status',13, 1),
        ('action_cards',   'Action Cards',    14, 1),
        ('ai_preview',     'AI Style Preview',15, 1),
    ]
    try:
        for _k,_t,_o,_a in _topup:
            db.execute("INSERT OR IGNORE INTO home_sections(section_key,section_title,content,sort_order,active) VALUES(?,?,'{}',?,?)",
                       (_k,_t,_o,_a))
        db.commit()
    except: pass

    try:
        sections = db.execute("SELECT * FROM home_sections ORDER BY sort_order").fetchall()
        sections_data = [{**dict(s), 'content_parsed': json.loads(s['content'])} for s in sections]
    except:
        sections_data = []

    # Load all products with images for the catalogue picker
    all_products = []
    try:
        items = db.execute("""
            SELECT i.id, i.name, i.image_url, c.name as cat_name
            FROM web_service_items i
            LEFT JOIN web_service_categories c ON c.id = i.category_id
            ORDER BY c.sort_order, i.sort_order, i.id
        """).fetchall()
        # Get first image from web_item_media if available
        media_rows = db.execute("SELECT item_id, url FROM web_item_media WHERE media_type='image' ORDER BY item_id, sort_order").fetchall()
        media_map = {}
        for m in media_rows:
            if m['item_id'] not in media_map:
                media_map[m['item_id']] = m['url']
        for item in items:
            img = media_map.get(item['id']) or item['image_url'] or ''
            all_products.append({'id': item['id'], 'name': item['name'], 'cat': item['cat_name'] or '', 'img': img})
    except:
        pass

    return render_template("owner/homepage_admin.html", sections=sections_data, all_products=all_products)

@bp.route("/website/homepage/section/get/<section_key>")
def homepage_section_get(section_key):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    import json
    db = get_db()
    try:
        row = db.execute("SELECT * FROM home_sections WHERE section_key=?", (section_key,)).fetchone()
        if not row: return jsonify({"ok":False,"error":"Not found"})
        return jsonify({"ok":True,"section":dict(row),"content":json.loads(row["content"])})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

@bp.route("/website/homepage/section/save", methods=["POST"])
def homepage_section_save():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    import json
    db = get_db()
    d = request.get_json() or {}
    section_key = d.get("section_key","")
    content = d.get("content",{})
    active = int(d.get("active", 1))
    if not section_key: return jsonify({"ok":False,"error":"section_key required"})
    try:
        # UPSERT: insert if missing, then update — so hero (and any new section) is always saved
        db.execute(
            "INSERT OR IGNORE INTO home_sections(section_key, section_title, content, sort_order, active)"
            " VALUES(?, ?, '{}', 99, 1)",
            (section_key, section_key.replace('_', ' ').title())
        )
        db.execute(
            "UPDATE home_sections SET content=?, active=? WHERE section_key=?",
            (json.dumps(content), active, section_key)
        )
        db.commit()
        return jsonify({"ok":True})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

@bp.route("/website/homepage/sections/reorder", methods=["POST"])
def homepage_sections_reorder():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    order = d.get("order",[])  # list of section_keys in new order
    try:
        for i, key in enumerate(order):
            db.execute("UPDATE home_sections SET sort_order=? WHERE section_key=?", (i+1, key))
        db.commit()
        return jsonify({"ok":True})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

@bp.route("/website/homepage/sections")
def homepage_sections_list():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    import json
    db = get_db()
    try:
        rows = db.execute("SELECT section_key,section_title,sort_order,active FROM home_sections ORDER BY sort_order").fetchall()
        return jsonify({"ok":True,"sections":[dict(r) for r in rows]})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})


# ── Hero background image upload ──────────────────────────────────
@bp.route("/website/homepage/hero/upload-image", methods=["POST"])
def homepage_hero_upload_image():
    if not session.get("owner_logged_in"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 403
    import os as _os, uuid as _uuid
    try:
        file = request.files.get("image")
        if not file or not file.filename:
            return jsonify({"ok": False, "error": "No file received"})
        ext = _os.path.splitext(file.filename)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
            ext = ".jpg"
        folder = _os.path.join(_os.path.dirname(__file__), "../../static/website/img/hero")
        _os.makedirs(folder, exist_ok=True)
        fname = f"hero_{_uuid.uuid4().hex[:10]}{ext}"
        fpath = _os.path.join(folder, fname)
        file.save(fpath)
        try:
            from app.utils.image_optimize import optimize_image as _oi
            fpath = _oi(fpath)
            fname = _os.path.basename(fpath)
        except Exception:
            pass
        url = "/static/website/img/hero/" + fname
        return jsonify({"ok": True, "url": url})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ── Item Tiles ────────────────────────────────────────────────────
@bp.route("/website/item/tiles/<int:iid>")
def item_tiles_list(iid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    try: rows = db.execute("SELECT * FROM web_item_tiles WHERE item_id=? ORDER BY sort_order",( iid,)).fetchall()
    except: rows = []
    return jsonify({"ok":True,"tiles":[dict(r) for r in rows]})

@bp.route("/website/item/tiles/<int:iid>/save", methods=["POST"])
def item_tiles_save(iid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    tiles = d.get("tiles",[])
    try:
        db.execute("DELETE FROM web_item_tiles WHERE item_id=?", (iid,))
        for i, t in enumerate(tiles):
            db.execute("INSERT INTO web_item_tiles(item_id,emoji,text,sort_order) VALUES(?,?,?,?)",
                       (iid, t.get("emoji",""), t.get("text",""), i))
        db.commit(); return jsonify({"ok":True})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

# ── Item Bullets ──────────────────────────────────────────────────
@bp.route("/website/item/bullets/<int:iid>")
def item_bullets_list(iid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    try: rows = db.execute("SELECT * FROM web_item_bullets WHERE item_id=? ORDER BY sort_order",( iid,)).fetchall()
    except: rows = []
    return jsonify({"ok":True,"bullets":[dict(r) for r in rows]})

@bp.route("/website/item/bullets/<int:iid>/save", methods=["POST"])
def item_bullets_save(iid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    bullets = d.get("bullets",[])
    try:
        db.execute("DELETE FROM web_item_bullets WHERE item_id=?", (iid,))
        for i, b in enumerate(bullets):
            db.execute("INSERT INTO web_item_bullets(item_id,bullet,sort_order) VALUES(?,?,?)",
                       (iid, b, i))
        db.commit(); return jsonify({"ok":True})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

# ── Item FAQ ──────────────────────────────────────────────────────
@bp.route("/website/item/faq/<int:iid>")
def item_faq_list(iid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    try: rows = db.execute("SELECT * FROM web_item_faq WHERE item_id=? ORDER BY sort_order",( iid,)).fetchall()
    except: rows = []
    return jsonify({"ok":True,"faq":[dict(r) for r in rows]})

@bp.route("/website/item/faq/<int:iid>/save", methods=["POST"])
def item_faq_save(iid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    faq = d.get("faq",[])
    try:
        db.execute("DELETE FROM web_item_faq WHERE item_id=?", (iid,))
        for i, f in enumerate(faq):
            db.execute("INSERT INTO web_item_faq(item_id,question,answer,sort_order) VALUES(?,?,?,?)",
                       (iid, f.get("question",""), f.get("answer",""), i))
        db.commit(); return jsonify({"ok":True})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})


# ── Customer Q&A (per-row moderation, not bulk-replace) ──────────────────────
@bp.route("/website/item/questions/<int:iid>")
def item_questions_list(iid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    try:
        rows = db.execute("SELECT * FROM web_item_questions WHERE item_id=? ORDER BY (status='pending') DESC, id DESC", (iid,)).fetchall()
    except: rows = []
    return jsonify({"ok":True,"questions":[dict(r) for r in rows]})

@bp.route("/website/item/questions/<int:qid>/answer", methods=["POST"])
def item_questions_answer(qid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    from datetime import datetime
    db = get_db()
    d = request.get_json() or {}
    answer = (d.get("answer") or "").strip()
    if not answer: return jsonify({"ok":False,"error":"Answer required"})
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        db.execute("UPDATE web_item_questions SET answer=?, status='answered', answered_at=? WHERE id=?", (answer, ts, qid))
        db.commit(); return jsonify({"ok":True})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

@bp.route("/website/item/questions/<int:qid>/delete", methods=["POST"])
def item_questions_delete(qid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}),403
    from database import get_db
    db = get_db()
    try:
        db.execute("DELETE FROM web_item_questions WHERE id=?", (qid,))
        db.commit(); return jsonify({"ok":True})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})


# ── Garment Style Options ──────────────────────────────────────────────────────
@bp.route("/website/services/item/style-options/<int:iid>")
def style_options_list(iid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    try:
        rows = db.execute("SELECT * FROM garment_style_options WHERE item_id=? ORDER BY sort_order,id", (iid,)).fetchall()
        result = []
        for r in rows:
            vals = db.execute("SELECT * FROM garment_style_values WHERE option_id=? ORDER BY sort_order,id", (r["id"],)).fetchall()
            opt = dict(r)
            opt["values"] = [dict(v) for v in vals]
            result.append(opt)
        return jsonify({"ok":True, "options": result})
    except: return jsonify({"ok":True,"options":[]})

@bp.route("/website/services/item/style-options/add/<int:iid>", methods=["POST"])
def style_option_add(iid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    grp = d.get("option_group","").strip()
    lbl = d.get("option_label","").strip()
    req = 1 if d.get("is_required") else 0
    if not grp or not lbl: return jsonify({"ok":False,"error":"Group name and label required"})
    db.execute("INSERT INTO garment_style_options(item_id,option_group,option_label,option_values,is_required) VALUES(?,?,?,?,?)",
               (iid, grp, lbl, "", req))
    db.commit()
    new_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    return jsonify({"ok":True, "id": new_id})

@bp.route("/website/services/item/style-options/update/<int:oid>", methods=["POST"])
def style_option_update(oid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    db.execute("UPDATE garment_style_options SET option_label=?,is_required=? WHERE id=?",
               (d.get("option_label",""), 1 if d.get("is_required") else 0, oid))
    db.commit()
    return jsonify({"ok":True})

@bp.route("/website/services/item/style-options/delete/<int:oid>", methods=["POST"])
def style_option_delete(oid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    db.execute("DELETE FROM garment_style_values WHERE option_id=?", (oid,))
    db.execute("DELETE FROM garment_style_options WHERE id=?", (oid,))
    db.commit()
    return jsonify({"ok":True})

# ── Style Values (options within a group) ──
@bp.route("/website/services/item/style-value/add", methods=["POST"])
def style_value_add():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    oid = d.get("option_id")
    label = (d.get("value_label") or "").strip()
    ai_prompt = (d.get("ai_prompt") or "").strip()
    if not oid or not label: return jsonify({"ok":False,"error":"option_id and value_label required"})
    key = label.lower().replace(" ","_").replace("/","_")
    db.execute("INSERT INTO garment_style_values(option_id,value_label,value_key,image_url,ai_prompt) VALUES(?,?,?,?,?)",
               (oid, label, key, "", ai_prompt))
    db.commit()
    new_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    return jsonify({"ok":True, "id": new_id, "value_key": key})

@bp.route("/website/services/item/style-value/update/<int:vid>", methods=["POST"])
def style_value_update(vid):
    """Edit an existing style value's label and/or its explicit AI instruction text.
    The ai_prompt field is what the paid image-generation backend uses verbatim for
    this option — keeping it accurate here directly controls generation cost/quality,
    so this endpoint exists specifically so admins never have to touch Python code to
    fix or add an AI instruction for a style choice."""
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    sets, params = [], []
    if "value_label" in d:
        label = (d.get("value_label") or "").strip()
        if not label: return jsonify({"ok":False,"error":"value_label cannot be empty"})
        sets.append("value_label=?"); params.append(label)
    if "ai_prompt" in d:
        sets.append("ai_prompt=?"); params.append((d.get("ai_prompt") or "").strip())
    if not sets: return jsonify({"ok":False,"error":"Nothing to update"})
    params.append(vid)
    db.execute(f"UPDATE garment_style_values SET {','.join(sets)} WHERE id=?", params)
    db.commit()
    return jsonify({"ok":True})

@bp.route("/website/services/item/style-value/delete/<int:vid>", methods=["POST"])
def style_value_delete(vid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    db.execute("DELETE FROM garment_style_values WHERE id=?", (vid,))
    db.commit()
    return jsonify({"ok":True})

@bp.route("/website/services/item/style-value/upload-image/<int:vid>", methods=["POST"])
def style_value_upload_image(vid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    import os, uuid
    f = request.files.get("image")
    if not f: return jsonify({"ok":False,"error":"No file"})
    ext = os.path.splitext(f.filename)[1].lower() or ".jpg"
    fname = "styleval_" + str(vid) + "_" + uuid.uuid4().hex[:8] + ext
    upload_dir = os.path.join(os.path.dirname(__file__), "../../static/uploads")
    os.makedirs(upload_dir, exist_ok=True)
    fpath = os.path.join(upload_dir, fname)
    f.save(fpath)
    from app.utils.image_optimize import optimize_image as _oi; fpath = _oi(fpath); fname = os.path.basename(fpath)
    url = "/static/uploads/" + fname
    from database import get_db
    db = get_db()
    db.execute("UPDATE garment_style_values SET image_url=? WHERE id=?", (url, vid))
    db.commit()
    return jsonify({"ok":True, "url": url})

@bp.route("/website/services/item/style-value/set-image-url/<int:vid>", methods=["POST"])
def style_value_set_image_url(vid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    url = (d.get("url") or "").strip()
    if not url: return jsonify({"ok":False,"error":"URL required"})
    db.execute("UPDATE garment_style_values SET image_url=? WHERE id=?", (url, vid))
    db.commit()
    return jsonify({"ok":True, "url": url})


# Default, explicit AI-instruction text per seeded style value — this is what
# actually reaches the paid Replicate generation backend for these values, so
# freshly seeded items work accurately out of the box without needing any
# hardcoded Python keyword match. Admins can edit/override any of these later
# from the style-value editor (see style_value_update route above).
_DEFAULT_STYLE_AI_PROMPTS = {
    "Spread Collar":    "a wide spread collar with the points spread far apart",
    "Mandarin / Chinese": "a short mandarin/Chinese stand-up band collar that sits straight up around the neck with NO fold-down points and NO spread",
    "Band Collar":      "a plain short band collar with no points",
    "Button-Down":      "a button-down collar with small visible buttons fastening each collar point to the shirt body",
    "Full Sleeve":       "full-length long sleeves reaching the wrists, with buttoned cuffs",
    "Half Sleeve":       "short half sleeves ending above the elbow",
    "3/4 Sleeve":        "three-quarter length sleeves ending below the elbow",
    "Standard":          "a standard shirt placket with regular visible buttons down the front",
    "Concealed / Hidden": "a concealed hidden-button placket with no visible buttons, clean minimalist front",
    "French Placket":   "a French placket - a folded fabric front band with visible top-stitching",
    "Dark / Black":      "dark black buttons",
    "White / Pearl":     "white pearl buttons",
    "Gold / Metal":      "gold-toned metal buttons",
    "Round Hem":         "a rounded curved hem at the bottom - the side seams curve gently inward toward the bottom corners instead of forming sharp square corners",
    "Straight Hem":      "a straight horizontal hem at the bottom with sharp square corners, no curve",
    "Side Cut":          "side slit openings at the bottom hem on both side seams",
    "Notch Lapel":       "a notch lapel - the classic V-shaped notch where the collar meets the lapel",
    "Peak Lapel":        "a peak lapel - the lapel points angle upward toward the shoulder, wider and more formal-looking than a notch lapel",
    "Shawl Lapel":       "a shawl lapel - one continuous rounded curve from the collar to the button, with no notch at all",
    "Single Button":     "a single-button jacket front closure",
    "Double Breasted":   "a double-breasted jacket front with two parallel columns of buttons and overlapping front panels",
    "Two Button":         "a two-button jacket front closure",
    "Slim Fit":          "a slim tailored fit, close to the body",
    "Regular Fit":       "a regular comfortable fit, not too tight or loose",
    "Relaxed Fit":       "a relaxed loose fit with extra room through the body",
    "Tapered Fit":       "a tapered fit - fuller through the thigh and narrowing gradually toward the ankle",
    "Flap Pockets":      "flap pockets - pockets with a fabric flap covering the opening",
    "Welt Pockets":      "welt pockets - slim, flapless pockets with a clean fabric-edged slit opening",
    "Patch Pockets":     "patch pockets - pockets sewn on top of the fabric as visible separate patches, casual style",
    "Flat Front":        "a flat front waistband with no pleats, smooth and clean across the front",
    "Single Pleat":      "a single pleat on each side of the front waistband",
    "Double Pleat":      "double pleats on each side of the front waistband",
    "Plain Hem":         "a plain finished hem at the ankle with no cuff or fold",
    "Cuffed Hem":        "a cuffed hem - a folded-back cuff at the ankle opening",
    "Raw Edge":          "a raw unfinished edge hem at the ankle, deliberately frayed/unhemmed look",
    "Classic":           "a classic, timeless design with traditional clean lines",
    "Modern":            "a modern, contemporary design with clean minimal lines",
    "Traditional":       "a traditional design following classic regional tailoring conventions",
}


@bp.route("/website/services/item/seed-default-styles/<int:iid>", methods=["POST"])
def seed_default_styles(iid):
    """Seed standard shirt/garment style options for a given item."""
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    garment_type = d.get("type", "shirt").lower()

    # Default options for shirts/kurta
    if "shirt" in garment_type or "kurta" in garment_type or "pathani" in garment_type:
        groups = [
            ("Collar",       "Collar style choose karo", 0, ["Spread Collar","Mandarin / Chinese","Band Collar","Button-Down"]),
            ("Sleeves",      "Sleeve length",            0, ["Full Sleeve","Half Sleeve","3/4 Sleeve"]),
            ("Front Placket","Placket style",            0, ["Standard","Concealed / Hidden","French Placket"]),
            ("Buttons",      "Button colour / style",    0, ["Dark / Black","White / Pearl","Gold / Metal"]),
            ("Curved Hem",   "Hem / bottom shape",       0, ["Round Hem","Straight Hem","Side Cut"]),
        ]
    elif "suit" in garment_type or "blazer" in garment_type:
        groups = [
            ("Lapel",   "Lapel style",    0, ["Notch Lapel","Peak Lapel","Shawl Lapel"]),
            ("Buttons", "Button count",   0, ["Single Button","Double Breasted","Two Button"]),
            ("Fit",     "Jacket fit",     0, ["Slim Fit","Regular Fit","Relaxed Fit"]),
            ("Pocket",  "Pocket style",   0, ["Flap Pockets","Welt Pockets","Patch Pockets"]),
        ]
    elif "pant" in garment_type or "trouser" in garment_type or "jeans" in garment_type:
        groups = [
            ("Fit",     "Pant fit",    0, ["Slim Fit","Regular Fit","Relaxed Fit","Tapered Fit"]),
            ("Waist",   "Waist style",    0, ["Flat Front","Single Pleat","Double Pleat"]),
            ("Hem",     "Bottom hem",     0, ["Plain Hem","Cuffed Hem","Raw Edge"]),
        ]
    else:
        groups = [
            ("Style",   "Style preference", 0, ["Classic","Modern","Traditional"]),
            ("Fit",     "Garment fit",       0, ["Slim Fit","Regular Fit","Relaxed Fit"]),
        ]

    try:
        # Remove existing options for this item first (optional - only if requested)
        if d.get("replace"):
            existing = db.execute("SELECT id FROM garment_style_options WHERE item_id=?", (iid,)).fetchall()
            for row in existing:
                db.execute("DELETE FROM garment_style_values WHERE option_id=?", (row["id"],))
            db.execute("DELETE FROM garment_style_options WHERE item_id=?", (iid,))

        added = 0
        for (grp_name, grp_label, is_req, values) in groups:
            # Skip if group already exists
            existing_grp = db.execute(
                "SELECT id FROM garment_style_options WHERE item_id=? AND option_group=?",
                (iid, grp_name)
            ).fetchone()
            if existing_grp:
                grp_id = existing_grp["id"]
            else:
                db.execute(
                    "INSERT INTO garment_style_options(item_id,option_group,option_label,option_values,is_required) VALUES(?,?,?,?,?)",
                    (iid, grp_name, grp_label, "", is_req)
                )
                db.commit()
                grp_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
                added += 1

            for val in values:
                # Skip if value already exists
                exists = db.execute(
                    "SELECT 1 FROM garment_style_values WHERE option_id=? AND value_label=?",
                    (grp_id, val)
                ).fetchone()
                if not exists:
                    key = val.lower().replace(" ","_").replace("/","_").replace("-","_")
                    default_ai = _DEFAULT_STYLE_AI_PROMPTS.get(val, "")
                    db.execute(
                        "INSERT INTO garment_style_values(option_id,value_label,value_key,image_url,ai_prompt) VALUES(?,?,?,?,?)",
                        (grp_id, val, key, "", default_ai)
                    )
        db.commit()
        return jsonify({"ok": True, "message": f"Style options seeded successfully ({added} new groups added)"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})



@bp.route("/website/services/item/name/<int:iid>", methods=["POST"])
def website_services_item_name(iid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    name = d.get("name","").strip()
    if not name: return jsonify({"ok":False,"error":"Name required"})
    db.execute("UPDATE web_service_items SET name=? WHERE id=?", (name, iid))
    db.commit()
    return jsonify({"ok":True})

@bp.route("/website/services/item/desc/<int:iid>", methods=["POST"])
def website_services_item_desc(iid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    try:
        db.execute("UPDATE web_service_items SET description=?, long_desc=? WHERE id=?",
            (d.get("description",""), d.get("long_desc",""), iid))
    except:
        pass
    db.commit()
    return jsonify({"ok":True})

@bp.route("/website/reviews/add/<int:item_id>", methods=["POST"])
def website_review_add(item_id):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    import datetime
    db = get_db()
    d = request.get_json() or {}
    name = d.get("reviewer_name","").strip()
    text = d.get("review_text","").strip()
    rating = int(d.get("rating",5))
    if not name: return jsonify({"ok":False,"error":"Name required"})
    db.execute("INSERT INTO web_item_reviews(item_id,reviewer_name,review_text,rating,created_at) VALUES(?,?,?,?,?)",
        (item_id, name, text, rating, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
    db.commit()
    return jsonify({"ok":True})

@bp.route("/website/reviews/delete/<int:rid>", methods=["POST"])
def website_review_delete(rid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    db.execute("DELETE FROM web_item_reviews WHERE id=?", (rid,))
    db.commit()
    return jsonify({"ok":True})

@bp.route("/website/reviews/list/<int:item_id>")
def website_review_list(item_id):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    try:
        rows = db.execute("SELECT * FROM web_item_reviews WHERE item_id=? ORDER BY id DESC", (item_id,)).fetchall()
        return jsonify({"ok":True, "reviews":[dict(r) for r in rows]})
    except: return jsonify({"ok":True,"reviews":[]})

@bp.route("/website/services/item/upload-image/<int:iid>", methods=["POST"])
def website_services_item_upload(iid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    import os, uuid
    from database import get_db
    f = request.files.get("image")
    if not f: return jsonify({"ok":False,"error":"No file"})
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ['.jpg','.jpeg','.png','.webp']: return jsonify({"ok":False,"error":"Only JPG/PNG/WEBP allowed"})
    fname = f"svc_{iid}_{uuid.uuid4().hex[:8]}{ext}"
    save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static","website","img","services")
    os.makedirs(save_dir, exist_ok=True)
    _sp = os.path.join(save_dir, fname); f.save(_sp)
    from app.utils.image_optimize import optimize_image as _oi; _sp = _oi(_sp); fname = os.path.basename(_sp)
    img_url = "/static/website/img/services/" + fname
    db = get_db()
    db.execute("UPDATE web_service_items SET image_url=? WHERE id=?", (img_url, iid))
    # Also replace in web_item_media so get_item_media() picks it up on frontend pages
    db.execute("DELETE FROM web_item_media WHERE item_id=? AND media_type='image'", (iid,))
    db.execute("INSERT INTO web_item_media(item_id, media_type, url, sort_order) VALUES(?,?,?,0)",
               (iid, "image", img_url))
    db.commit()
    return jsonify({"ok":True, "url": img_url})


# ── Fabric swatch image upload for a service item ─────────────────────────────
@bp.route("/website/services/item/upload-fabric-image/<int:iid>", methods=["POST"])
def website_services_item_upload_fabric(iid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    import os, uuid
    from database import get_db
    f = request.files.get("image")
    if not f: return jsonify({"ok":False,"error":"No file"})
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ['.jpg','.jpeg','.png','.webp']: return jsonify({"ok":False,"error":"Only JPG/PNG/WEBP allowed"})
    fname = f"fabric_{iid}_{uuid.uuid4().hex[:8]}{ext}"
    save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static","website","img","services")
    os.makedirs(save_dir, exist_ok=True)
    _sp = os.path.join(save_dir, fname); f.save(_sp)
    from app.utils.image_optimize import optimize_image as _oi; _sp = _oi(_sp); fname = os.path.basename(_sp)
    img_url = "/static/website/img/services/" + fname
    db = get_db()
    try:
        db.execute("UPDATE web_service_items SET fabric_image_url=? WHERE id=?", (img_url, iid))
    except Exception:
        db.execute("ALTER TABLE web_service_items ADD COLUMN fabric_image_url TEXT DEFAULT ''")
        db.execute("UPDATE web_service_items SET fabric_image_url=? WHERE id=?", (img_url, iid))
    db.commit()
    return jsonify({"ok":True, "url": img_url})


# ── Save fabric_image_url directly (URL paste) ───────────────────────────────
@bp.route("/website/services/item/fabric-url/<int:iid>", methods=["POST"])
def website_services_item_fabric_url(iid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    d = request.get_json(force=True, silent=True) or {}
    url = d.get("fabric_image_url","").strip()
    db = get_db()
    try:
        db.execute("UPDATE web_service_items SET fabric_image_url=? WHERE id=?", (url, iid))
    except Exception:
        db.execute("ALTER TABLE web_service_items ADD COLUMN fabric_image_url TEXT DEFAULT ''")
        db.execute("UPDATE web_service_items SET fabric_image_url=? WHERE id=?", (url, iid))
    db.commit()
    return jsonify({"ok":True})


# ── Settings All (for JS fetch) ───────────────────────────────────────────────
@bp.route("/website/settings/all")
def website_settings_all():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    return jsonify({"ok":True, "settings":{r["key"]:r["value"] for r in rows}})

# ── Story Timeline ────────────────────────────────────────────────────────────
@bp.route("/website/story/timeline")
def story_timeline_list():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    try:
        entries = db.execute("SELECT * FROM web_story_timeline ORDER BY sort_order, year").fetchall()
        return jsonify({"ok":True, "entries":[dict(e) for e in entries]})
    except: return jsonify({"ok":True, "entries":[]})

@bp.route("/website/story/timeline/add", methods=["POST"])
def story_timeline_add():
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    try:
        db.execute("INSERT INTO web_story_timeline(year,title,body,sort_order) VALUES(?,?,?,(SELECT COALESCE(MAX(sort_order),0)+1 FROM web_story_timeline))",
            (d.get("year",""), d.get("title",""), d.get("body","")))
        db.commit()
        return jsonify({"ok":True})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

@bp.route("/website/story/timeline/delete/<int:tid>", methods=["POST"])
def story_timeline_delete(tid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    db.execute("DELETE FROM web_story_timeline WHERE id=?", (tid,))
    db.commit()
    return jsonify({"ok":True})

@bp.route("/website/story/timeline/update/<int:tid>", methods=["POST"])
def story_timeline_update(tid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    db.execute("UPDATE web_story_timeline SET year=?,title=?,body=? WHERE id=?",
        (d.get("year",""), d.get("title",""), d.get("body",""), tid))
    db.commit()
    return jsonify({"ok":True})

@bp.route("/website/services/item/media/<int:iid>", methods=["POST"])
def website_services_item_media(iid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    if "image_url" in d:
        db.execute("UPDATE web_service_items SET image_url=? WHERE id=?", (d["image_url"], iid))
    if "video_url" in d:
        try: db.execute("UPDATE web_service_items SET video_url=? WHERE id=?", (d["video_url"], iid))
        except: db.execute("ALTER TABLE web_service_items ADD COLUMN video_url TEXT DEFAULT ''")
        db.execute("UPDATE web_service_items SET video_url=? WHERE id=?", (d["video_url"], iid))
    db.commit()
    return jsonify({"ok":True})

@bp.route("/website/services/item/upload-video/<int:iid>", methods=["POST"])
def website_services_item_upload_video(iid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    import os, uuid
    from database import get_db
    f = request.files.get("video")
    if not f: return jsonify({"ok":False,"error":"No file"})
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ['.mp4','.webm','.mov']: return jsonify({"ok":False,"error":"Only MP4/WEBM/MOV allowed"})
    fname = f"svc_{iid}_{uuid.uuid4().hex[:8]}{ext}"
    save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static","website","img","services")
    os.makedirs(save_dir, exist_ok=True)
    f.save(os.path.join(save_dir, fname))
    vid_url = f"/static/website/img/services/{fname}"
    db = get_db()
    try: db.execute("UPDATE web_service_items SET video_url=? WHERE id=?", (vid_url, iid))
    except:
        db.execute("ALTER TABLE web_service_items ADD COLUMN video_url TEXT DEFAULT ''")
        db.execute("UPDATE web_service_items SET video_url=? WHERE id=?", (vid_url, iid))
    db.commit()
    return jsonify({"ok":True, "url": vid_url})

# ── Multi-media per item ──────────────────────────────────────────────────────
@bp.route("/website/services/item/media/list/<int:iid>")
def item_media_list(iid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    try:
        rows = db.execute("SELECT * FROM web_item_media WHERE item_id=? ORDER BY sort_order",(iid,)).fetchall()
        # Also include legacy image_url/video_url
        item = db.execute("SELECT image_url, video_url FROM web_service_items WHERE id=?",(iid,)).fetchone()
        media = [dict(r) for r in rows]
        # Add legacy if not in media table
        if item and item["image_url"] and not any(m["url"]==item["image_url"] for m in media):
            media.insert(0,{"id":-1,"item_id":iid,"media_type":"image","url":item["image_url"],"sort_order":-1})
        try:
            if item and item["video_url"] and not any(m["url"]==item["video_url"] for m in media):
                media.append({"id":-2,"item_id":iid,"media_type":"video","url":item["video_url"],"sort_order":999})
        except: pass
        return jsonify({"ok":True,"media":media})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

@bp.route("/website/services/item/media/add/<int:iid>", methods=["POST"])
def item_media_add(iid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    d = request.get_json() or {}
    url = d.get("url","").strip()
    mtype = d.get("type","image")
    if not url: return jsonify({"ok":False,"error":"URL required"})
    db.execute("INSERT INTO web_item_media(item_id,media_type,url,sort_order) VALUES(?,?,?,(SELECT COALESCE(MAX(sort_order),0)+1 FROM web_item_media WHERE item_id=?))",(iid,mtype,url,iid))
    # Also update primary image_url if first image
    if mtype == "image":
        existing = db.execute("SELECT id FROM web_item_media WHERE item_id=? AND media_type='image' ORDER BY sort_order",(iid,)).fetchall()
        if len(existing)<=1:
            db.execute("UPDATE web_service_items SET image_url=? WHERE id=?",(url,iid))
    db.commit()
    return jsonify({"ok":True})

@bp.route("/website/services/item/media/delete/<int:mid>", methods=["POST"])
def item_media_delete(mid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    from database import get_db
    db = get_db()
    db.execute("DELETE FROM web_item_media WHERE id=?",(mid,))
    db.commit()
    return jsonify({"ok":True})

@bp.route("/website/services/item/media/upload/<int:iid>", methods=["POST"])
def item_media_upload(iid):
    if not session.get("owner_logged_in"): return jsonify({"ok":False}), 403
    import os, uuid
    from database import get_db
    f = request.files.get("file")
    if not f: return jsonify({"ok":False,"error":"No file"})
    ext = os.path.splitext(f.filename)[1].lower()
    is_video = ext in ['.mp4','.webm','.mov']
    is_image = ext in ['.jpg','.jpeg','.png','.webp']
    if not is_video and not is_image: return jsonify({"ok":False,"error":"Unsupported file type"})
    fname = f"svc_{iid}_{uuid.uuid4().hex[:8]}{ext}"
    save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static","website","img","services")
    os.makedirs(save_dir, exist_ok=True)
    _sp = os.path.join(save_dir, fname); f.save(_sp)
    if is_image:
        from app.utils.image_optimize import optimize_image as _oi; _sp = _oi(_sp); fname = os.path.basename(_sp)
    url = "/static/website/img/services/" + fname
    mtype = "video" if is_video else "image"
    db = get_db()
    db.execute("INSERT INTO web_item_media(item_id,media_type,url,sort_order) VALUES(?,?,?,(SELECT COALESCE(MAX(sort_order),0)+1 FROM web_item_media WHERE item_id=?))",(iid,mtype,url,iid))
    if mtype=="image":
        existing = db.execute("SELECT COUNT(*) as c FROM web_item_media WHERE item_id=? AND media_type='image'",(iid,)).fetchone()["c"]
        if existing<=1: db.execute("UPDATE web_service_items SET image_url=? WHERE id=?",(url,iid))
    db.commit()
    return jsonify({"ok":True,"url":url,"type":mtype})

# ── Commission Page Admin Routes ──────────────────────────────────────────────

@bp.route("/website/commission/settings")
def commission_settings_get():
    if not session.get("owner_logged_in"): return jsonify({"ok": False}), 403
    from database import get_db
    db = get_db()
    rows = db.execute("SELECT key, value FROM settings WHERE key LIKE 'commission_%'").fetchall()
    settings = {r["key"]: r["value"] for r in rows}
    return jsonify({"ok": True, "settings": settings})


@bp.route("/website/commission/upload-header-image", methods=["POST"])
def commission_upload_header_image():
    if not session.get("owner_logged_in"): return jsonify({"ok": False}), 403
    import os, uuid
    from database import get_db
    f = request.files.get("image")
    if not f: return jsonify({"ok": False, "error": "No file"})
    ext = os.path.splitext(f.filename)[1].lower() or ".jpg"
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]: return jsonify({"ok": False, "error": "Only JPG/PNG/WebP allowed"})
    fname = f"commission_header_{uuid.uuid4().hex[:10]}{ext}"
    save_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "static", "website", "img"
    )
    os.makedirs(save_dir, exist_ok=True)
    _cp = os.path.join(save_dir, fname); f.save(_cp)
    from app.utils.image_optimize import optimize_image as _oi; _cp = _oi(_cp); fname = os.path.basename(_cp)
    url = "/static/website/img/" + fname
    # Save to settings
    db = get_db()
    if db.execute("SELECT 1 FROM settings WHERE key='commission_header_image'").fetchone():
        db.execute("UPDATE settings SET value=? WHERE key='commission_header_image'", (url,))
    else:
        db.execute("INSERT INTO settings(key,value) VALUES('commission_header_image',?)", (url,))
    db.commit()
    return jsonify({"ok": True, "url": url})
