"""
python fix_owner.py
───────────────────
1. Truncates owner.py at line 4513  (removes orphaned duplicate block)
2. Patches every image upload in owner.py + features.py to auto-convert
   uploaded images to AVIF/WebP using app/utils/image_optimize.py
"""
import os, sys, shutil
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))

def fix(relpath, patches, truncate_at=None):
    path = os.path.join(BASE, relpath)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        src = f.read()
    lines = src.splitlines(keepends=True)
    orig_len = len(lines)

    if truncate_at:
        lines = lines[:truncate_at]
        print(f"  Truncated {relpath}: {orig_len} → {len(lines)} lines")

    src = "".join(lines)
    applied = 0
    for old, new in patches:
        if old in src:
            src = src.replace(old, new, 1)
            applied += 1
        else:
            print(f"  WARNING: patch not found in {relpath}:\n    {repr(old[:80])}")

    print(f"  Applied {applied}/{len(patches)} patches to {relpath}")

    try:
        compile(src, path, "exec")
        print(f"  ✓ Compiles OK")
    except SyntaxError as e:
        print(f"  ✗ SyntaxError at line {e.lineno}: {e.msg}")
        print(f"    text: {repr(e.text)}")
        sys.exit(1)

    bak = path + f".bak_{datetime.now().strftime('%H%M%S')}"
    shutil.copy2(path, bak)
    with open(path, "w", encoding="utf-8", errors="replace", newline="\n") as f:
        f.write(src)
    print(f"  Saved (backup: {os.path.basename(bak)})")
    return True

OI = "from app.utils.image_optimize import optimize_image as _oi"

