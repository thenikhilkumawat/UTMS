#!/usr/bin/env python3
"""
Repair order_images DB rows that still point to a file which no longer
exists (because the WebP conversion moved the original to backup) but a
.webp version of the SAME image exists at the same location. Handles both
plain "/static/order_images/CODE/file.jpg" paths AND the QR-upload
"temp:CODE:/static/order_images/CODE/file.jpg" format.

Nothing is deleted. This only UPDATES database text pointing at files that
are already safely on disk as .webp.

USAGE (run from the UTMS project root):
  python3 scripts/repair_webp_links.py
"""
import os, sys

sys.path.insert(0, os.getcwd())
try:
    from database import get_db
except ImportError:
    print("Run this from the UTMS project root folder (where database.py lives).")
    sys.exit(1)

IMG_BASE = os.path.join(os.getcwd(), "static", "order_images")


def main():
    conn = get_db()
    rows = conn.execute("SELECT id, file_path FROM order_images").fetchall()
    fixed = 0
    already_ok = 0
    still_missing = []

    for row in rows:
        fp = row["file_path"]
        if not fp:
            continue

        is_temp = fp.startswith("temp:")
        if is_temp:
            parts = fp.split(":", 2)
            if len(parts) != 3:
                continue
            _, code, url = parts
        else:
            url = fp
            code = None

        if not url.startswith("/static/order_images/"):
            continue

        rel = url[len("/static/order_images/"):]
        full_path = os.path.join(IMG_BASE, rel)

        if os.path.exists(full_path):
            already_ok += 1
            continue

        base, ext = os.path.splitext(full_path)
        webp_path = base + ".webp"
        if os.path.exists(webp_path):
            new_rel = os.path.splitext(rel)[0] + ".webp"
            new_url = "/static/order_images/" + new_rel
            new_fp = f"temp:{code}:{new_url}" if is_temp else new_url
            conn.execute("UPDATE order_images SET file_path=? WHERE id=?", (new_fp, row["id"]))
            conn.commit()
            fixed += 1
            print(f"✅ Fixed id={row['id']}: {fp}\n         → {new_fp}")
        else:
            still_missing.append((row["id"], fp))
            print(f"❌ No file AND no webp found for id={row['id']}: {fp}")

    conn.close()
    print(f"\n=== DONE ===")
    print(f"Already fine: {already_ok}, Fixed: {fixed}, Still broken (needs manual look): {len(still_missing)}")
    if still_missing:
        print("\nStill-broken rows:")
        for rid, fp in still_missing:
            print(f"  id={rid}: {fp}")


if __name__ == "__main__":
    main()
