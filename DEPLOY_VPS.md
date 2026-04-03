# MuseGenx1000 VPS Deployment Guide

## 🚀 Quick Start
Run the automated deployment script:
```bash
chmod +x deploy_vps.sh
./deploy_vps.sh
```

## 🔑 Secrets Checklist (.env.production)
Ensure the following variables are set in your `.env.production` file before deploying.
**WARNING**: Never commit `.env.production` to version control. Use `.env.example` as a template.
**GitHub Actions**: If using CI/CD, add these secrets to your repository settings.

- **Database**
  - `POSTGRES_PASSWORD`: Set this to a strong password.
  - `DATABASE_URL`: `postgresql://muse:<POSTGRES_PASSWORD>@postgres:5432/musegenx1000` (Update password here too).

- **Email (Optional)**
  - `SMTP_USER`
  - `SMTP_PASS`

- **Integrations**
  - `SLACK_WEBHOOK_URL`: For notifications.
  - `SENTRY_DSN`: For error tracking.
  - `GOAPI_KEY`: For integration tests (if running).
  - `FAL_KEY`: If using Fal.ai.
  - `TWOCAPTCHA_KEY`: For Suno/Udio captcha solving.

## 🗄️ Database Migrations (Alembic)

The application uses Alembic for database migrations.

### Generating Initial Migration (Development)
If this is the first time setting up the database with Alembic, you need to generate the initial migration script.
Run this command inside the container:
```bash
docker-compose exec app alembic revision --autogenerate -m "Initial migration"
```

### Running Migrations
To upgrade the database to the latest schema version:
```bash
docker-compose exec app alembic upgrade head
```
*Tip: Always test migrations on a staging environment before applying to production.*

### Switching to External Postgres (RDS)
If you decide to move from the containerized Postgres to a managed service (e.g., AWS RDS, DigitalOcean Managed DB):

1.  Update `.env.production`:
    Change `DATABASE_URL` to your external database connection string.
    ```env
    DATABASE_URL=postgresql://user:password@rds-endpoint:5432/dbname
    ```
2.  Run migrations against the new database:
    ```bash
    docker-compose exec app alembic upgrade head
    ```

## ⚙️ Systemd Service (Auto-start)
The deployment script sets up a Systemd service (`musegenx1000.service`) to automatically start the application on boot.

### Service File Example (`/etc/systemd/system/musegenx1000.service`)
```ini
[Unit]
Description=MuseGenX1000 Compose
Requires=docker.service
After=docker.service

[Service]
WorkingDirectory=/home/ubuntu/musegenx1000
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
RemainAfterExit=yes
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

### Manual Setup
If you need to set this up manually:
```bash
sudo cp deploy/musegenx1000.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable musegenx1000.service
sudo systemctl start musegenx1000.service
```

## 🛡️ Security & Firewall
Basic security measures for your VPS.

### UFW Firewall
Allow only necessary ports (SSH, HTTP, HTTPS) and deny everything else.
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow http
sudo ufw allow https
sudo ufw enable
```

### Database Security
**By default, Postgres and Redis ports are NOT exposed to the host.**
The `docker-compose.yml` configuration ensures that:
- `postgres` (5432) is only accessible by other containers in the `musenet` network.
- `redis` (6379) is only accessible by other containers in the `musenet` network.
- `clamav` (3310) is only accessible by the app container.

**Verification**:
Run `docker-compose ps` and ensure the `PORTS` column for these services is empty or does not show `0.0.0.0:PORT->...`.
If you see `127.0.0.1:5432->5432/tcp`, it is bound to localhost (safe from internet).
If you see `0.0.0.0:5432->5432/tcp`, it is **UNSAFE**. Remove the `ports` section in `docker-compose.yml`.

## 🔐 SSL/TLS Setup (Certbot)
To obtain a free SSL certificate from Let's Encrypt:

1.  **Stop Nginx** (to free up port 80):
    ```bash
    docker-compose stop nginx
    ```
2.  **Run Certbot**:
    ```bash
    sudo certbot certonly --standalone -d musegenx1000.com -d www.musegenx1000.com
    ```
3.  **Start Nginx**:
    ```bash
    docker-compose start nginx
    ```

### Auto-Renewal
Certbot usually installs a systemd timer. Verify it:
```bash
systemctl list-timers | grep certbot
```
If not, add a cron job (`crontab -e`). Example:
```bash
# Renew daily at 3am. The hook restarts nginx if renewed.
0 3 * * * /usr/bin/certbot renew --quiet --post-hook "docker-compose -f /home/ubuntu/musegenx1000/docker-compose.yml restart nginx"
```

## 💾 Backup & Retention

### Database Backup Script
We use a script to backup Postgres and rotate backups older than 90 days.
Script location: `scripts/pg_backup_rotate.sh`.

**Setup on VPS**:
1. Copy the script to `/usr/local/bin/`:
   ```bash
   sudo cp scripts/pg_backup_rotate.sh /usr/local/bin/
   sudo chmod +x /usr/local/bin/pg_backup_rotate.sh
   ```

2. Ensure `.pgpass` file exists for passwordless authentication (or use env vars in script).

