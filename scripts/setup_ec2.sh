#!/bin/bash
set -e

# Auto-detect Package Manager
if command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
elif command -v apt-get &> /dev/null; then
    PKG_MANAGER="apt-get"
else
    echo "Unsupported OS: Neither dnf nor apt-get found."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Installing Docker using $PKG_MANAGER..."
    
    if [ "$PKG_MANAGER" = "dnf" ]; then
        # Amazon Linux 2023
        sudo dnf update -y
        sudo dnf install -y docker git
        sudo service docker start
        sudo usermod -a -G docker ec2-user
        sudo systemctl enable docker
    elif [ "$PKG_MANAGER" = "apt-get" ]; then
        # Ubuntu
        sudo apt-get update -y
        sudo apt-get install -y docker.io git
        sudo systemctl start docker
        sudo systemctl enable docker
        # Try adding 'ubuntu' user to docker group, fallback to current user
        sudo usermod -a -G docker ubuntu || sudo usermod -a -G docker $USER
    fi
else
    echo "Docker already installed."
    # Ensure current user is in docker group just in case (idempotent-ish)
    if [ "$PKG_MANAGER" = "dnf" ]; then
         sudo usermod -a -G docker ec2-user
    else
         sudo usermod -a -G docker ubuntu || sudo usermod -a -G docker $USER
    fi
fi

# Check if Docker Compose is installed
if ! docker compose version &> /dev/null; then
    echo "Installing Docker Compose..."
    sudo mkdir -p /usr/local/lib/docker/cli-plugins/
    sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
    sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
else
    echo "Docker Compose already installed."
fi

echo "Setup Complete!"
docker compose version || echo "Please re-login to use docker without sudo."
