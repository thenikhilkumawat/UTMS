# Gunicorn configuration for Render free tier
workers = 1
worker_class = "sync"
timeout = 120          # 2 minute timeout (default is 30s - too short)
keepalive = 5
max_requests = 1000    # Restart worker after 1000 requests to prevent memory leaks
max_requests_jitter = 100
preload_app = True     # Load app once, share between workers
