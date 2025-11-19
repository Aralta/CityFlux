FROM postgis/postgis:16-3.4

# Copie du script SQL d'initialisation dans l'emplacement prévu par Postgres
COPY initdb.sql /docker-entrypoint-initdb.d/initdb.sql
