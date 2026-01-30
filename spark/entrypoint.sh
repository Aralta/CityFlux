#!/bin/bash
set -e

# Fix pour la résolution du hostname Java
# Java InetAddress.getLocalHost() a besoin que le hostname soit résolvable
HOSTNAME_VAL=$(hostname)
if ! getent hosts "$HOSTNAME_VAL" > /dev/null 2>&1; then
    echo "127.0.0.1 $HOSTNAME_VAL" >> /etc/hosts
    echo "✅ Ajouté $HOSTNAME_VAL dans /etc/hosts"
fi

SPARK_WORKLOAD=$1

echo "🚀 Démarrage Spark en mode: $SPARK_WORKLOAD"

# Désactiver rsync pour éviter l'erreur SSH
export SPARK_NO_RSYNC=true

case "$SPARK_WORKLOAD" in
  master)
    echo "📍 Lancement du Spark Master..."
    exec start-master.sh
    ;;
  worker)
    echo "⚙️  Lancement du Spark Worker..."
    exec start-worker.sh ${SPARK_MASTER_URL}
    ;;
  history)
    echo "📜 Lancement du Spark History Server..."
    exec start-history-server.sh
    ;;
  *)
    echo "❌ Mode inconnu: $SPARK_WORKLOAD"
    echo "Modes disponibles: master, worker, history"
    exit 1
    ;;
esac