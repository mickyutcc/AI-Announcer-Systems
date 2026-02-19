#!/bin/bash

# Exit on error
set -e

echo "🚀 Starting MuseGenx1000 VPS Deployment..."

# 1. Check for .env.production
if [ ! -f .env.production ]; then
    echo "❌ Error: .env.production file not found!"
    echo "Please create .env.production from the template before running this script."
    exit 1
fi

# Check for default/unsafe values
if grep -q "POSTGRES_PASSWORD=musepass" .env.production; then
    echo "⚠️  WARNING: You are using the default POSTGRES_PASSWORD ('musepass')."
    echo "   Please change this in .env.production for production security."
fi

if grep -q "SLACK_WEBHOOK_URL=$" .env.production; then
    echo "ℹ️  Note: SLACK_WEBHOOK_URL is empty. Alert notifications will not work."
fi

if grep -q "SENTRY_DSN=$" .env.production; then
    echo "ℹ️  Note: SENTRY_DSN is empty. Error tracking is disabled."
fi

# 2. Create storage directories
echo "📂 Creating storage directories..."
mkdir -p /data/proofs
mkdir -p ./assets/proofs
# Ensure permissions (optional, adjust user as needed)
# sudo chown -R $USER:$USER /data/proofs

# 3. Check for SSL Certificates
DOMAIN="musegenx1000.com"
CERT_PATH="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"

if [ ! -f "$CERT_PATH" ]; then
    echo "⚠️  SSL Certificate not found at $CERT_PATH"
    echo "Running Certbot to generate certificates..."
    
    # Stop Nginx if running to free port 80
    if docker ps | grep -q musegenx1000_nginx; then
        echo "Stopping Nginx container..."
        docker-compose stop nginx
    fi
    
    # Run Certbot (Standalone)
    # Requires sudo if running as non-root user
    echo "Running Certbot (standalone mode)..."
    sudo certbot certonly --standalone \
        -d musegenx1000.com \
        -d www.musegenx1000.com \
        --non-interactive \
        --agree-tos \
        --email support@musegenx1000.com || {
            echo "❌ Certbot failed! Please check your domain DNS settings."
            exit 1
        }
        
    echo "✅ Certificates generated successfully!"
else
    echo "✅ SSL Certificates found."
fi

# 3.5 Configure Firewall
echo "🛡️  Configuring Firewall (UFW)..."
# Allow SSH to prevent lockout (Standard Practice)
sudo ufw allow OpenSSH
sudo ufw allow http
sudo ufw allow https
# Enable UFW non-interactively
echo "y" | sudo ufw enable
echo "✅ Firewall configured."

# 3.6 Setup Systemd Service (Optional but recommended)
echo "⚙️  Setting up Systemd service..."
SERVICE_FILE="deploy/musegenx1000.service"
TARGET_SERVICE="/etc/systemd/system/musegenx1000.service"
CURRENT_DIR=$(pwd)
DOCKER_COMPOSE_PATH=$(which docker-compose)

if [ -f "$SERVICE_FILE" ]; then
    echo "Installing service file..."
    sudo cp $SERVICE_FILE $TARGET_SERVICE
    
    # Update WorkingDirectory to current path
    sudo sed -i "s|WorkingDirectory=.*|WorkingDirectory=$CURRENT_DIR|g" $TARGET_SERVICE
    
    # Update ExecStart/Stop with actual docker-compose path
    if [ ! -z "$DOCKER_COMPOSE_PATH" ]; then
        sudo sed -i "s|ExecStart=.*|ExecStart=$DOCKER_COMPOSE_PATH up -d|g" $TARGET_SERVICE
        sudo sed -i "s|ExecStop=.*|ExecStop=$DOCKER_COMPOSE_PATH down|g" $TARGET_SERVICE
    fi
    
    sudo systemctl daemon-reload
    sudo systemctl enable musegenx1000.service
    echo "✅ Systemd service installed and enabled."
else
    echo "⚠️  Service file not found at $SERVICE_FILE, skipping systemd setup."
fi

# 3.7 Check Monitoring Configs
echo "📊 Checking Monitoring Configs..."
if [ ! -f "deploy/monitoring/alertmanager.yml" ]; then
    echo "⚠️  alertmanager.yml not found. Creating default..."
    mkdir -p deploy/monitoring
    cat <<EOF > deploy/monitoring/alertmanager.yml
global:
  resolve_timeout: 5m
route:
  group_by: ['alertname']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 1h
  receiver: 'slack-notifications'
receivers:
- name: 'slack-notifications'
  slack_configs:
  - api_url: 'SLACK_WEBHOOK_URL_PLACEHOLDER'
    channel: '#alerts'
    send_resolved: true
    title: '{{ template "slack.default.title" . }}'
    text: '{{ template "slack.default.text" . }}'
EOF
fi

# Inject Slack Webhook from .env.production if available
if grep -q "SLACK_WEBHOOK_URL=" .env.production; then
    # Extract URL (handle potential quotes)
    SLACK_URL=$(grep "^SLACK_WEBHOOK_URL=" .env.production | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    
    if [ ! -z "$SLACK_URL" ] && [ "$SLACK_URL" != "https://hooks.slack.com/services/..." ]; then
        echo "🔧 Injecting Slack Webhook from .env.production into alertmanager.yml..."
        # Use a temporary file for sed to avoid issues with slashes in URL
        # We search for the specific placeholder or the generic example URL
        sed -i "s|api_url: '.*'|api_url: '$SLACK_URL'|g" deploy/monitoring/alertmanager.yml
        # Also try to replace the previous placeholder if it exists
        sed -i "s|SLACK_WEBHOOK_URL_PLACEHOLDER|$SLACK_URL|g" deploy/monitoring/alertmanager.yml
        echo "✅ Alertmanager config updated with Slack Webhook."
    else
        echo "⚠️  SLACK_WEBHOOK_URL is empty or default in .env.production. Alertmanager will not send notifications."
    fi
fi

if [ ! -f "deploy/monitoring/prometheus.yml" ]; then
    echo "⚠️  prometheus.yml not found. Creating default..."
    mkdir -p deploy/monitoring
    cat <<EOF > deploy/monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
rule_files:
  - "alerts.yml"
alerting:
  alertmanagers:
  - static_configs:
    - targets:
      - alertmanager:9093
scrape_configs:
  - job_name: "musegenx1000"
    metrics_path: "/metrics"
    static_configs:
      - targets: ["app:7860"]
EOF
fi

if [ ! -f "deploy/monitoring/alerts.yml" ]; then
    echo "⚠️  alerts.yml not found. Creating default..."
    mkdir -p deploy/monitoring
    cat <<EOF > deploy/monitoring/alerts.yml
groups:
- name: musegenx1000_alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{job="musegenx1000",status=~"5.."}[5m]) > 0.05
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High 5xx rate"
      description: "5xx errors >5% in last 5m"
EOF
fi

# 4. Build and Start Services
echo "🐳 Building and starting Docker services..."
echo "  - Pulling latest base images..."
docker-compose pull
echo "  - Building services..."
docker-compose build
echo "  - Starting services..."
docker-compose up -d

# 5. Initialize Database
echo "🗄️  Initializing database schema..."
# Wait a moment for Postgres to be ready
echo "Waiting 10s for Postgres to start..."
sleep 10
docker-compose exec -T app python scripts/init_db.py

echo "✅ Deployment Complete!"
echo "------------------------------------------------"
echo "🌐 App is running at https://$DOMAIN"
echo "📊 Logs: docker-compose logs -f app"
echo "------------------------------------------------"
echo "Status:"
docker-compose ps
