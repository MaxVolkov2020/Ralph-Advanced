#!/bin/bash
# Ralph-Advanced Deployment Script
#
# This script automates the deployment of Ralph-Advanced on a Docker host.
#
# Usage:
#   ./scripts/deploy.sh
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - .env file configured (will be created with defaults if not present)

set -e

echo "========================================"
echo "Ralph-Advanced Deployment Script"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."

    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    print_status "Prerequisites OK"
}

# Check and create .env file if needed
setup_env() {
    print_status "Setting up environment..."

    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from .env.example..."

        if [ -f .env.example ]; then
            cp .env.example .env

            # Generate encryption key
            ENCRYPTION_KEY=$(python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())" 2>/dev/null || openssl rand -base64 32)

            # Update .env with generated key
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s|your-fernet-encryption-key-here|${ENCRYPTION_KEY}|g" .env
            else
                sed -i "s|your-fernet-encryption-key-here|${ENCRYPTION_KEY}|g" .env
            fi

            print_status "Generated encryption key and updated .env"
        else
            print_error ".env.example not found. Please create .env manually."
            exit 1
        fi
    else
        print_status ".env file exists"
    fi
}

# Build containers
build_containers() {
    print_status "Building Docker containers..."
    docker-compose build --no-cache
    print_status "Build complete"
}

# Start containers
start_containers() {
    print_status "Starting containers..."
    docker-compose up -d
    print_status "Containers started"
}

# Wait for services to be ready
wait_for_services() {
    print_status "Waiting for services to be ready..."

    # Wait for orchestrator health check
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            print_status "Orchestrator is ready"
            break
        fi

        if [ $attempt -eq $max_attempts ]; then
            print_error "Orchestrator failed to start. Check logs with: docker-compose logs orchestrator"
            exit 1
        fi

        echo -n "."
        sleep 2
        ((attempt++))
    done

    # Wait for UI
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:5555 > /dev/null 2>&1; then
            print_status "UI is ready"
            break
        fi

        if [ $attempt -eq $max_attempts ]; then
            print_error "UI failed to start. Check logs with: docker-compose logs ui"
            exit 1
        fi

        echo -n "."
        sleep 2
        ((attempt++))
    done
}

# Create admin user
create_admin() {
    print_status "Creating admin user..."

    # Copy script to container and run
    docker cp scripts/create_admin.py ralph-orchestrator:/app/scripts/
    docker-compose exec -T orchestrator python /app/scripts/create_admin.py --username admin --password '123LetsBuild@26!'

    print_status "Admin user created"
}

# Print summary
print_summary() {
    echo ""
    echo "========================================"
    echo "Deployment Complete!"
    echo "========================================"
    echo ""
    print_status "Ralph-Advanced is now running"
    echo ""
    echo "Access the application at:"
    echo "  - Web UI: http://localhost:5555 (or https://app.pressblk.com:5555)"
    echo "  - API: http://localhost:8000/api"
    echo ""
    echo "Login credentials:"
    echo "  - Username: admin"
    echo "  - Password: 123LetsBuild@26!"
    echo ""
    echo "Next steps:"
    echo "  1. Log in to the web interface"
    echo "  2. Go to Settings and configure your Claude API key"
    echo "  3. Create a project and add codebases"
    echo "  4. Start building!"
    echo ""
    echo "Useful commands:"
    echo "  - View logs: docker-compose logs -f"
    echo "  - Stop: docker-compose down"
    echo "  - Restart: docker-compose restart"
    echo ""
}

# Main execution
main() {
    check_prerequisites
    setup_env
    build_containers
    start_containers
    wait_for_services
    create_admin
    print_summary
}

# Run main function
main