### Automated Schedule (Crontab)
Add the following line to root's crontab (`sudo crontab -e`) to run daily at 02:30:

```bash
30 2 * * * /usr/local/bin/pg_backup_rotate.sh >> /var/log/musegenx1000_backup.log 2>&1
```

## 📊 Monitoring & Alerting

### Prometheus
We expose metrics at `/metrics` (on the main app port 7860).
To monitor the application, you can run Prometheus (either locally or in a container).

**Example Configuration**:
- `deploy/monitoring/prometheus.yml`: Example Prometheus config.
- `deploy/monitoring/alerts.yml`: Alert rules for high error rates and latency.
- `deploy/monitoring/alertmanager.yml`: Alertmanager config for Slack notifications.

**Slack Notifications**:
The deployment script automatically injects `SLACK_WEBHOOK_URL` from `.env.production` into `alertmanager.yml`.
1. Set `SLACK_WEBHOOK_URL=https://hooks.slack.com/...` in `.env.production`.
2. Run `./deploy_vps.sh` (or restart containers) to apply changes.

### Sentry (Error Tracking)
Ensure `SENTRY_DSN` is set in `.env.production`.

**Quick Verification**:
Run this command inside the app container to trigger a test error:
```bash
docker-compose exec app python -c "import os, sentry_sdk; sentry_sdk.init(os.getenv('SENTRY_DSN')); 1/0"
```
Check your Sentry dashboard for the "ZeroDivisionError".

### Healthcheck Endpoint
The app exposes a healthcheck endpoint for Nginx/Load Balancers:
- **URL**: `/healthz`
- **Method**: `GET`
- **Response**: `200 OK`, Body: `{"status": "ok"}`

## 🛠️ Useful Commands

### Service Management
- **Start/Restart (Rebuild)**: Pull latest images/code and restart.
  ```bash
  docker-compose up -d --build
  ```
- **Stop**: Stop all services.
  ```bash
  docker-compose down
  ```
- **View Logs**: Follow logs for the main application.
  ```bash
  docker-compose logs -f app
  ```

### Database
- **Run Migrations**: Apply latest database schema changes.
  ```bash
  docker-compose exec app alembic upgrade head
  ```
- **Connect to DB**: Open psql shell inside container.
  ```bash
  docker-compose exec postgres psql -U muse -d musegenx1000
  ```

## ✅ Quick Validation & Smoke Test (Post-Deploy)

### 1. Manual Checklist
Run these commands on the VPS to verify the deployment:

```bash
# 1. Check containers status
docker-compose ps

# 2. View application logs
docker-compose logs -f app

# 3. Verify Nginx listening on 80/443
sudo ss -ltnp | grep nginx

# 4. Verify Gradio/FastAPI response (internal)
curl -v http://localhost:7860/healthz

# 5. Verify Nginx Proxy (external)
curl -vk https://musegenx1000.com/healthz

# 6. Verify Postgres connection
docker-compose exec postgres psql -U muse -d musegenx1000 -c '\l'

# 7. Verify Redis connection
docker-compose exec redis redis-cli ping
# Should return PONG

# 8. Verify ClamAV listening on 3310
nc -vz localhost 3310
```

### 2. Automated Smoke Test
We have provided a script `scripts/run_smoke_test.sh` to simulate a user subscription flow and admin approval.

**Prerequisites**:
- `jq` installed (`sudo apt install jq`)
- App running and accessible

**Run the test**:
```bash
# Ensure it is executable
chmod +x scripts/run_smoke_test.sh

# Run against localhost (default)
./scripts/run_smoke_test.sh
```

## ✅ Final Pre-Production Checklist
Execute this checklist before switching DNS or going live.

### 1. SSL & HTTPS Verification
- [ ] **Certificates Valid**: Ensure Certbot has successfully generated certificates in `/etc/letsencrypt/live/musegenx1000.com/`.
- [ ] **Nginx Serving HTTPS**: Verify the site is accessible via HTTPS and redirects HTTP to HTTPS.
  ```bash
  curl -I https://musegenx1000.com
  # Expect HTTP/2 200 OK or 301 Moved Permanently
  ```

### 2. Health & Smoke Tests
- [ ] **Healthz Endpoint**: Confirm the application is healthy.
  ```bash
  curl -f https://musegenx1000.com/healthz
  # Expect {"status": "ok"}
  ```
- [ ] **Smoke Test**: Run the automated smoke test script against the production URL.
  ```bash
  ./scripts/run_smoke_test.sh https://musegenx1000.com
  ```

### 3. Backup Verification
- [ ] **Manual Backup Run**: Execute the backup script manually and verify the output file.
  ```bash
  sudo /usr/local/bin/pg_backup_rotate.sh
  ls -lh /var/backups/musegenx1000/
  # Ensure a new .sql.gz file exists with non-zero size.
  ```
- [ ] **Cron Job**: Verify the cron job is active.
  ```bash
  sudo crontab -l | grep pg_backup_rotate.sh
  ```

### 4. Monitoring & Alerting
- [ ] **Prometheus UI**: Access via `http://<VPS_IP>:9090`.
  - Go to **Status > Targets**.
  - Ensure `musegenx1000` target (`app:7860/metrics`) is **UP**.
