# Usar imagem oficial do Python slim
FROM python:3.12-slim

# Definir variáveis de ambiente para otimizar o Python no container
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Definir diretório de trabalho
WORKDIR /app

# Instalar dependências de sistema necessárias para PostgreSQL e compilação básica
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements.txt e instalar dependências do Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo o código da aplicação
COPY . /app/

# Expor a porta que o gunicorn usará
EXPOSE 8000

# Executar migrações, coletar arquivos estáticos e iniciar o Gunicorn
CMD ["sh", "-c", "python manage.py collectstatic --noinput && python manage.py migrate && gunicorn clinic_manager.wsgi:application --bind 0.0.0.0:8000"]
