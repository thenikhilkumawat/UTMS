#!/usr/bin/env python3
"""
Convert order_images (JPEG/PNG) to WebP — saves storage, faster page loads.

SAFE BY DESIGN:
  - Originals are NEVER deleted — moved to a backup folder instead.
  - The new .webp file is opened + verified BEFORE the DB is touched.
  - Run with --dry-run first to see space savings WITHOUT changing anything.

USAGE (run this FROM the UTMS project root, e.g. /home/ubuntu/UTMS):
  python3 convert_images_webp.py --dry-run     # preview only, no changes
  python3 convert_images_webp.py               # actually convert

Requires Pillow: pip3 install Pillow --break-system-packages
"""
import os, sys, argparse

try:
    from PIL import Image
except ImportError:
    print("Pillow not installed. Run: pip3 install Pillow --break-system-packages")
    sys.exit(1)

sys.path.insert(0, os.getcwd())
try:
    from database import get_db
except ImportError:
    print("Could not import database.py — run this script FROM the UTMS project root folder.")
    sys.exit(1)

IMG_BASE    = os.path.join(os.getcwd(), "static", "order_images")
BACKUP_BASE = os.path.join(os.getcwd(), "static", "order_images_originals_backup")
QUALITY     = 85
EXTS        = (".jpg", ".jpeg", ".png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Preview only, don't change anything")
    ap.add_argument("--limit", type=int, default=0, help="Only process first N images (for testing)")
    args = ap.parse_args()

    if not os.path.isdir(IMG_BASE):
        print(f"❌ Folder not found: {IMG_BASE}\nRun this script from the UTMS project root (where static/ lives).")
        sys.exit(1)

    conn = None if args.dry_run else get_db()
    total_before = total_after = converted = skipped = 0
    errors = []

    for order_code in sorted(os.listdir(IMG_BASE)):
        folder = os.path.join(IMG_BASE, order_code)
        if not os.path.isdir(folder):
            continue
        for fname in sorted(os.listdir(folder)):
            if not fname.lower().endswith(EXTS):
                continue
            if args.limit and converted >= args.limit:
                break

            old_path = os.path.join(folder, fname)
            new_fname = os.path.splitext(fname)[0] + ".webp"
            new_path = os.path.join(folder, new_fname)

            if os.path.exists(new_path):
                skipped += 1
                continue

            try:
                size_before = os.path.getsize(old_path)

                if args.dry_run:
                    # Estimate only — actually encode to a temp buffer to measure real savings
                    img = Image.open(old_path)
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    import io
                    buf = io.BytesIO()
                    img.save(buf, "WEBP", quality=QUALITY)
                    size_after = buf.tell()
                    total_before += size_before
                    total_after += size_after
                    converted += 1
                    print(f"[DRY-RUN] {order_code}/{fname}  {size_before//1024}KB → ~{size_after//1024}KB")
                    continue

                img = Image.open(old_path)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(new_path, "WEBP", quality=QUALITY)

                # Verify the new file is genuinely valid before touching anything else
                Image.open(new_path).verify()
                size_after = os.path.getsize(new_path)

                # Back up original — never deleted
                backup_folder = os.path.join(BACKUP_BASE, order_code)
                os.makedirs(backup_folder, exist_ok=True)
                os.rename(old_path, os.path.join(backup_folder, fname))

                # Update DB reference (only rows that still point to the old file)
                old_url = f"/static/order_images/{order_code}/{fname}"
                new_url = f"/static/order_images/{order_code}/{new_fname}"
                # Handle BOTH plain paths and QR-upload "temp:CODE:path" rows
                conn.execute("UPDATE order_images SET file_path=? WHERE file_path=?", (new_url, old_url))
                conn.execute(
                    "UPDATE order_images SET file_path=? WHERE file_path=?",
                    (f"temp:{order_code}:{new_url}", f"temp:{order_code}:{old_url}")
                )
                conn.commit()

                total_before += size_before
                total_after += size_after
                converted += 1
                print(f"✅ {order_code}/{fname} → {new_fname}  ({size_before//1024}KB → {size_after//1024}KB)")

            except Exception as e:
                errors.append(f"{order_code}/{fname}: {e}")
                print(f"❌ {order_code}/{fname}: {e}")

    if conn:
        conn.close()

    print("\n=== DONE ===")
    print(f"{'Would convert' if args.dry_run else 'Converted'}: {converted}, Already done/skipped: {skipped}, Errors: {len(errors)}")
    if total_before:
        print(f"Size before: {total_before/1024/1024:.1f} MB")
        print(f"Size after:  {total_after/1024/1024:.1f} MB")
        print(f"Saved:       {(1 - total_after/total_before)*100:.1f}%")
    if errors:
        print("\nErrors:")
        for e in errors:
            print(" -", e)


if __name__ == "__main__":
    main()
