FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Dépendances système
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        netcat-openbsd \
        curl \
        build-essential \
        cmake \
        pkg-config \
        libblas-dev \
        liblapack-dev \
        libigraph-dev \
        libxml2-dev \
        zlib1g-dev \
        gfortran \
        default-jdk-headless \
        git \
        ca-certificates \
        gnupg && \
    # Installation Docker CLI
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian bookworm stable" > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce-cli && \
    rm -rf /var/lib/apt/lists/*

# Installation Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Variables Spark
ENV SPARK_HOME=/usr/local/lib/python3.11/site-packages/pyspark
ENV PYSPARK_PYTHON=python3.11
ENV JAVA_HOME=/usr/lib/jvm/default-java

# Copie de l'entrypoint (AVANT le code)
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Copie du code Django
COPY app /app

EXPOSE 8000