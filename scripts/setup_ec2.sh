#!/bin/bash
set -e

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    sudo dnf update -y
    sudo dnf install -y docker git
    sudo service docker start
    sudo usermod -a -G docker ec2-user
    sudo systemctl enable docker
else
    echo "Docker already installed."
fi

# Check if Docker Compose is installed
if [ ! -f "/usr/local/lib/docker/cli-plugins/docker-compose" ]; then
    echo "Installing Docker Compose..."
    sudo mkdir -p /usr/local/lib/docker/cli-plugins/
    sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
    sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
else
    echo "Docker Compose already installed."
fi

echo "Setup Complete!"
docker compose version || echo "Please re-login to use docker without sudo."
