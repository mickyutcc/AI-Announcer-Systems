#!/usr/bin/env bash
set -euo pipefail

# Configuration
OUTDIR=/var/backups/musegenx1000
PGPASSFILE=/root/.pgpass   # Ensure this file exists with permissions 0600 or use env vars
CONTAINER_NAME=postgres    # Adjust if your container name is different (e.g., musegenx1000_postgres_1)

mkdir -p "$OUTDIR"

TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")

# Backup
# Note: We use docker-compose exec if running via compose, or docker exec if container is known.
# The user provided example uses `docker-compose exec`. We need to be in the right directory or use -f.
# For simplicity in a standalone script, `docker exec` might be more robust if we know the container name,
# but `docker-compose` is what was requested. Let's assume the script is run where docker-compose.yml is,
# or we specify the path.
# User's snippet: docker-compose exec -T postgres ...
# We should probably hardcode the project path or allow it to be set.
PROJECT_DIR="/home/ubuntu/musegenx1000"

if [ -d "$PROJECT_DIR" ]; then
    cd "$PROJECT_DIR"
    /usr/bin/docker-compose exec -T postgres pg_dump -U muse musegenx1000 | gzip > "$OUTDIR/pg_$TIMESTAMP.sql.gz"
else
    echo "Error: Project directory $PROJECT_DIR not found."
    exit 1
fi

# Rotate: delete older than 90 days
find "$OUTDIR" -type f -name 'pg_*.sql.gz' -mtime +90 -delete
