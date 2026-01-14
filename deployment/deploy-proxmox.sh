#!/bin/bash

# Ralph-Advanced Proxmox Deployment Script
# This script deploys Ralph-Advanced to a Proxmox LXC container

set -e

echo "========================================="
echo "Ralph-Advanced Proxmox Deployment"
echo "========================================="
echo ""

# Configuration
CONTAINER_ID=${1:-100}
CONTAINER_NAME="ralph-advanced"
CONTAINER_HOSTNAME="ralph-advanced"
CONTAINER_PASSWORD="ralph2026"
CONTAINER_MEMORY=4096
CONTAINER_SWAP=2048
CONTAINER_DISK=20
CONTAINER_CORES=2
STORAGE="local-lxc"
TEMPLATE="ubuntu-22.04-standard_22.04-1_amd64.tar.zst"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root or with sudo"
  exit 1
fi

echo "Step 1: Creating LXC container..."
pct create $CONTAINER_ID $STORAGE:vztmpl/$TEMPLATE \
  --hostname $CONTAINER_HOSTNAME \
  --password $CONTAINER_PASSWORD \
  --memory $CONTAINER_MEMORY \
  --swap $CONTAINER_SWAP \
  --rootfs $STORAGE:$CONTAINER_DISK \
  --cores $CONTAINER_CORES \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --features nesting=1 \
  --unprivileged 1 \
  --onboot 1

echo "Step 2: Starting container..."
pct start $CONTAINER_ID

# Wait for container to be ready
echo "Waiting for container to start..."
sleep 10

echo "Step 3: Installing dependencies..."
pct exec $CONTAINER_ID -- bash -c "
  apt-get update
  apt-get install -y curl git docker.io docker-compose
  systemctl enable docker
  systemctl start docker
"

echo "Step 4: Creating application directory..."
pct exec $CONTAINER_ID -- bash -c "
  mkdir -p /opt/ralph-advanced
  cd /opt/ralph-advanced
"

echo "Step 5: Copying Ralph-Advanced files..."
# Note: You need to have the Ralph-Advanced directory on the Proxmox host
# Adjust the path as needed
RALPH_DIR="/root/Ralph-Advanced"
if [ -d "$RALPH_DIR" ]; then
  pct push $CONTAINER_ID $RALPH_DIR /opt/ -r
else
  echo "Warning: Ralph-Advanced directory not found at $RALPH_DIR"
  echo "You'll need to manually copy the files or clone from Git"
fi

echo "Step 6: Setting up environment..."
pct exec $CONTAINER_ID -- bash -c "
  cd /opt/ralph-advanced
  cp .env.example .env
  echo 'Please edit /opt/ralph-advanced/.env with your API keys'
"

echo "Step 7: Building and starting Docker containers..."
pct exec $CONTAINER_ID -- bash -c "
  cd /opt/ralph-advanced
  docker-compose build
  docker-compose up -d
"

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Container ID: $CONTAINER_ID"
echo "Container Name: $CONTAINER_NAME"
echo "Container Password: $CONTAINER_PASSWORD"
echo ""
echo "Next steps:"
echo "1. Get container IP: pct exec $CONTAINER_ID -- hostname -I"
echo "2. Edit environment: pct exec $CONTAINER_ID -- nano /opt/ralph-advanced/.env"
echo "3. Restart services: pct exec $CONTAINER_ID -- bash -c 'cd /opt/ralph-advanced && docker-compose restart'"
echo "4. Access UI: http://<container-ip>"
echo "5. Login with: Admin / 123Test@2026!"
echo ""
echo "Useful commands:"
echo "- View logs: pct exec $CONTAINER_ID -- bash -c 'cd /opt/ralph-advanced && docker-compose logs -f'"
echo "- Stop services: pct exec $CONTAINER_ID -- bash -c 'cd /opt/ralph-advanced && docker-compose down'"
echo "- Start services: pct exec $CONTAINER_ID -- bash -c 'cd /opt/ralph-advanced && docker-compose up -d'"
echo ""
