# C1 - Cloud Communication System

Python asyncio-based system that handles communication between in-car systems and cloud services. Sends data every 10 seconds and processes cloud commands.

## Features

- **Periodic Data Upload**: Sends car data to cloud every 10 seconds
- **Cloud Command Processing**: Receives and forwards commands from cloud
- **C2 Integration**: Gets latest sensor data from central broker
- **B2 Integration**: Optional command checking from IoT gateway
- **Error Handling**: Retry logic and failure counting
- **Status Reporting**: Regular status updates to cloud
- **Mock Cloud Server**: Built-in test server for development

## Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Copy environment configuration:
```bash
cp .env.example .env
```

3. Make sure Redis (C2) is running:
```bash
# If using Docker
docker run -d -p 6379:6379 redis:alpine
```

4. Run the cloud communicator:
```bash
python cloud_communicator.py
```

## Configuration

Environment variables (see `.env.example`):

- `CLOUD_ENDPOINT`: Cloud API endpoint URL
- `CLOUD_API_KEY`: API key for cloud authentication  
- `REDIS_URL`: Redis connection URL (C2)
- `LICENSE_PLATE`: Car license plate identifier
- `SEND_INTERVAL`: Data sending interval in seconds (default: 10)

## Usage

### Basic Usage
```bash
python cloud_communicator.py
```

### Testing with Data Simulator
In a separate terminal, run the C2 data simulator:
```bash
python test_c2_simulator.py
```

This will generate realistic car data and store it in Redis for C1 to process.

### Custom Configuration
```bash
export LICENSE_PLATE=XYZ-789
export SEND_INTERVAL=15
python cloud_communicator.py
```

## Data Flow

1. **Get Data from C2**: Retrieves latest sensor data from Redis
2. **Send to Cloud**: Posts data to cloud endpoint via HTTP
3. **Process Commands**: Handles commands received from cloud
4. **Forward Commands**: Publishes commands to Redis for B2
5. **Status Updates**: Reports system status to cloud
6. **Optional B2 Check**: Retrieves pending commands from B2

## API Endpoints

The system communicates with cloud via REST API:

### POST /api/car-data
Send car sensor data to cloud.

**Payload:**
```json
{
  "timestamp": "2024-11-04T10:30:00.000Z",
  "license_plate": "ABC-123",
  "data": {
    "indoorTemp": 22.5,
    "outdoorTemp": 15.2,
    "gps": {
      "lat": 60.1699,
      "lng": 24.9384
    },
    "speed": 65,
    "engineStatus": "running"
  },
  "source": "C1_cloud_communicator"
}
```

**Response:**
```json
{
  "status": "received",
  "message": "Data processed successfully",
  "commands": [
    {
      "action": "start_heating",
      "parameters": {
        "target_temp": 22
      }
    }
  ]
}
```

### POST /api/car-status
Send system status updates.

**Payload:**
```json
{
  "timestamp": "2024-11-04T10:30:00.000Z",
  "license_plate": "ABC-123",
  "status": "online",
  "details": {
    "component": "C1_cloud_communicator"
  },
  "source": "C1_cloud_communicator"
}
```

## Redis Integration

### Data Retrieval (from C2)
- Key: `car:{license_plate}:latest_data`
- Contains: Latest sensor data in JSON format

### Command Publishing (to B2)
- Channel: `car:{license_plate}:commands`
- Contains: Command data for car systems

### Command Checking (from B2)
- Key: `car:{license_plate}:pending_commands`
- Contains: Array of pending commands

## Error Handling

- **Connection Failures**: Automatic retry with exponential backoff
- **Data Validation**: Validates data before sending to cloud
- **Timeout Handling**: 30-second timeout for cloud requests
- **Failure Counting**: Stops after 5 consecutive failures
- **Status Reporting**: Sends error status to cloud

## Mock Cloud Server

The built-in mock server simulates cloud responses:

- Listens on `http://localhost:8888`
- Accepts car data and status updates
- Randomly sends back commands (10% chance)
- Logs all received data

## Testing

1. Start Redis:
```bash
docker run -d -p 6379:6379 redis:alpine
```

2. Start C2 data simulator:
```bash
python test_c2_simulator.py
```

3. Start cloud communicator:
```bash
python cloud_communicator.py
```

4. Monitor logs to see data flow and command processing.

## Integration

This component integrates with:
- **C2** (Redis) - Gets sensor data, publishes commands
- **B2** (Redis) - Optional command retrieval
- **Cloud Services** - HTTP API communication

## Dependencies

- `aiohttp`: Async HTTP client for cloud communication
- `redis`: Async Redis client for C2/B2 communication
- `python-dotenv`: Environment variable management

## Deployment

For production deployment:

1. Set proper cloud endpoint and API key
2. Configure Redis connection for production
3. Set appropriate logging levels
4. Consider using systemd or Docker for service management
5. Monitor failure rates and adjust retry logic