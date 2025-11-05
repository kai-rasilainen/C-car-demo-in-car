const redis = require('redis');
const express = require('express');
const cors = require('cors');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3003;

// Middleware
app.use(cors());
app.use(express.json());

// Redis clients
let pubClient, subClient, storageClient;

// Data storage for sensor data
const sensorData = new Map();
const commandHistory = new Map();

async function initializeRedis() {
  try {
    const redisConfig = {
      url: process.env.REDIS_URL || 'redis://localhost:6379'
    };

    // Publisher client
    pubClient = redis.createClient(redisConfig);
    await pubClient.connect();

    // Subscriber client  
    subClient = redis.createClient(redisConfig);
    await subClient.connect();

    // Storage client for data persistence
    storageClient = redis.createClient(redisConfig);
    await storageClient.connect();

    console.log('Connected to Redis - C2 Central Broker ready');

    // Subscribe to sensor data from C5
    await subClient.subscribe('sensors:indoor_temp', handleSensorData);
    await subClient.subscribe('sensors:outdoor_temp', handleSensorData);
    await subClient.subscribe('sensors:gps', handleSensorData);

    // Subscribe to commands from B1/B2
    await subClient.pSubscribe('car:*:commands', handleCarCommands);

  } catch (error) {
    console.error('Redis connection error:', error);
  }
}

async function handleSensorData(message, channel) {
  try {
    const data = JSON.parse(message);
    console.log(`Received sensor data on ${channel}:`, data);

    const { licensePlate, sensorType, value, timestamp } = data;

    // Store latest sensor data
    const carKey = `car:${licensePlate}:sensors`;
    await storageClient.hSet(carKey, sensorType, JSON.stringify({
      value,
      timestamp,
      source: 'C5_sensors'
    }));

    // Update latest aggregated data
    await updateLatestCarData(licensePlate);

    // Relay to other components
    await pubClient.publish(`car:${licensePlate}:data`, JSON.stringify(data));

  } catch (error) {
    console.error('Error handling sensor data:', error);
  }
}

async function updateLatestCarData(licensePlate) {
  try {
    // Get all sensor data for this car
    const carKey = `car:${licensePlate}:sensors`;
    const sensors = await storageClient.hGetAll(carKey);

    const latestData = {
      licensePlate,
      timestamp: new Date().toISOString()
    };

    // Parse sensor data
    Object.entries(sensors).forEach(([sensorType, dataStr]) => {
      try {
        const sensorData = JSON.parse(dataStr);
        latestData[sensorType] = sensorData.value;
        latestData[`${sensorType}_timestamp`] = sensorData.timestamp;
      } catch (e) {
        console.error(`Error parsing sensor data for ${sensorType}:`, e);
      }
    });

    // Store aggregated data
    const latestKey = `car:${licensePlate}:latest_data`;
    await storageClient.set(latestKey, JSON.stringify(latestData), { EX: 300 });

    console.log(`Updated latest data for ${licensePlate}:`, latestData);

  } catch (error) {
    console.error('Error updating latest car data:', error);
  }
}

async function handleCarCommands(message, channel) {
  try {
    const command = JSON.parse(message);
    console.log(`Received command on ${channel}:`, command);

    const licensePlate = command.licensePlate;
    
    // Store command in history
    const commandKey = `car:${licensePlate}:command_history`;
    await storageClient.lPush(commandKey, JSON.stringify({
      ...command,
      received_at: new Date().toISOString()
    }));
    await storageClient.lTrim(commandKey, 0, 99); // Keep last 100 commands

    // Relay command to car systems
    await pubClient.publish(`car:${licensePlate}:active_commands`, message);

  } catch (error) {
    console.error('Error handling car command:', error);
  }
}

// REST API endpoints

// Get latest data for a car
app.get('/api/car/:licensePlate/data', async (req, res) => {
  try {
    const { licensePlate } = req.params;
    const latestKey = `car:${licensePlate}:latest_data`;
    
    const data = await storageClient.get(latestKey);
    if (data) {
      res.json(JSON.parse(data));
    } else {
      res.status(404).json({ error: 'No data found for car' });
    }
  } catch (error) {
    console.error('Error getting car data:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get sensor history
app.get('/api/car/:licensePlate/sensors/:sensorType', async (req, res) => {
  try {
    const { licensePlate, sensorType } = req.params;
    const carKey = `car:${licensePlate}:sensors`;
    
    const sensorData = await storageClient.hGet(carKey, sensorType);
    if (sensorData) {
      res.json(JSON.parse(sensorData));
    } else {
      res.status(404).json({ error: 'Sensor data not found' });
    }
  } catch (error) {
    console.error('Error getting sensor data:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Send command to car
app.post('/api/car/:licensePlate/command', async (req, res) => {
  try {
    const { licensePlate } = req.params;
    const { command, parameters } = req.body;

    const commandData = {
      licensePlate,
      command,
      parameters: parameters || {},
      timestamp: new Date().toISOString(),
      source: 'C2_api'
    };

    await pubClient.publish(`car:${licensePlate}:commands`, JSON.stringify(commandData));

    res.json({ 
      success: true, 
      message: `Command sent to car ${licensePlate}`,
      command: commandData
    });

  } catch (error) {
    console.error('Error sending command:', error);
    res.status(500).json({ error: 'Failed to send command' });
  }
});

// Get command history
app.get('/api/car/:licensePlate/commands', async (req, res) => {
  try {
    const { licensePlate } = req.params;
    const limit = parseInt(req.query.limit) || 20;
    
    const commandKey = `car:${licensePlate}:command_history`;
    const commands = await storageClient.lRange(commandKey, 0, limit - 1);
    
    const parsedCommands = commands.map(cmd => JSON.parse(cmd));
    res.json(parsedCommands);

  } catch (error) {
    console.error('Error getting command history:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get all active cars
app.get('/api/cars', async (req, res) => {
  try {
    const keys = await storageClient.keys('car:*:latest_data');
    const cars = [];

    for (const key of keys) {
      const data = await storageClient.get(key);
      if (data) {
        cars.push(JSON.parse(data));
      }
    }

    res.json(cars);
  } catch (error) {
    console.error('Error getting cars:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Health check
app.get('/health', async (req, res) => {
  try {
    await storageClient.ping();
    const info = await storageClient.info();
    
    res.json({
      status: 'healthy',
      redis: 'connected',
      uptime: process.uptime(),
      timestamp: new Date().toISOString(),
      redis_info: {
        version: info.includes('redis_version') ? info.match(/redis_version:([^\r\n]+)/)[1] : 'unknown',
        connected_clients: info.includes('connected_clients') ? info.match(/connected_clients:([^\r\n]+)/)[1] : 'unknown'
      }
    });
  } catch (error) {
    res.status(500).json({
      status: 'unhealthy',
      error: error.message
    });
  }
});

// Start server
async function startServer() {
  await initializeRedis();
  
  app.listen(PORT, () => {
    console.log(`C2 Central Broker running on port ${PORT}`);
    console.log(`Health check: http://localhost:${PORT}/health`);
    console.log(`API docs: http://localhost:${PORT}/api/cars`);
  });
}

// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('Shutting down C2 Central Broker...');
  if (pubClient) await pubClient.quit();
  if (subClient) await subClient.quit();
  if (storageClient) await storageClient.quit();
  process.exit(0);
});

startServer().catch(console.error);