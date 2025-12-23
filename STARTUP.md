# WebSearch Startup Guide

## Required Services

| Service | Port | Domain | Location |
|---------|------|--------|----------|
| websearch-app | 8001 | refinedaf.com | /opt/web-search |
| websearch-meilisearch | 7700 | (internal) | /opt/web-search |
| media-server | 8080 | watch.refinedaf.com | ~/media-server |
| cloudflared | - | (tunnel) | systemd service |

## Quick Start (All Services)

```bash
# 1. Start WebSearch (app + meilisearch)
cd /opt/web-search
docker compose up -d

# 2. Start Media Server
cd ~/media-server
docker compose up -d

# 3. Verify cloudflared tunnel is running
systemctl status cloudflared
```

## Rebuild After Code Changes

```bash
cd /opt/web-search
docker compose up -d --build
```

**Note:** Do NOT use `--no-cache` unless absolutely necessary (takes 10+ minutes).

## Database Migrations

If you get errors like `no such column`, run:

```bash
docker exec websearch-app alembic upgrade head
```

Or manually add columns:

```bash
docker exec websearch-app python -c "
import sqlite3
conn = sqlite3.connect('/data/websearch.db')
cursor = conn.cursor()
# Add your ALTER TABLE statements here
conn.commit()
conn.close()
"
```

## Troubleshooting

### Check Container Status
```bash
docker compose ps
docker logs websearch-app --tail 50
```

### Check Health Endpoints
```bash
curl http://localhost:8001/health  # WebSearch
curl http://localhost:7700/health  # Meilisearch
curl http://localhost:8080/health  # Media Server (if available)
```

### DNS Issues During Docker Build

If docker build fails with DNS timeout errors (especially with VPN active):

1. The `# syntax=docker/dockerfile:1` line was removed from Dockerfile to avoid this
2. **Permanent fix (already applied)**: DNS servers added to Docker daemon:
   ```bash
   # /etc/docker/daemon.json contains: {"dns": ["8.8.8.8", "8.8.4.4"]}
   # If needed to recreate:
   echo '{"dns": ["8.8.8.8", "8.8.4.4"]}' | sudo tee /etc/docker/daemon.json
   sudo systemctl restart docker
   ```

### Cloudflared Tunnel

Config location: `~/.cloudflared/config.yml`

```bash
# Check status
systemctl status cloudflared

# View logs
journalctl -u cloudflared -f

# Restart if needed
sudo systemctl restart cloudflared
```

## Full System Restart

```bash
# Stop everything
cd /opt/web-search && docker compose down
cd ~/media-server && docker compose down

# Start everything
cd /opt/web-search && docker compose up -d
cd ~/media-server && docker compose up -d

# Verify
docker ps
systemctl status cloudflared
```
