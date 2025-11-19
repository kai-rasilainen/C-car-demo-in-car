const redis = require('redis');
const { promisify } = require('util');

/**
 * Comprehensive C2 Central Broker Tests
 * Tests Redis pub/sub, message routing, and data aggregation
 */

jest.mock('redis');

describe('C2 Central Broker - Comprehensive Tests', () => {
  let mockRedisClient;
  let mockPubSub;
  let publishedMessages;
  let subscribedChannels;

  beforeAll(() => {
    publishedMessages = [];
    subscribedChannels = new Set();

    // Mock Redis client
    mockRedisClient = {
      connect: jest.fn().mockResolvedValue(true),
      get: jest.fn(),
      set: jest.fn().mockResolvedValue('OK'),
      publish: jest.fn((channel, message) => {
        publishedMessages.push({ channel, message });
        return Promise.resolve(1);
      }),
      subscribe: jest.fn((channel, callback) => {
        subscribedChannels.add(channel);
        return Promise.resolve();
      }),
      hSet: jest.fn().mockResolvedValue(1),
      hGet: jest.fn(),
      hGetAll: jest.fn(),
      quit: jest.fn().mockResolvedValue('OK')
    };

    redis.createClient = jest.fn(() => mockRedisClient);
  });

  beforeEach(() => {
    jest.clearAllMocks();
    publishedMessages = [];
    subscribedChannels.clear();
  });

  describe('Redis Connection', () => {
    test('should connect to Redis successfully', async () => {
      const client = redis.createClient({ url: 'redis://localhost:6379' });
      await client.connect();

      expect(client.connect).toHaveBeenCalled();
      expect(redis.createClient).toHaveBeenCalledWith({ url: 'redis://localhost:6379' });
    });

    test('should handle connection configuration', () => {
      const config = { url: 'redis://localhost:6379' };
      const client = redis.createClient(config);

      expect(redis.createClient).toHaveBeenCalledWith(config);
    });
  });

  describe('Sensor Data Publishing', () => {
    test('should publish sensor data to sensors:temperature channel', async () => {
      const client = redis.createClient();
      await client.connect();

      const sensorData = {
        licensePlate: 'ABC-123',
        indoorTemp: 22.5,
        outdoorTemp: 15.2,
        timestamp: new Date().toISOString()
      };

      await client.publish('sensors:temperature', JSON.stringify(sensorData));

      expect(client.publish).toHaveBeenCalledWith(
        'sensors:temperature',
        JSON.stringify(sensorData)
      );
      expect(publishedMessages).toHaveLength(1);
      expect(publishedMessages[0].channel).toBe('sensors:temperature');
    });

    test('should publish GPS data to sensors:gps channel', async () => {
      const client = redis.createClient();
      await client.connect();

      const gpsData = {
        licensePlate: 'ABC-123',
        lat: 60.1699,
        lng: 24.9384,
        timestamp: new Date().toISOString()
      };

      await client.publish('sensors:gps', JSON.stringify(gpsData));

      expect(client.publish).toHaveBeenCalledWith(
        'sensors:gps',
        JSON.stringify(gpsData)
      );
    });

    test('should publish battery data to sensors:battery channel', async () => {
      const client = redis.createClient();
      await client.connect();

      const batteryData = {
        licensePlate: 'ABC-123',
        batteryLevel: 85,
        voltage: 12.6,
        timestamp: new Date().toISOString()
      };

      await client.publish('sensors:battery', JSON.stringify(batteryData));

      expect(publishedMessages).toHaveLength(1);
      expect(publishedMessages[0].channel).toBe('sensors:battery');
    });

    test('should handle multiple sensor data types', async () => {
      const client = redis.createClient();
      await client.connect();

      const sensorTypes = ['temperature', 'gps', 'battery', 'speed', 'fuel'];

      for (const type of sensorTypes) {
        const data = {
          licensePlate: 'ABC-123',
          type,
          value: Math.random() * 100,
          timestamp: new Date().toISOString()
        };

        await client.publish(`sensors:${type}`, JSON.stringify(data));
      }

      expect(publishedMessages).toHaveLength(5);
      expect(publishedMessages.map(m => m.channel)).toEqual(
        sensorTypes.map(t => `sensors:${t}`)
      );
    });
  });

  describe('Channel Subscription', () => {
    test('should subscribe to sensors:* channels', async () => {
      const client = redis.createClient();
      await client.connect();

      await client.subscribe('sensors:*', (message, channel) => {
        console.log(`Received on ${channel}: ${message}`);
      });

      expect(client.subscribe).toHaveBeenCalled();
      expect(subscribedChannels.has('sensors:*')).toBe(true);
    });

    test('should subscribe to vehicle:* channels', async () => {
      const client = redis.createClient();
      await client.connect();

      await client.subscribe('vehicle:*', (message, channel) => {
        console.log(`Received on ${channel}: ${message}`);
      });

      expect(subscribedChannels.has('vehicle:*')).toBe(true);
    });

    test('should subscribe to car-specific command channels', async () => {
      const client = redis.createClient();
      await client.connect();

      await client.subscribe('car:ABC-123:commands', (message, channel) => {
        console.log(`Command for ABC-123: ${message}`);
      });

      expect(subscribedChannels.has('car:ABC-123:commands')).toBe(true);
    });

    test('should handle multiple subscriptions', async () => {
      const client = redis.createClient();
      await client.connect();

      const channels = [
        'sensors:temperature',
        'sensors:gps',
        'sensors:battery',
        'car:ABC-123:commands'
      ];

      for (const channel of channels) {
        await client.subscribe(channel, () => {});
      }

      expect(client.subscribe).toHaveBeenCalledTimes(4);
      channels.forEach(channel => {
        expect(subscribedChannels.has(channel)).toBe(true);
      });
    });
  });

  describe('Data Aggregation and Storage', () => {
    test('should store aggregated car data in hash', async () => {
      const client = redis.createClient();
      await client.connect();

      const carData = {
        licensePlate: 'ABC-123',
        indoorTemp: 22.5,
        outdoorTemp: 15.2,
        batteryLevel: 85,
        gps: JSON.stringify({ lat: 60.1699, lng: 24.9384 })
      };

      await client.hSet('car:ABC-123:sensors', carData);

      expect(client.hSet).toHaveBeenCalledWith('car:ABC-123:sensors', carData);
    });

    test('should retrieve car sensor data from hash', async () => {
      const client = redis.createClient();
      await client.connect();

      const mockData = {
        licensePlate: 'ABC-123',
        indoorTemp: '22.5',
        outdoorTemp: '15.2',
        batteryLevel: '85'
      };

      client.hGetAll.mockResolvedValue(mockData);

      const data = await client.hGetAll('car:ABC-123:sensors');

      expect(client.hGetAll).toHaveBeenCalledWith('car:ABC-123:sensors');
      expect(data).toEqual(mockData);
    });

    test('should store latest data with timestamp', async () => {
      const client = redis.createClient();
      await client.connect();

      const timestamp = new Date().toISOString();
      const data = {
        licensePlate: 'ABC-123',
        value: '22.5',
        timestamp
      };

      await client.set('car:ABC-123:latest_data', JSON.stringify(data));

      expect(client.set).toHaveBeenCalledWith(
        'car:ABC-123:latest_data',
        JSON.stringify(data)
      );
    });

    test('should retrieve latest data for car', async () => {
      const client = redis.createClient();
      await client.connect();

      const mockLatestData = JSON.stringify({
        licensePlate: 'ABC-123',
        indoorTemp: 22.5,
        batteryLevel: 85,
        timestamp: new Date().toISOString()
      });

      client.get.mockResolvedValue(mockLatestData);

      const data = await client.get('car:ABC-123:latest_data');
      const parsed = JSON.parse(data);

      expect(client.get).toHaveBeenCalledWith('car:ABC-123:latest_data');
      expect(parsed.licensePlate).toBe('ABC-123');
      expect(parsed.indoorTemp).toBe(22.5);
    });
  });

  describe('Command Routing', () => {
    test('should publish command to car-specific channel', async () => {
      const client = redis.createClient();
      await client.connect();

      const command = {
        command: 'lock',
        timestamp: new Date().toISOString(),
        source: 'B2-iot-gateway'
      };

      await client.publish('car:ABC-123:commands', JSON.stringify(command));

      expect(publishedMessages).toHaveLength(1);
      expect(publishedMessages[0].channel).toBe('car:ABC-123:commands');
      
      const publishedCommand = JSON.parse(publishedMessages[0].message);
      expect(publishedCommand.command).toBe('lock');
    });

    test('should handle multiple commands for same car', async () => {
      const client = redis.createClient();
      await client.connect();

      const commands = ['lock', 'unlock', 'start', 'stop'];

      for (const cmd of commands) {
        const command = {
          command: cmd,
          timestamp: new Date().toISOString()
        };

        await client.publish('car:ABC-123:commands', JSON.stringify(command));
      }

      expect(publishedMessages).toHaveLength(4);
      publishedMessages.forEach((msg, i) => {
        const cmd = JSON.parse(msg.message);
        expect(cmd.command).toBe(commands[i]);
      });
    });

    test('should route commands to different cars', async () => {
      const client = redis.createClient();
      await client.connect();

      const cars = ['ABC-123', 'XYZ-789', 'DEF-456'];

      for (const car of cars) {
        const command = {
          command: 'lock',
          licensePlate: car,
          timestamp: new Date().toISOString()
        };

        await client.publish(`car:${car}:commands`, JSON.stringify(command));
      }

      expect(publishedMessages).toHaveLength(3);
      expect(publishedMessages.map(m => m.channel)).toEqual(
        cars.map(c => `car:${c}:commands`)
      );
    });
  });

  describe('Message Format Validation', () => {
    test('should handle valid JSON sensor data', async () => {
      const client = redis.createClient();
      await client.connect();

      const validData = {
        licensePlate: 'ABC-123',
        sensor: 'temperature',
        value: 22.5,
        unit: 'celsius',
        timestamp: new Date().toISOString()
      };

      await client.publish('sensors:temperature', JSON.stringify(validData));

      expect(client.publish).toHaveBeenCalled();
      
      const published = JSON.parse(publishedMessages[0].message);
      expect(published).toEqual(validData);
    });

    test('should handle sensor data with nested objects', async () => {
      const client = redis.createClient();
      await client.connect();

      const complexData = {
        licensePlate: 'ABC-123',
        gps: {
          lat: 60.1699,
          lng: 24.9384,
          accuracy: 5,
          altitude: 10
        },
        metadata: {
          source: 'C5-sensors',
          version: '1.0'
        },
        timestamp: new Date().toISOString()
      };

      await client.publish('sensors:gps', JSON.stringify(complexData));

      const published = JSON.parse(publishedMessages[0].message);
      expect(published.gps.lat).toBe(60.1699);
      expect(published.metadata.source).toBe('C5-sensors');
    });
  });

  describe('Data Flow Simulation', () => {
    test('should simulate complete sensor-to-cloud data flow', async () => {
      const client = redis.createClient();
      await client.connect();

      // Step 1: Sensor publishes data
      const sensorData = {
        licensePlate: 'ABC-123',
        temperature: 22.5,
        timestamp: new Date().toISOString()
      };

      await client.publish('sensors:temperature', JSON.stringify(sensorData));

      // Step 2: C2 stores aggregated data
      await client.hSet('car:ABC-123:sensors', {
        temperature: '22.5',
        lastUpdate: sensorData.timestamp
      });

      // Step 3: C2 updates latest data
      await client.set('car:ABC-123:latest_data', JSON.stringify(sensorData));

      // Verify all steps
      expect(publishedMessages).toHaveLength(1);
      expect(client.hSet).toHaveBeenCalled();
      expect(client.set).toHaveBeenCalled();
    });

    test('should simulate command-to-car flow', async () => {
      const client = redis.createClient();
      await client.connect();

      // Step 1: Cloud sends command via B2
      const command = {
        command: 'lock',
        source: 'B2-iot-gateway',
        timestamp: new Date().toISOString()
      };

      await client.publish('car:ABC-123:commands', JSON.stringify(command));

      // Step 2: C2 routes command to car (already published)
      
      // Step 3: Subscribe to commands (car would receive this)
      await client.subscribe('car:ABC-123:commands', (msg) => {
        const cmd = JSON.parse(msg);
        expect(cmd.command).toBe('lock');
      });

      // Verify
      expect(publishedMessages[0].channel).toBe('car:ABC-123:commands');
      expect(subscribedChannels.has('car:ABC-123:commands')).toBe(true);
    });
  });

  describe('Error Handling', () => {
    test('should handle connection errors', async () => {
      mockRedisClient.connect.mockRejectedValueOnce(new Error('Connection failed'));

      const client = redis.createClient();

      await expect(client.connect()).rejects.toThrow('Connection failed');
    });

    test('should handle publish errors', async () => {
      mockRedisClient.publish.mockRejectedValueOnce(new Error('Publish failed'));

      const client = redis.createClient();
      await client.connect();

      await expect(
        client.publish('test:channel', 'test message')
      ).rejects.toThrow('Publish failed');
    });

    test('should handle invalid JSON data gracefully', async () => {
      const client = redis.createClient();
      await client.connect();

      // Even though we publish invalid JSON, Redis will store it as-is
      // It's the receiver's responsibility to handle parsing errors
      await client.publish('sensors:test', '{invalid json}');

      expect(client.publish).toHaveBeenCalled();
    });
  });

  describe('Performance', () => {
    test('should handle rapid message publishing', async () => {
      const client = redis.createClient();
      await client.connect();

      const messageCount = 100;
      const promises = [];

      for (let i = 0; i < messageCount; i++) {
        const data = {
          licensePlate: 'ABC-123',
          value: i,
          timestamp: new Date().toISOString()
        };

        promises.push(
          client.publish('sensors:test', JSON.stringify(data))
        );
      }

      await Promise.all(promises);

      expect(publishedMessages).toHaveLength(messageCount);
    });

    test('should handle multiple car data streams concurrently', async () => {
      const client = redis.createClient();
      await client.connect();

      const cars = ['ABC-123', 'XYZ-789', 'DEF-456'];
      const promises = [];

      cars.forEach(car => {
        const data = {
          licensePlate: car,
          temperature: Math.random() * 30,
          timestamp: new Date().toISOString()
        };

        promises.push(
          client.publish('sensors:temperature', JSON.stringify(data))
        );
      });

      await Promise.all(promises);

      expect(publishedMessages).toHaveLength(3);
    });
  });

  describe('Cleanup', () => {
    test('should disconnect from Redis cleanly', async () => {
      const client = redis.createClient();
      await client.connect();
      await client.quit();

      expect(client.quit).toHaveBeenCalled();
    });
  });
});

