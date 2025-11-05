#!/usr/bin/env python3

import asyncio
import json
import random
import time
import math
from datetime import datetime
from typing import Dict, Any
import redis.asyncio as redis
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SensorSimulator:
    """Simulates car sensors sending data to C2 central broker"""
    
    def __init__(self, license_plate: str, redis_url: str = "redis://localhost:6379"):
        self.license_plate = license_plate
        self.redis_url = redis_url
        self.redis_client = None
        self.running = False
        
        # Sensor simulation parameters
        self.base_indoor_temp = 20.0
        self.base_outdoor_temp = 10.0
        self.base_lat = 60.1699  # Helsinki
        self.base_lng = 24.9384
        
        # Simulation state
        self.time_offset = 0
        self.outdoor_temp_trend = 0
        
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info(f"Car {self.license_plate} sensors connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def cleanup(self):
        """Clean up Redis connection"""
        if self.redis_client:
            await self.redis_client.aclose()
    
    def generate_indoor_temperature(self) -> float:
        """Generate realistic indoor temperature with daily variation"""
        # Base temperature with some random variation
        temp = self.base_indoor_temp + random.uniform(-2, 5)
        
        # Add some slow drift to simulate heating/cooling
        drift = math.sin(self.time_offset * 0.01) * 3
        temp += drift
        
        return round(temp, 1)
    
    def generate_outdoor_temperature(self) -> float:
        """Generate realistic outdoor temperature with daily cycle"""
        # Daily temperature cycle (simplified)
        hour_of_day = (time.time() % 86400) / 3600  # 0-24
        daily_variation = math.sin((hour_of_day - 6) * math.pi / 12) * 8  # Peak at 2 PM
        
        # Seasonal base temperature
        temp = self.base_outdoor_temp + daily_variation
        
        # Add weather variation
        temp += self.outdoor_temp_trend
        self.outdoor_temp_trend += random.uniform(-0.1, 0.1)
        self.outdoor_temp_trend = max(-5, min(5, self.outdoor_temp_trend))  # Limit trend
        
        # Random noise
        temp += random.uniform(-1, 1)
        
        return round(temp, 1)
    
    def generate_gps_location(self) -> Dict[str, float]:
        """Generate GPS coordinates with realistic movement"""
        # Simulate car movement in a small area
        movement_radius = 0.005  # ~500m radius
        
        # Slow movement pattern
        angle = self.time_offset * 0.02
        distance = random.uniform(0, movement_radius)
        
        lat_offset = math.cos(angle) * distance
        lng_offset = math.sin(angle) * distance
        
        return {
            'lat': round(self.base_lat + lat_offset, 6),
            'lng': round(self.base_lng + lng_offset, 6)
        }
    
    async def send_sensor_data(self, sensor_type: str, value: Any):
        """Send sensor data to C2 via Redis"""
        try:
            data = {
                'licensePlate': self.license_plate,
                'sensorType': sensor_type,
                'value': value,
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'C5_sensors'
            }
            
            channel = f"sensors:{sensor_type}"
            await self.redis_client.publish(channel, json.dumps(data))
            
            logger.debug(f"Car {self.license_plate} sent {sensor_type}: {value}")
            
        except Exception as e:
            logger.error(f"Error sending sensor data: {e}")
    
    async def temperature_sensor_loop(self):
        """Indoor temperature sensor - sends every 100ms"""
        while self.running:
            try:
                temp = self.generate_indoor_temperature()
                await self.send_sensor_data('indoorTemp', temp)
                await asyncio.sleep(0.1)  # 100ms
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Indoor temperature sensor error: {e}")
                await asyncio.sleep(1)
    
    async def outdoor_sensor_loop(self):
        """Outdoor temperature sensor - sends every 100ms"""
        while self.running:
            try:
                temp = self.generate_outdoor_temperature()
                await self.send_sensor_data('outdoorTemp', temp)
                await asyncio.sleep(0.1)  # 100ms
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Outdoor temperature sensor error: {e}")
                await asyncio.sleep(1)
    
    async def gps_sensor_loop(self):
        """GPS sensor - sends every 1 second"""
        while self.running:
            try:
                location = self.generate_gps_location()
                await self.send_sensor_data('gps', location)
                await asyncio.sleep(1.0)  # 1 second
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"GPS sensor error: {e}")
                await asyncio.sleep(1)
    
    async def time_tracker(self):
        """Track simulation time"""
        start_time = time.time()
        while self.running:
            self.time_offset = time.time() - start_time
            await asyncio.sleep(1)
    
    async def run_sensors(self):
        """Run all sensors concurrently"""
        logger.info(f"Starting sensors for car {self.license_plate}")
        self.running = True
        
        # Start all sensor tasks
        tasks = [
            asyncio.create_task(self.temperature_sensor_loop()),
            asyncio.create_task(self.outdoor_sensor_loop()),
            asyncio.create_task(self.gps_sensor_loop()),
            asyncio.create_task(self.time_tracker())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info(f"Stopping sensors for car {self.license_plate}")
        finally:
            self.running = False
            for task in tasks:
                task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*tasks, return_exceptions=True)

class MultiCarSensorSimulator:
    """Simulates sensors for multiple cars"""
    
    def __init__(self, cars=['ABC-123', 'XYZ-789', 'DEF-456'], redis_url="redis://localhost:6379"):
        self.cars = cars
        self.redis_url = redis_url
        self.simulators = []
    
    async def initialize(self):
        """Initialize simulators for all cars"""
        for license_plate in self.cars:
            simulator = SensorSimulator(license_plate, self.redis_url)
            await simulator.initialize()
            self.simulators.append(simulator)
            logger.info(f"Initialized sensors for {license_plate}")
    
    async def cleanup(self):
        """Clean up all simulators"""
        for simulator in self.simulators:
            await simulator.cleanup()
    
    async def run_all(self):
        """Run sensors for all cars concurrently"""
        logger.info(f"Starting sensor simulation for {len(self.cars)} cars")
        
        tasks = []
        for simulator in self.simulators:
            task = asyncio.create_task(simulator.run_sensors())
            tasks.append(task)
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Stopping all car sensors")
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

async def main():
    """Main function to run the sensor simulators"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Car sensor simulator for C5 component')
    parser.add_argument('--cars', nargs='+', default=['ABC-123', 'XYZ-789', 'DEF-456'],
                       help='License plates of cars to simulate')
    parser.add_argument('--redis-url', default='redis://localhost:6379',
                       help='Redis URL for C2 connection')
    
    args = parser.parse_args()
    
    simulator = MultiCarSensorSimulator(args.cars, args.redis_url)
    
    try:
        await simulator.initialize()
        await simulator.run_all()
    finally:
        await simulator.cleanup()

if __name__ == "__main__":
    asyncio.run(main())