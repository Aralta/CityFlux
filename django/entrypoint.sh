#!/bin/bash
set -e

echo "🔄 Attente de PostgreSQL..."
until nc -z $SQL_HOST $SQL_PORT; do
  echo "  ⏳ PostgreSQL indisponible - attente..."
  sleep 2
done
echo "✅ PostgreSQL prêt!"

echo "🔄 Attente de Spark Master..."
until nc -z spark-master 7077; do
  echo "  ⏳ Spark Master indisponible - attente..."
  sleep 2
done
echo "✅ Spark Master prêt!"

# Si la commande commence par 'celery', attendre Redis
if [[ "$1" == "celery" ]]; then
  echo "🔄 Attente de Redis..."
  until nc -z redis 6379; do
    echo "  ⏳ Redis indisponible - attente..."
    sleep 2
  done
  echo "✅ Redis prêt!"
  echo "🚀 Démarrage de Celery..."
else
  echo "🚀 Démarrage du serveur Django..."
fi

exec "$@"
