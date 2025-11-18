FROM python:3.11-slim

WORKDIR /app

# Dépendances système (Debian Trixie compatible)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        netcat-openbsd \
        build-essential \
        gcc \
        g++ \
        cmake \
        libblas-dev \
        liblapack-dev \
        libigraph-dev \
        libxml2-dev \
        zlib1g-dev \
        gfortran \
        default-jdk-headless \
        git && \
    rm -rf /var/lib/apt/lists/*

# Configuration Java
ENV JAVA_HOME=/usr/lib/jvm/default-java
ENV PYSPARK_PYTHON=python3.11

# Installation Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . /app

CMD ["python", "preprocess.py"]