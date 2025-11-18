#!/bin/bash
set -e

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
    exec start-worker.sh ${SPARK_MASTER}
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