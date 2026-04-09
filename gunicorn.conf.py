import os

bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"
workers = 2
threads = 2
worker_class = "gthread"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
