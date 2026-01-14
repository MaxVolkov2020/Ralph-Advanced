# Ralph-Advanced Testing Guide

This document provides instructions for testing the Ralph-Advanced system.

## Prerequisites

- Docker and Docker Compose installed
- API key for Manus or Claude
- Git configured with SSH keys (for repository access)

## Setup for Testing

### 1. Configure Environment

```bash
cd Ralph-Advanced
cp .env.example .env
```

Edit `.env` and add your API key:

```env
API_PROVIDER=manus
MANUS_API_KEY=your_actual_api_key_here
```

### 2. Build and Start Services

```bash
docker-compose build
docker-compose up -d
```

### 3. Verify Services are Running

```bash
docker-compose ps
```

All services should show "Up" status:
- ralph-redis
- ralph-orchestrator
- ralph-worker-backend
- ralph-worker-mobile
- ralph-worker-qa
- ralph-worker-code-review
- ralph-worker-security
- ralph-ui

### 4. Check Logs

```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f orchestrator
```

## Test Scenarios

### Scenario 1: Authentication

1. Open browser and navigate to `http://localhost`
2. You should see the login page
3. Login with:
   - Username: `Admin`
   - Password: `123Test@2026!`
4. You should be redirected to the dashboard

**Expected Result**: Successful login and dashboard display

### Scenario 2: Create a Project

1. Navigate to "Projects" page
2. Click "New Project"
3. Fill in the form:
   - Name: "Test Project"
   - Description: "A test project for Ralph-Advanced"
   - Backend Repository URL: `https://github.com/yourusername/backend-repo.git`
   - Mobile Repository URL: `https://github.com/yourusername/mobile-repo.git`
4. Click "Create Project"

**Expected Result**: Project is created and appears in the project list

### Scenario 3: Create a Feature

1. Click on the test project
2. Click "New Feature"
3. Fill in the form:
   - Name: "Task Priority System"
   - Description: "Add priority field to tasks"
   - Branch Name: "feature/task-priority"
   - PRD JSON: Copy content from `docs/sample_prd.json`
4. Click "Create Feature"

**Expected Result**: Feature is created with 5 user stories

### Scenario 4: Start Feature Execution

1. Click "Start Feature" on the created feature
2. Monitor the dashboard for progress updates
3. Check the story board to see stories moving through stages

**Expected Result**: 
- Stories move from "Pending" to "In Progress"
- Agent activity logs show agent invocations
- Stories progress through quality gates
- Successful stories are committed to git

### Scenario 5: Monitor Real-Time Updates

1. Keep the dashboard open while a feature is running
2. Observe real-time updates via WebSocket
3. Check the agent logs for detailed activity

**Expected Result**: Real-time updates without page refresh

### Scenario 6: View System Logs

1. Navigate to the logs section
2. Filter by log level (INFO, WARNING, ERROR)
3. Search for specific keywords

**Expected Result**: Logs are displayed and filterable

## API Testing

### Test Authentication

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "Admin", "password": "123Test@2026!"}'

# Response should include access_token
```

### Test Project Creation

```bash
# Create project (replace TOKEN with actual token from login)
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "name": "API Test Project",
    "description": "Created via API",
    "backend_repo_url": "https://github.com/example/backend.git"
  }'
```

### Test Dashboard Stats

```bash
curl -X GET http://localhost:8000/api/dashboard/stats \
  -H "Authorization: Bearer TOKEN"
```

## Worker Testing

### Test Backend Worker

```bash
# Enter worker container
docker exec -it ralph-worker-backend bash

# Check Python environment
python --version

# Test agent invoker
python -c "from agent_invoker import invoker; print('Agent invoker loaded successfully')"
```

### Test Redis Connection

```bash
# Enter Redis container
docker exec -it ralph-redis redis-cli

# Check connection
PING
# Should return: PONG

# Check queues
KEYS *
```

## Database Testing

### Access Database

```bash
# Enter orchestrator container
docker exec -it ralph-orchestrator bash

# Access SQLite database
sqlite3 ralph_advanced.db

# List tables
.tables

# Query users
SELECT * FROM users;

# Query projects
SELECT * FROM projects;

# Exit
.exit
```

## Troubleshooting

### Services Won't Start

```bash
# Check logs for errors
docker-compose logs

# Restart services
docker-compose restart

# Rebuild if needed
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Database Issues

```bash
# Reset database
docker-compose down -v
docker-compose up -d
```

### Worker Not Processing Tasks

```bash
# Check worker logs
docker-compose logs worker-backend

# Check Redis queue
docker exec -it ralph-redis redis-cli
LLEN backend
```

### API Key Issues

```bash
# Verify environment variables
docker exec ralph-orchestrator env | grep API_KEY

# Update .env and restart
docker-compose restart
```

## Performance Testing

### Load Test with Multiple Projects

1. Create 5 projects via API
2. Create 1 feature per project
3. Start all features simultaneously
4. Monitor system resources:

```bash
docker stats
```

**Expected Result**: System handles multiple projects concurrently

### Stress Test with Large Feature

1. Create a feature with 50+ user stories
2. Start the feature
3. Monitor completion time and resource usage

**Expected Result**: System processes all stories without crashing

## Integration Testing

### Test Full Workflow

1. Create project
2. Create feature with sample PRD
3. Start feature execution
4. Wait for completion
5. Verify:
   - All stories completed
   - Git commits created
   - Quality gates passed
   - No errors in logs

**Expected Result**: Complete feature implementation with all quality checks passed

## Cleanup

```bash
# Stop all services
docker-compose down

# Remove volumes (resets database)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

## Test Checklist

- [ ] Services start successfully
- [ ] Login works with default credentials
- [ ] Projects can be created
- [ ] Features can be created
- [ ] Features can be started
- [ ] Workers process tasks
- [ ] Quality gates execute
- [ ] Git commits are created
- [ ] Real-time updates work
- [ ] Logs are accessible
- [ ] API endpoints work
- [ ] Multiple projects run simultaneously
- [ ] System handles errors gracefully

## Known Limitations

1. **Repository Access**: Requires SSH keys or HTTPS credentials configured
2. **API Rate Limits**: Manus/Claude API rate limits may slow processing
3. **Resource Usage**: Each worker consumes memory; adjust based on available resources
4. **Database**: SQLite is for testing; use PostgreSQL for production

## Next Steps

After successful testing:

1. Configure production environment variables
2. Set up PostgreSQL database
3. Configure SSL/TLS for HTTPS
4. Set up monitoring and alerting
5. Deploy to production server or Proxmox
