# Ralph-Advanced Deployment Guide

This guide covers deploying Ralph-Advanced using Docker containers for web access.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Network                            │
│                                                                  │
│  ┌──────────┐     ┌──────────────┐     ┌─────────────────────┐ │
│  │  Nginx   │────▶│  Orchestrator │────▶│      Redis          │ │
│  │  (UI)    │     │   (FastAPI)   │     │   (Task Queue)      │ │
│  │  :80     │     │    :8000      │     │    :6379            │ │
│  └──────────┘     └──────────────┘     └─────────────────────┘ │
│       │                  │                        │             │
│       │                  │                        │             │
│       │                  ▼                        │             │
│       │         ┌──────────────┐                  │             │
│       │         │   SQLite/    │                  │             │
│       │         │  PostgreSQL  │                  │             │
│       │         └──────────────┘                  │             │
│       │                                           │             │
│       │           ┌─────────────────────────┐    │             │
│       │           │       Workers            │◀───┘             │
│       │           │  - backend              │                   │
│       │           │  - mobile               │                   │
│       │           │  - qa                   │                   │
│       │           │  - code_review          │                   │
│       │           │  - security             │                   │
│       │           └─────────────────────────┘                   │
│       │                                                         │
└───────┼─────────────────────────────────────────────────────────┘
        │
        ▼
   Web Browser (Port 80)
```

## Prerequisites

- **Docker**: Version 20.10 or later
- **Docker Compose**: Version 2.0 or later
- **Server**: Linux server with at least 4GB RAM, 20GB storage
- **API Key**: Anthropic Claude API key or Manus API key

## Quick Start Deployment

### Step 1: Clone the Repository

```bash
git clone https://repo.verixity.com/internalapps/appbuilder.git ralph-advanced
cd ralph-advanced
```

### Step 2: Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Generate encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Copy the output to .env as ENCRYPTION_KEY

# Edit .env with your values
nano .env
```

**Required environment variables:**

| Variable | Description | Example |
|----------|-------------|---------|
| `API_PROVIDER` | AI provider: `claude` or `manus` | `claude` |
| `CLAUDE_API_KEY` | Anthropic API key | `sk-ant-...` |
| `SECRET_KEY` | JWT signing key | `random-32-char-string` |
| `ENCRYPTION_KEY` | Fernet key for git credentials | Generated above |

### Step 3: Build and Start Containers

```bash
# Build all containers
docker-compose build

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### Step 4: Access the Application

Open your browser and navigate to:
- **Web UI**: `http://your-server-ip:5555/`
- **API**: `http://your-server-ip:8000/api/`
- **Health Check**: `http://your-server-ip:8000/health`

For the PressBlk deployment:
- **Web UI**: `https://app.pressblk.com:5555/`

### Step 5: Create Initial User

The system needs an initial admin user. Use the provided script:

```bash
# Copy the script to the container and run it
docker cp scripts/create_admin.py ralph-orchestrator:/app/scripts/
docker-compose exec orchestrator python /app/scripts/create_admin.py --username admin --password 'your-secure-password'
```

Or use the automated deployment script:

```bash
./scripts/deploy.sh
```

The deployment script will create an admin user with:
- Username: `admin`
- Password: `123LetsBuild@26!`

### Step 6: Configure API Key

After logging in to the web interface:

1. Navigate to **Settings** in the top navigation
2. Enter your Claude API key
3. Click "Test API Key" to verify it works
4. Click "Save Settings"

The API key is encrypted before being stored in the database.

## Production Deployment

### Using PostgreSQL (Recommended for Production)

1. Uncomment PostgreSQL in `docker-compose.yml`:

```yaml
postgres:
  image: postgres:15-alpine
  container_name: ralph-postgres
  environment:
    POSTGRES_DB: ralph_advanced
    POSTGRES_USER: ralph
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  ports:
    - "5432:5432"
  volumes:
    - postgres_data:/var/lib/postgresql/data
  restart: unless-stopped
```

2. Update `.env`:

```bash
DATABASE_URL=postgresql://ralph:your_password@postgres:5432/ralph_advanced
POSTGRES_PASSWORD=your_password
```

