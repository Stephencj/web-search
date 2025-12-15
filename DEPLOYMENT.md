# WebSearch Deployment Guide

This guide covers deploying WebSearch to a Linux server with Docker.

## Prerequisites

- Linux server (Ubuntu 22.04+ recommended)
- Docker and Docker Compose installed
- Domain name pointed to your server (e.g., refinedaf.com)
- Ports 80 and 443 available

## Quick Start

### 1. Clone the Repository

```bash
cd /opt
git clone https://github.com/yourusername/web-search.git
cd web-search
```

### 2. Configure Environment

```bash
# Copy the production environment template
cp .env.prod.example .env

# Edit with your settings
nano .env
```

Required settings:
```env
DOMAIN=refinedaf.com
ACME_EMAIL=your-email@example.com
MEILI_MASTER_KEY=your-secure-key  # Generate with: openssl rand -base64 32
```

### 3. Deploy

```bash
# Build and start all services
docker compose -f docker-compose.prod.yml up -d --build

# Check status
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs -f
```

### 4. Verify

Visit `https://refinedaf.com` - you should see the WebSearch app with a valid SSL certificate.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Traefik (Reverse Proxy)                                    │
│  - SSL termination (Let's Encrypt)                          │
│  - HTTP → HTTPS redirect                                    │
│  - www → non-www redirect                                   │
│  Ports: 80, 443                                             │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│  WebSearch App          │     │  Meilisearch            │
│  - FastAPI backend      │────▶│  - Full-text search     │
│  - SvelteKit frontend   │     │  - Video indexing       │
│  Port: 8000 (internal)  │     │  Port: 7700 (internal)  │
└─────────────────────────┘     └─────────────────────────┘
              │
              ▼
┌─────────────────────────┐
│  Docker Volumes         │
│  - websearch-data       │
│  - meilisearch-data     │
│  - letsencrypt-data     │
└─────────────────────────┘
```

---

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DOMAIN` | Your domain name | `refinedaf.com` |
| `ACME_EMAIL` | Email for Let's Encrypt | `admin@refinedaf.com` |
| `MEILI_MASTER_KEY` | Meilisearch API key | (required) |
| `WEBSEARCH_OAUTH__YOUTUBE_CLIENT_ID` | YouTube OAuth client | (optional) |
| `WEBSEARCH_OAUTH__YOUTUBE_CLIENT_SECRET` | YouTube OAuth secret | (optional) |
| `WEBSEARCH_OAUTH__ENCRYPTION_KEY` | Token encryption key | (optional) |

### YouTube OAuth Setup (Optional)

For YouTube OAuth features:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable YouTube Data API v3
3. Configure OAuth consent screen
4. Create OAuth 2.0 Client ID (Web application)
5. Add authorized redirect URI: `https://refinedaf.com/api/accounts/callback/youtube`
6. Add client ID and secret to `.env`

---

## Common Operations

### Update Application

```bash
cd /opt/web-search

# Pull latest code
git pull

# Rebuild and restart
docker compose -f docker-compose.prod.yml up -d --build
```

### View Logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f websearch
docker compose -f docker-compose.prod.yml logs -f meilisearch
docker compose -f docker-compose.prod.yml logs -f traefik
```

### Restart Services

```bash
# Restart all
docker compose -f docker-compose.prod.yml restart

# Restart specific service
docker compose -f docker-compose.prod.yml restart websearch
```

### Stop Services

```bash
docker compose -f docker-compose.prod.yml down
```

### Backup Data

```bash
# Create backup directory
mkdir -p /opt/backups/websearch

# Backup volumes
docker run --rm \
  -v websearch-data:/data \
  -v /opt/backups/websearch:/backup \
  alpine tar czf /backup/websearch-data-$(date +%Y%m%d).tar.gz -C /data .

docker run --rm \
  -v meilisearch-data:/data \
  -v /opt/backups/websearch:/backup \
  alpine tar czf /backup/meilisearch-data-$(date +%Y%m%d).tar.gz -C /data .
```

### Restore Data

```bash
# Stop services first
docker compose -f docker-compose.prod.yml down

# Restore volume
docker run --rm \
  -v websearch-data:/data \
  -v /opt/backups/websearch:/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/websearch-data-YYYYMMDD.tar.gz -C /data"

# Start services
docker compose -f docker-compose.prod.yml up -d
```

---

## Using Existing Reverse Proxy

If you already have Traefik, Nginx, or another reverse proxy running (e.g., for botanicmanics.com), use the standard `docker-compose.yml` instead:

### With External Traefik

```bash
# Use the standard compose file
docker compose up -d --build
```

Then add labels to your existing Traefik configuration or update your nginx config:

**Nginx example:**
```nginx
server {
    listen 443 ssl http2;
    server_name refinedaf.com;

    ssl_certificate /etc/letsencrypt/live/refinedaf.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/refinedaf.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

---

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs websearch

# Check if port is in use
sudo lsof -i :80
sudo lsof -i :443
```

### SSL certificate issues

```bash
# Check Traefik logs
docker compose -f docker-compose.prod.yml logs traefik

# Verify DNS is pointing to server
dig refinedaf.com
```

### Database issues

```bash
# Enter container
docker compose -f docker-compose.prod.yml exec websearch bash

# Check database
ls -la /data/
```

### Meilisearch not healthy

```bash
# Check Meilisearch logs
docker compose -f docker-compose.prod.yml logs meilisearch

# Verify health endpoint
docker compose -f docker-compose.prod.yml exec meilisearch wget -qO- http://localhost:7700/health
```

---

## Security Recommendations

1. **Use strong keys**: Generate `MEILI_MASTER_KEY` with `openssl rand -base64 32`
2. **Keep Docker updated**: `apt update && apt upgrade docker-ce`
3. **Enable firewall**: Only allow ports 80, 443, and SSH
4. **Regular backups**: Set up automated backup cron jobs
5. **Monitor logs**: Use `docker compose logs -f` or ship to log aggregator

---

## Resource Requirements

Minimum:
- 1 CPU core
- 1GB RAM
- 10GB disk

Recommended:
- 2 CPU cores
- 2GB RAM
- 20GB disk

---

## Support

For issues, open a GitHub issue at: https://github.com/yourusername/web-search/issues
