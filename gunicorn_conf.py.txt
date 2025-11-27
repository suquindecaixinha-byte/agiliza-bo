# gunicorn_conf.py
import multiprocessing

# Configurações para o Render/Heroku
bind = "0.0.0.0:10000"
workers = 1  # No plano free, 1 worker é seguro
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120 # Tempo para a IA pensar sem dar timeout
keepalive = 5