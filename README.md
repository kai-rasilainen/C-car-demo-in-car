# Car Demo System - In-Car Systems

In-car systems and sensors for the car demo system.

## Components

- **C1-cloud-communication**: Python cloud communication system
- **C2-central-broker**: Redis + Node.js central message broker
- **C5-data-sensors**: Python sensor simulators

## Quick Start

```bash
# Setup Python environment
./scripts/setup-python.sh

# Start Redis broker
docker-compose up -d

# Start all systems
./scripts/start-all.sh
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| C2 Central Broker | 3003 | Message broker HTTP API |
| Redis | 6379 | Message broker storage |
| C1 Cloud Comm | 8888 | Mock cloud server |
| C5 Sensors | - | Publishes to Redis |
