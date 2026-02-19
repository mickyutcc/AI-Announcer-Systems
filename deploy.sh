#!/bin/bash
set -e

# Configuration
APP_NAME="musegenx1000"
DOCKER_COMPOSE_FILE="docker-compose.prod.yml"

echo "🚀 Deploying $APP_NAME..."

# Check if .env.prod exists
if [ ! -f .env.prod ]; then
    echo "❌ Error: .env.prod file not found!"
    echo "Please create one based on .env.example.prod"
    exit 1
fi

# Pull latest images
echo "📥 Pulling latest images..."
docker-compose -f $DOCKER_COMPOSE_FILE pull

# Build custom images
echo "🔨 Building application..."
docker-compose -f $DOCKER_COMPOSE_FILE build

# Stop existing containers
echo "🛑 Stopping old containers..."
docker-compose -f $DOCKER_COMPOSE_FILE down --remove-orphans

# Start new containers
echo "🚀 Starting new containers..."
docker-compose -f $DOCKER_COMPOSE_FILE up -d

# Wait for DB to be ready
echo "⏳ Waiting for database..."
sleep 10

# Run migrations (if any)
# Note: Since we use SQLAlchemy create_all in app startup or separate script, 
# we might need to trigger it manually or rely on app.py.
# Here we assume app.py handles it or we run a specific command:
echo "🔄 Running database migrations..."
docker-compose -f $DOCKER_COMPOSE_FILE exec -T web python -c "from models import Base; from database_setup import engine; Base.metadata.create_all(engine); print('DB Schema Updated')"

echo "✅ Deployment complete! Check status with: docker-compose -f $DOCKER_COMPOSE_FILE ps"
