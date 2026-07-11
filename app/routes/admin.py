from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models import Fabric, Order, Customer
from datetime import datetime, date

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/api/admin/orders')
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    today  = date.today().isoformat()
    result = []
    for o in orders:
        cust = Customer.query.get(o.customer_id)
        result.append({
            'public_id':      o.public_id,
            'customer_name':  cust.name if cust else 'Unknown',
            'customer_phone': cust.phone if cust else '',
            'garment_type':   o.garment_type,
            'measure_method': o.measurement.method if o.measurement else 'size',
            'delivery_type':  o.delivery_type,
            'total_amount':   o.total_amount,
            'advance_amount': o.advance_amount,
            'status':         o.status,
            'payment_status': o.payment_status,
            'created_at':     o.created_at.isoformat(),
        })
    today_count   = sum(1 for o in orders if o.created_at.date().isoformat() == today)
    pending_count = sum(1 for o in orders if o.status in ('received','confirmed'))
    return jsonify({'orders': result, 'total': len(result), 'today': today_count, 'pending': pending_count})

@admin_bp.route('/api/admin/fabrics/add', methods=['POST'])
def admin_fab_add():
    d = request.json or {}
    f = Fabric(
        name=d.get('name',''), price_per_metre=float(d.get('price_per_metre',0)),
        stock_metres=float(d.get('stock_metres',0)), image_url=d.get('image_url',''),
        active=True, sort_order=Fabric.query.count()+1,
    )
    db.session.add(f); db.session.commit()
    return jsonify({'success': True, 'id': f.id})

@admin_bp.route('/api/admin/fabrics/delete/<int:fid>', methods=['POST'])
def admin_fab_delete(fid):
    f = Fabric.query.get(fid)
    if f: f.active = False; db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/api/admin/prices/save', methods=['POST'])
def admin_prices_save():
    # Store prices in a simple JSON file for now
    import json, os
    prices = request.json or {}
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'website_prices.json')
    with open(path, 'w') as f: json.dump(prices, f)
    return jsonify({'success': True})

@admin_bp.route('/api/admin/settings/save', methods=['POST'])
def admin_settings_save():
    import json, os
    d = request.json or {}
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'website_settings.json')
    settings = {}
    if os.path.exists(path):
        with open(path) as f: settings = json.load(f)
    settings[d.get('key','')] = d.get('value','')
    with open(path, 'w') as f: json.dump(settings, f)
    return jsonify({'success': True})
