# C5 - Data Sensors

Python-based sensor simulators that generate realistic car sensor data and send it to the C2 central broker.

## Features

- **Indoor Temperature Sensor**: Sends data every 100ms with realistic variation
- **Outdoor Temperature Sensor**: Sends data every 100ms with daily cycles  
- **GPS Sensor**: Sends location data every 1 second with movement simulation
- **Multi-Car Support**: Simulate multiple cars simultaneously
- **Realistic Data**: Temperature cycles, movement patterns, and weather variation

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure Redis (C2) is running:
```bash
docker run -d -p 6379:6379 redis:alpine
```

3. Run the sensor simulator:
```bash
python sensor_simulator.py
```

## Usage

### Default (3 cars)
```bash
python sensor_simulator.py
```
Simulates ABC-123, XYZ-789, and DEF-456.

### Custom cars
```bash
python sensor_simulator.py --cars ABC-123 XYZ-789
```

### Custom Redis URL
```bash
python sensor_simulator.py --redis-url redis://localhost:6379
```

## Sensor Details

### Indoor Temperature (100ms interval)
- Base temperature: 20°C
- Variation: ±2°C random + heating/cooling cycles
- Realistic drift patterns

### Outdoor Temperature (100ms interval)  
- Base temperature: 10°C
- Daily temperature cycle (peaks at 2 PM)
- Weather trend simulation
- Seasonal variation

### GPS Location (1s interval)
- Base location: Helsinki, Finland
- Realistic movement in ~500m radius
- Slow movement patterns

## Data Format

Sensors publish to Redis channels:
- `sensors:indoorTemp`
- `sensors:outdoorTemp` 
- `sensors:gps`

Data format:
```json
{
  "licensePlate": "ABC-123",
  "sensorType": "indoorTemp",
  "value": 22.5,
  "timestamp": "2024-11-04T10:30:00.000Z",
  "source": "C5_sensors"
}
```

## Integration

- Sends data to **C2** central broker via Redis
- **C2** aggregates and stores the sensor data
- Other components consume data from **C2**

## Testing

Monitor sensor data in Redis:
```bash
redis-cli monitor
```

Or check the C2 API:
```bash
curl http://localhost:3003/api/cars
```