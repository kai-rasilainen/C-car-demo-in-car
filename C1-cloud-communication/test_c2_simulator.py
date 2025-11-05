#!/usr/bin/env python3

import asyncio
import json
import random
import time
from datetime import datetime
import redis.asyncio as redis

class C2DataSimulator:
    """Simulate C2 data for testing C1 cloud communication"""
    
    def __init__(self, redis_url="redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        
    async def initialize(self):
        self.redis_client = redis.from_url(self.redis_url)
        await self.redis_client.ping()
        print("Connected to Redis")
    
    async def cleanup(self):
        if self.redis_client:
            await self.redis_client.aclose()
    
    async def generate_car_data(self, license_plate):
        """Generate realistic car sensor data"""
        base_indoor = 20.0
        base_outdoor = 10.0
        
        # Add some realistic variation
        indoor_temp = base_indoor + random.uniform(-3, 7)
        outdoor_temp = base_outdoor + random.uniform(-5, 10)
        
        # GPS coordinates around Helsinki
        base_lat, base_lng = 60.1699, 24.9384
        gps_lat = base_lat + random.uniform(-0.01, 0.01)
        gps_lng = base_lng + random.uniform(-0.01, 0.01)
        
        data = {
            'licensePlate': license_plate,
            'indoorTemp': round(indoor_temp, 1),
            'outdoorTemp': round(outdoor_temp, 1),
            'gps': {
                'lat': round(gps_lat, 6),
                'lng': round(gps_lng, 6)
            },
            'speed': random.randint(0, 80),
            'engineStatus': random.choice(['running', 'idle', 'off']),
            'fuelLevel': random.randint(10, 100),
            'batteryVoltage': round(random.uniform(11.8, 14.4), 1),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return data
    
    async def store_data_in_c2(self, license_plate, data):
        """Store data in Redis as C2 would do"""
        # Store latest data
        latest_key = f"car:{license_plate}:latest_data"
        await self.redis_client.set(latest_key, json.dumps(data), ex=300)  # 5 min expiry
        
        # Also store in history
        history_key = f"car:{license_plate}:history"
        await self.redis_client.lpush(history_key, json.dumps(data))
        await self.redis_client.ltrim(history_key, 0, 99)  # Keep last 100 entries
        
        print(f"Stored data for {license_plate}: Indoor {data['indoorTemp']}°C, Outdoor {data['outdoorTemp']}°C")
    
    async def simulate_data_flow(self, cars=['ABC-123', 'XYZ-789', 'DEF-456']):
        """Continuously generate and store car data"""
        print(f"Starting data simulation for cars: {cars}")
        
        try:
            while True:
                for license_plate in cars:
                    data = await self.generate_car_data(license_plate)
                    await self.store_data_in_c2(license_plate, data)
                
                # Wait before next update (simulate C5 sensor interval)
                await asyncio.sleep(5)  # 5 seconds between updates
                
        except KeyboardInterrupt:
            print("Data simulation stopped")

async def main():
    """Run the C2 data simulator"""
    simulator = C2DataSimulator()
    
    try:
        await simulator.initialize()
        await simulator.simulate_data_flow()
    finally:
        await simulator.cleanup()

if __name__ == "__main__":
    asyncio.run(main())