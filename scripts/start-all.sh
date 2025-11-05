#!/bin/bash
set -e

echo "Starting in-car system..."

# Detect docker compose command
if command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="docker compose"
fi

# Check if Redis is running
if ! docker ps | grep -q redis; then
    echo "Starting Redis..."
    $DOCKER_COMPOSE up -d redis
    sleep 5
fi

# Start C2 central broker
echo "Starting C2 central broker..."
cd C2-central-broker
npm start &
BROKER_PID=$!
cd ..

# Activate Python environment and start sensors
echo "Starting C5 sensor simulators..."
source .venv/bin/activate
cd C5-data-sensors
python sensor_simulator.py &
SENSORS_PID=$!
cd ..

# Start C1 cloud communication
echo "Starting C1 cloud communication..."
cd C1-cloud-communication
python cloud_communicator.py &
CLOUD_PID=$!
cd ..

echo "All in-car systems started!"
echo "PIDs: Broker=$BROKER_PID, Sensors=$SENSORS_PID, Cloud=$CLOUD_PID"
