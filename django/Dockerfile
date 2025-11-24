FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

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
        git && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

ENV SPARK_HOME=/usr/local/lib/python3.11/site-packages/pyspark
ENV PYSPARK_PYTHON=python3.11
ENV JAVA_HOME=/usr/lib/jvm/default-java

# ENTRYPOINT HORS DE /app
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Dossier de code (vide ici, remplacé par volume)
RUN mkdir -p /app

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
