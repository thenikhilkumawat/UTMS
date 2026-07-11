#!/usr/bin/env python3
"""
BACKUP SCRIPT for Uttam Tailors
Run this anytime to backup your data.
Your data is NEVER deleted when you update the app.
Just replace all files EXCEPT uttam.db
"""
import shutil, os
from datetime import datetime

src = os.path.join(os.path.dirname(__file__), "uttam.db")
if not os.path.exists(src):
    print("No database found yet.")
else:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(os.path.dirname(__file__), f"uttam_backup_{ts}.db")
    shutil.copy2(src, dst)
    print(f"✅ Backup saved: {dst}")
    print(f"   Size: {os.path.getsize(dst)/1024:.1f} KB")
    print()
    print("TO UPDATE THE APP WITHOUT LOSING DATA:")
    print("1. Run this backup script first")
    print("2. Extract the new zip")
    print("3. Copy YOUR uttam.db back into the new folder")
    print("   (overwrite the empty one)")
    print("4. Run python run.py")