# ─── owner.py patches ─────────────────────────────────────────────────────────
OWNER_PATCHES = [

    # 1. Gallery local upload (line 1499)
    (
        '            fname = f"gal_{type_id}_{int(_time.time())}{ext}"\n'
        '            file.save(_os.path.join(folder, fname))\n',
        '            fname = f"gal_{type_id}_{int(_time.time())}{ext}"\n'
        '            _gp = _os.path.join(folder, fname); file.save(_gp)\n'
        '            ' + OI + '; _gp = _oi(_gp); fname = _os.path.basename(_gp)\n'
    ),

    # 2. Fabric upload for existing fabric (line 2962)
    (
        '    f_file.save(os.path.join(folder, fname))\n'
        '    img_url = f"/static/website/img/fabrics/{fname}"\n'
        '    db = get_db()\n'
        '    db.execute("UPDATE web_fabrics SET image_url=? WHERE id=?", (img_url, fid))',
        '    _fp = os.path.join(folder, fname); f_file.save(_fp)\n'
        '    ' + OI + '; _fp = _oi(_fp); fname = os.path.basename(_fp)\n'
        '    img_url = "/static/website/img/fabrics/" + fname\n'
        '    db = get_db()\n'
        '    db.execute("UPDATE web_fabrics SET image_url=? WHERE id=?", (img_url, fid))'
    ),

    # 3. Fabric temp upload (line 2985)
    (
        '    f_file.save(os.path.join(folder, fname))\n'
        '    img_url = f"/static/website/img/fabrics/{fname}"\n'
        '    return jsonify({"ok":True, "url": img_url})',
        '    _fp = os.path.join(folder, fname); f_file.save(_fp)\n'
        '    ' + OI + '; _fp = _oi(_fp); fname = os.path.basename(_fp)\n'
        '    img_url = "/static/website/img/fabrics/" + fname\n'
        '    return jsonify({"ok":True, "url": img_url})'
    ),

    # 4. Fabric media upload (line 3019)
    (
        '    f_file.save(os.path.join(folder, fname))\n'
        '    img_url = f"/static/website/img/fabrics/{fname}"\n'
        '    db.execute("INSERT INTO web_fabric_media',
        '    _fp = os.path.join(folder, fname); f_file.save(_fp)\n'
        '    ' + OI + '; _fp = _oi(_fp); fname = os.path.basename(_fp)\n'
        '    img_url = "/static/website/img/fabrics/" + fname\n'
        '    db.execute("INSERT INTO web_fabric_media'
    ),

    # 5. Style-value image upload (line 4013)
    (
        '    fpath = os.path.join(upload_dir, fname)\n'
        '    f.save(fpath)\n'
        '    url = "/static/uploads/" + fname',
        '    fpath = os.path.join(upload_dir, fname)\n'
        '    f.save(fpath)\n'
        '    ' + OI + '; fpath = _oi(fpath); fname = os.path.basename(fpath)\n'
        '    url = "/static/uploads/" + fname'
    ),

    # 6. Service item main image upload (line 4237)
    (
        '    fname = f"svc_{iid}_{uuid.uuid4().hex[:8]}{ext}"\n'
        '    save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static","website","img","services")\n'
        '    os.makedirs(save_dir, exist_ok=True)\n'
        '    f.save(os.path.join(save_dir, fname))\n'
        '    img_url = f"/static/website/img/services/{fname}"\n'
        '    db = get_db()\n'
        '    db.execute("UPDATE web_service_items SET image_url=? WHERE id=?", (img_url, iid))',
        '    fname = f"svc_{iid}_{uuid.uuid4().hex[:8]}{ext}"\n'
        '    save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static","website","img","services")\n'
        '    os.makedirs(save_dir, exist_ok=True)\n'
        '    _sp = os.path.join(save_dir, fname); f.save(_sp)\n'
        '    ' + OI + '; _sp = _oi(_sp); fname = os.path.basename(_sp)\n'
        '    img_url = "/static/website/img/services/" + fname\n'
        '    db = get_db()\n'
        '    db.execute("UPDATE web_service_items SET image_url=? WHERE id=?", (img_url, iid))'
    ),

    # 7. Service item fabric/swatch image upload (line 4262)
    (
        '    fname = f"fabric_{iid}_{uuid.uuid4().hex[:8]}{ext}"\n'
        '    save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static","website","img","services")\n'
        '    os.makedirs(save_dir, exist_ok=True)\n'
        '    f.save(os.path.join(save_dir, fname))\n'
        '    img_url = f"/static/website/img/services/{fname}"',
        '    fname = f"fabric_{iid}_{uuid.uuid4().hex[:8]}{ext}"\n'
        '    save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static","website","img","services")\n'
        '    os.makedirs(save_dir, exist_ok=True)\n'
        '    _sp = os.path.join(save_dir, fname); f.save(_sp)\n'
        '    ' + OI + '; _sp = _oi(_sp); fname = os.path.basename(_sp)\n'
        '    img_url = "/static/website/img/services/" + fname'
    ),

    # 8. Service item media upload — image/video (line 4443), only convert images
    (
        '    fname = f"svc_{iid}_{uuid.uuid4().hex[:8]}{ext}"\n'
        '    save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static","website","img","services")\n'
        '    os.makedirs(save_dir, exist_ok=True)\n'
        '    f.save(os.path.join(save_dir, fname))\n'
        '    url = f"/static/website/img/services/{fname}"\n'
        '    mtype = "video" if is_video else "image"',
        '    fname = f"svc_{iid}_{uuid.uuid4().hex[:8]}{ext}"\n'
        '    save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static","website","img","services")\n'
        '    os.makedirs(save_dir, exist_ok=True)\n'
        '    _sp = os.path.join(save_dir, fname); f.save(_sp)\n'
        '    if is_image:\n'
        '        ' + OI + '; _sp = _oi(_sp); fname = os.path.basename(_sp)\n'
        '    url = "/static/website/img/services/" + fname\n'
        '    mtype = "video" if is_video else "image"'
    ),

    # 9. Commission header image upload (line 4481)
    (
        '    f.save(os.path.join(save_dir, fname))\n'
        '    url = f"/static/website/img/{fname}"\n'
        '    # Save to settings',
        '    _cp = os.path.join(save_dir, fname); f.save(_cp)\n'
        '    ' + OI + '; _cp = _oi(_cp); fname = os.path.basename(_cp)\n'
        '    url = "/static/website/img/" + fname\n'
        '    # Save to settings'
    ),

    # 10. Hero image upload (line 4511)
    (
        '    f.save(os.path.join(save_dir, fname))\n'
        '    url = f"/static/website/img/{fname}"\n'
        '    return jsonify({"ok": True, "url": url})',
        '    _hp = os.path.join(save_dir, fname); f.save(_hp)\n'
        '    ' + OI + '; _hp = _oi(_hp); fname = os.path.basename(_hp)\n'
        '    url = "/static/website/img/" + fname\n'
        '    return jsonify({"ok": True, "url": url})'
    ),
]

# ─── features.py patches ──────────────────────────────────────────────────────
FEATURES_PATCHES = [
    # Inspo image upload (around line 138)
    (
        '    file_obj.save(os.path.join(save_dir, fname))\n'
        '    return f"/static/website/img/inspo/{fname}"',
        '    _ip = os.path.join(save_dir, fname); file_obj.save(_ip)\n'
        '    ' + OI + '; _ip = _oi(_ip); fname = os.path.basename(_ip)\n'
        '    return "/static/website/img/inspo/" + fname'
    ),
]

print("=== Patching owner.py ===")
fix("app/routes/owner.py", OWNER_PATCHES, truncate_at=4513)

print("\n=== Patching features.py ===")
fix("app/routes/features.py", FEATURES_PATCHES)

# Clear pycache
for d in ["app/routes/__pycache__", "app/utils/__pycache__", "app/__pycache__"]:
    p = os.path.join(BASE, d)
    if os.path.isdir(p):
        shutil.rmtree(p, ignore_errors=True)
print("\n✓ __pycache__ cleared")
print("\n✅ All done! Run:  python run.py")
