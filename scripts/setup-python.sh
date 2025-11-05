#!/bin/bash
set -e

echo "Setting up Python environment for in-car systems..."

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Python environment setup complete!"
echo "To activate: source .venv/bin/activate"
