#!/bin/bash
# Quick Start Script for Multi-User Portfolio Tracking
# Run this to set up and test your new features

set -e  # Exit on error

echo "🚀 B3 Tracker - Multi-User Setup"
echo "=================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your credentials:"
    echo "   - DB_PASSWORD"
    echo "   - SECRET_KEY (generate with: openssl rand -hex 32)"
    echo "   - GOOGLE_CLIENT_ID"
    echo "   - GOOGLE_CLIENT_SECRET"
    echo ""
    echo "   Get Google OAuth credentials from:"
    echo "   https://console.cloud.google.com/apis/credentials"
    echo ""
    read -p "Press Enter after configuring .env file..."
fi

echo "🏗️  Building Docker images..."
docker compose build

echo ""
echo "🚀 Starting services (PostgreSQL + App + API)..."
docker compose up -d

echo ""
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5

# Wait for PostgreSQL
MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if docker compose exec -T db pg_isready -U b3user -d b3tracker > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    echo "   Waiting... ($ATTEMPT/$MAX_ATTEMPTS)"
    sleep 2
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "❌ PostgreSQL failed to start"
    exit 1
fi

echo ""
echo "🧪 Running tests..."
docker compose run --rm runner python src/test_multiuser.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo ""
echo "1. View API documentation:"
echo "   http://localhost:8000/docs"
echo ""
echo "2. Login with Google:"
echo "   http://localhost:8000/auth/login"
echo ""
echo "3. Test endpoints (after login, use the token):"
echo "   curl -H 'Authorization: Bearer YOUR_TOKEN' http://localhost:8000/auth/me"
echo ""
echo "4. View logs:"
echo "   docker compose logs -f"
echo ""
echo "5. Stop services:"
echo "   docker compose down"
echo ""
echo "📖 Read SETUP_MULTIUSER.md for detailed documentation"
echo ""
