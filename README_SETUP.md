# Development Environment Setup

## Prerequisites

- Python 3.9+
- Docker and Docker Compose (optional, for Redis and ClamAV)
- ClamAV (system-installed or via Docker)

## Services Setup

### 1. Redis and ClamAV

You can run Redis and ClamAV using Docker Compose for local development:

```bash
docker-compose up -d
```

This starts:
- Redis on port `6379`
- ClamAV on port `3310`

### 2. Manual ClamAV Setup (Linux/Ubuntu)

If you prefer not to use Docker for ClamAV:

```bash
sudo apt-get update
sudo apt-get install -y clamav clamav-daemon clamav-freshclam
sudo freshclam
sudo systemctl start clamav-daemon
```

### 3. Environment Variables

Create a `.env` file based on your needs. Key variables for services:

```ini
# Redis
REDIS_URL=redis://localhost:6379/0

# Metrics
METRICS_PORT=8000

# Security
AV_STRICT=false  # Set to true to enforce virus scanning
```

## Metrics and Monitoring

The application exposes Prometheus metrics at `http://localhost:8000/metrics`.

### Prometheus Alerts

An example alert rule configuration is provided in `prometheus_alerts.yml`. This rule triggers if the 90th percentile of subscription approval latency exceeds 24 hours.

To use this rule, configure your Prometheus server to load `prometheus_alerts.yml`.
