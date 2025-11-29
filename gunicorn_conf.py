import multiprocessing

# Configurações para o Render
bind = "0.0.0.0:10000"
workers = 1  # Manter 1 worker evita estourar a memória RAM do plano free
worker_class = "uvicorn.workers.UvicornWorker"

# AUMENTADO: Tempo limite para 400 segundos.
# Necessário para processar áudios longos e uploads de arquivos grandes.
timeout = 400 
keepalive = 5
