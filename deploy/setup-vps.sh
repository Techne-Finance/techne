#!/bin/bash
# Techne.finance VPS Deploy Script
# Run this on your Vultr VPS (Ubuntu 22.04)

set -e

echo "==================================="
echo "  Techne.finance Deploy Script"
echo "==================================="

# Update system
echo "[1/6] Updating system..."
apt update && apt upgrade -y

# Install dependencies
echo "[2/6] Installing dependencies..."
apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git

# Create app directory
echo "[3/6] Setting up app directory..."
mkdir -p /opt/techne-finance
cd /opt/techne-finance

# Create virtual environment
echo "[4/6] Creating Python environment..."
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install fastapi uvicorn httpx python-dotenv pydantic web3

# Create .env file
echo "[5/6] Creating .env file..."
cat > .env << 'EOF'
ALCHEMY_RPC_URL=https://base-mainnet.g.alchemy.com/v2/AqxI9okL6ZYv38MBFDHhb
MERIDIAN_WALLET=0xbA590c52173A29cDd594c2D5A903d54417D7c5c0
PORT=8000
EOF

echo "[6/6] Setup complete!"
echo ""
echo "Next steps:"
echo "1. Copy your backend files to /opt/techne-finance/"
echo "2. Run: systemctl enable techne && systemctl start techne"
echo "3. Configure nginx with provided config"
echo ""
