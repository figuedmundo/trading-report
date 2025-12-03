#!/bin/sh
set -e
echo "Running migrations..."
python3 /docker-entrypoint-initdb.d/run_migrations.py
echo "Migrations finished."
