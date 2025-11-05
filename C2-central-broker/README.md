# C2 - Central Message Broker

Redis-based central message broker that handles sensor data storage and relay between all car system components.

## Features

- **Sensor Data Management**: Receives and stores data from C5 sensors
- **Command Relay**: Forwards commands between components  
- **Data Aggregation**: Combines sensor data for each car
- **Real-time Updates**: Publishes data changes to subscribers
- **Command History**: Tracks all commands sent to cars
- **REST API**: HTTP endpoints for data access
- **Health Monitoring**: System status and diagnostics

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start Redis (if not using Docker):
```bash
docker-compose up -d
```

3. Start the broker:
```bash
npm start
# or for development:
npm run dev
```

## Data Flow

### Sensor Data (C5 → C2)
- C5 sensors publish to: `sensors:indoor_temp`, `sensors:outdoor_temp`, `sensors:gps`
- C2 stores and aggregates data
- C2 publishes updates to: `car:{licensePlate}:data`

### Commands (B1/B2 → C2 → Cars)
- Commands published to: `car:{licensePlate}:commands`
- C2 stores in history and relays to: `car:{licensePlate}:active_commands`

## API Endpoints

### GET /api/car/{licensePlate}/data
Get latest aggregated data for a car.

### GET /api/car/{licensePlate}/sensors/{sensorType}  
Get specific sensor data for a car.

### POST /api/car/{licensePlate}/command
Send command to a car.
```json
{
  "command": "start_heating",
  "parameters": {
    "target_temp": 22
  }
}
```

### GET /api/car/{licensePlate}/commands
Get command history for a car.

### GET /api/cars
Get all active cars with latest data.

### GET /health
System health check.

## Redis Data Structure

```
car:{licensePlate}:sensors         # Hash of sensor data
car:{licensePlate}:latest_data     # JSON string of aggregated data  
car:{licensePlate}:command_history # List of commands
```

## Integration

- **C5**: Receives sensor data
- **C4**: Provides temperature data every 1s
- **C3**: Provides data updates every 30s  
- **C1**: Provides latest data every 10s
- **B2**: Receives data and forwards commands