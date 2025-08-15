#!/usr/bin/env python3
"""
Configuración de Gunicorn para producción
"""

# Configuración del servidor
bind = "0.0.0.0:10000"
workers = 2
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 50

# Configuración de logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Configuración de proceso
preload_app = True
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = None
group = None

# Configuración de memoria
worker_tmp_dir = "/dev/shm"
