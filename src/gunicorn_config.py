# gunicorn_config.py
"""
Gunicorn WSGI server configuration for HPOneView-PagerDuty Bridge
Production-ready settings with logging, process management, and performance tuning
"""

import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
backlog = 2048

# Worker processes
# Auto-calculate based on CPU cores, or use environment variable
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = '-'  # Log to stdout
errorlog = '-'   # Log to stderr
loglevel = os.getenv('LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'hponeview-pagerduty-bridge'

# Preload app for better memory usage and faster worker spawn
preload_app = True


def when_ready(server):
    """Called just after the server is started."""
    server.log.info("HPOneView-PagerDuty Bridge server is ready. PID: %s", os.getpid())


def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("Worker received INT or QUIT signal")


def on_exit(server):
    """Called just before exiting."""
    server.log.info("HPOneView-PagerDuty Bridge server is shutting down")


# Security - Request size limits
limit_request_line = 4094        # Maximum size of HTTP request line
limit_request_fields = 100       # Maximum number of header fields
limit_request_field_size = 8190  # Maximum size of HTTP request header field