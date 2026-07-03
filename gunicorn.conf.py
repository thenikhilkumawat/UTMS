import os

bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
workers = 1          # 1 worker saves RAM on free tier (1GB only)
threads = 4          # 4 threads handles concurrent requests
worker_class = "gthread"
timeout = 120
keepalive = 5
max_requests = 1000  # Restart worker after 1000 requests (prevents memory leaks)
max_requests_jitter = 100
graceful_timeout = 30
worker_tmp_dir = "/dev/shm"  # Use RAM for temp files (faster)
preload_app = True   # Load app once, share between threads (saves RAM)
