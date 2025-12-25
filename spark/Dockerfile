FROM python:3.11-slim-bookworm

# Installation des dépendances système
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      curl \
      procps \
      rsync \
      openssh-client \
      default-jdk-headless \
      build-essential \
      cmake \
      pkg-config \
      libblas-dev \
      liblapack-dev \
      libigraph-dev \
      libxml2-dev \
      zlib1g-dev \
      gfortran \
      git && \
    rm -rf /var/lib/apt/lists/*

# Configuration Java et Spark
ENV JAVA_HOME=/usr/lib/jvm/default-java
ENV SPARK_VERSION=3.5.3
ENV HADOOP_VERSION=3
ENV SPARK_HOME=/opt/spark
ENV PATH="${SPARK_HOME}/sbin:${SPARK_HOME}/bin:${PATH}"
ENV PYSPARK_PYTHON=python3.11
ENV SPARK_NO_RSYNC=true

# Installation de Spark
RUN mkdir -p ${SPARK_HOME} && \
    curl -fsSL https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz \
    | tar -xz -C ${SPARK_HOME} --strip-components=1

# Driver JDBC PostgreSQL
RUN curl -fsSL https://jdbc.postgresql.org/download/postgresql-42.7.4.jar \
    -o ${SPARK_HOME}/jars/postgresql-42.7.4.jar

# Installation des dépendances Python
WORKDIR ${SPARK_HOME}
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Configuration Spark
COPY spark-defaults.conf ${SPARK_HOME}/conf/
RUN mkdir -p /opt/spark/spark-events /opt/spark/data /opt/spark/apps && \
    chmod -R 755 ${SPARK_HOME}/sbin ${SPARK_HOME}/bin

# Script d'entrée
COPY entrypoint.sh ${SPARK_HOME}/entrypoint.sh
RUN chmod +x ${SPARK_HOME}/entrypoint.sh


COPY /app/ ${SPARK_HOME}/apps/


EXPOSE 8080 7077 18080

ENTRYPOINT ["./entrypoint.sh"]