3. Add `depends_on: postgres` to orchestrator and workers.

### HTTPS with Let's Encrypt (Production)

For production, use a reverse proxy with SSL. Example with Traefik:

1. Create `traefik.yml`:

```yaml
version: '3.8'

services:
  traefik:
    image: traefik:v2.10
    command:
      - "--api.dashboard=true"
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.le.acme.httpchallenge=true"
      - "--certificatesresolvers.le.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.le.acme.email=your-email@example.com"
      - "--certificatesresolvers.le.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "letsencrypt:/letsencrypt"
    networks:
      - ralph-network

volumes:
  letsencrypt:
```

2. Update `ui` service with Traefik labels:

```yaml
ui:
  labels:
    - "traefik.enable=true"
    - "traefik.http.routers.ralph.rule=Host(`ralph.yourdomain.com`)"
    - "traefik.http.routers.ralph.entrypoints=websecure"
    - "traefik.http.routers.ralph.tls.certresolver=le"
```

### Scaling Workers

To handle more concurrent stories, scale workers:

```bash
# Scale backend workers to 3 instances
docker-compose up -d --scale worker-backend=3
```

## Management Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f orchestrator
docker-compose logs -f worker-backend
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart orchestrator
```

### Stop and Clean Up

```bash
# Stop all containers
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

### Database Backup (SQLite)

```bash
# Backup
docker cp ralph-orchestrator:/app/ralph_advanced.db ./backup_$(date +%Y%m%d).db

# Restore
docker cp ./backup.db ralph-orchestrator:/app/ralph_advanced.db
docker-compose restart orchestrator
```

### Database Backup (PostgreSQL)

```bash
# Backup
docker-compose exec postgres pg_dump -U ralph ralph_advanced > backup_$(date +%Y%m%d).sql

# Restore
docker-compose exec -T postgres psql -U ralph ralph_advanced < backup.sql
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs for errors
docker-compose logs orchestrator

# Verify environment variables
docker-compose config
```

### API Returns 500 Error

```bash
# Check orchestrator logs
docker-compose logs -f orchestrator

# Common issues:
# - Missing ENCRYPTION_KEY
# - Invalid database connection
# - Missing API keys
```

### Workers Not Processing

```bash
# Check Redis connection
docker-compose exec redis redis-cli ping

# Check worker logs
docker-compose logs -f worker-backend
```

### UI Not Loading

```bash
# Check nginx logs
docker-compose logs ui

# Verify build completed
docker-compose exec ui ls /usr/share/nginx/html
```

## Monitoring

### Health Endpoints

- **Orchestrator**: `GET /health`
- **Redis**: `redis-cli ping`

### Resource Usage

```bash
# View container stats
docker stats

# View disk usage
docker system df
```

## Security Recommendations

1. **Change default secrets** - Update `SECRET_KEY` and `ENCRYPTION_KEY`
2. **Use HTTPS** - Deploy with SSL/TLS in production
3. **Firewall** - Only expose port 5555 (or your custom port) publicly
4. **Regular backups** - Automate database backups
5. **Update containers** - Regularly pull latest images
6. **Limit access** - Use strong passwords for user accounts
7. **Change default password** - Update admin password after first login

## Container Details

| Service | Port | Purpose |
|---------|------|---------|
| `ui` | 5555 | Web interface (Nginx + React) |
| `orchestrator` | 8000 | FastAPI backend |
| `redis` | 6379 | Task queue |
| `worker-*` | - | Background task processors |

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_PROVIDER` | No | `claude` | AI provider (`claude` or `manus`) |
| `CLAUDE_API_KEY` | No | - | Anthropic API key (can be set via Settings UI) |
| `MANUS_API_KEY` | No | - | Manus API key (can be set via Settings UI) |
| `SECRET_KEY` | Yes | - | JWT signing secret |
| `ENCRYPTION_KEY` | Yes | - | Fernet key for encryption |
| `DATABASE_URL` | No | SQLite | Database connection string |
| `REDIS_HOST` | No | `redis` | Redis hostname |
| `REDIS_PORT` | No | `6379` | Redis port |

**Note:** API keys can now be configured via the Settings page in the web UI after deployment. They are encrypted before being stored in the database.
