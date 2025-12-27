FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primeiro (cache do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fonte
COPY src/ ./src/

# Criar diretórios para dados
RUN mkdir -p /app/data /app/exports

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV TZ=America/Sao_Paulo

CMD ["python", "src/main.py"]