- [ ] **Alertmanager UI**: Access via `http://<VPS_IP>:9093`.
  - Go to **Status**.
  - Verify `slack-notifications` receiver is configured.
- [ ] **Test Alerts**: Trigger a test alert (e.g., stop the app container briefly).
  - Check `#alerts` channel in Slack.
- [ ] **Manual Slack Test**: Verify webhook configuration.
  ```bash
  chmod +x scripts/test_slack.sh
  ./scripts/test_slack.sh
  ```

**Security Note**:
Ports 9090 and 9093 are exposed for convenience.
**Recommended**: Block these ports in UFW and use SSH Tunnel to access them securely:
```bash
ssh -L 9090:localhost:9090 -L 9093:localhost:9093 user@vps-ip
```
Then open `http://localhost:9090` and `http://localhost:9093` locally.

### 5. Security & Configuration
- [ ] **Secrets Management**: Ensure `.env.production` contains STRONG passwords and valid API keys.
- [ ] **AV_STRICT Mode**: If ClamAV is deployed and healthy, enable strict mode in `.env.production`.
  ```ini
  AV_STRICT=true
  ```
  Then restart the app: `docker-compose restart app`.
- [ ] **GitHub Actions Secrets**: If using CI/CD, configure repository secrets (`HOST`, `USERNAME`, `KEY`, `ENV_FILE`) to match production credentials.

### 6. Database Migrations & Smoke Test
**Run Database Migrations**:
Before testing, ensure the database schema is up-to-date.
```bash
# Option A: Run Alembic migrations (Recommended)
docker-compose exec app alembic upgrade head

# Option B: Run init script (if not using Alembic)
docker-compose exec app python scripts/init_db.py
```

**Run Smoke Test**:
Verify the application is working correctly against the production URL.
```bash
# Test against HTTPS (Production)
./scripts/run_smoke_test.sh https://musegenx1000.com

# Or test against localhost (Internal)
./scripts/run_smoke_test.sh http://localhost:7860
```
**Expected Output**:
- `/healthz`: `✅ /healthz OK`
- Create Subscription: `✅ Created subscription id=...`
- Admin Approve: `✅ Subscription approved successfully`

## 🚀 Go Live / DNS Switch
Follow this procedure to switch traffic to the new VPS.

### 1. Schedule Maintenance Window
- **Duration**: 10–30 minutes.
- **Action**: Notify users of potential downtime.

### 2. Update DNS Records
Login to your DNS Provider (e.g., Cloudflare, Namecheap, GoDaddy) and update:
- **Type**: `A` Record
- **Name**: `@` (or `musegenx1000.com`)
- **Value**: `<VPS_PUBLIC_IP>` (e.g., 1.2.3.4)
- **TTL**: Set to **Lowest possible** (e.g., 60s or 5 min) to ensure fast propagation.

*Note: If you have a `www` CNAME, ensure it points to `@` or the IP as well.*

### 3. Verify Propagation
Wait for DNS to propagate (check via `dig` or `whatsmydns.net`).
```bash
dig +short musegenx1000.com
# Should return your VPS IP
```

### 4. Final SSL & Smoke Test
Once DNS resolves to the VPS:
1. **SSL Certificate**: If you haven't generated the cert yet (or used a temporary IP), run Certbot now:
   ```bash
   sudo certbot certonly --standalone -d musegenx1000.com
   # Then restart Nginx
   docker-compose restart nginx
   ```
2. **Smoke Test**: Run the smoke test against the domain.
   ```bash
   ./scripts/run_smoke_test.sh https://musegenx1000.com
   ```

### 5. Post-Go Live Monitoring (First 30-60 Mins)
**Immediate Checks**:
1. **Metrics**: Watch Prometheus (`:9090`) for:
   - `http_requests_total`: Check for 5xx spikes.
   - `subscription_approval_latency`: Ensure it's within acceptable range.
2. **Logs**:
   ```bash
   docker-compose logs -f app nginx
   ```
3. **Backup Verification**:
   Manually run the backup script to ensure it works in the live environment:
   ```bash
   ./scripts/pg_backup_rotate.sh
   ls -lh /data/backups/postgres
   ```
4. **Antivirus Check**:
   If `AV_STRICT=true` caused issues (e.g., false positives or timeouts), temporarily disable it in `.env.production` and restart the app.
   ```ini
   AV_STRICT=false
   ```

### 6. Final DNS Cleanup
- **Increase TTL**: After 24-48 hours of stability, increase DNS TTL back to standard (e.g., 1 hour or 14400s).

## 🌟 Future Improvements

- **Visualization**: Add Grafana dashboard to visualize Prometheus metrics.
- **Automated SSL**: Use `nginx-proxy` + `acme-companion` for automated certificate management in containers.
- **CI/CD**: Configure Docker image tagging and CI to push images to a registry and perform zero-downtime deployments.
- **Managed Database**: Move Postgres to a managed DB (e.g., AWS RDS, DigitalOcean Managed Database) for better reliability, backups, and scaling.
