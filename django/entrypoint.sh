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

echo "🗄️  Application des migrations..."
python manage.py migrate --noinput || true

echo "📦 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput || true

echo "🚀 Démarrage du serveur Django..."
exec "$@"