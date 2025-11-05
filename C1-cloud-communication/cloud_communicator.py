import asyncio
import aiohttp
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
import redis.asyncio as redis
import os
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class CloudConfig:
    """Configuration for cloud communication"""
    cloud_endpoint: str
    api_key: str
    redis_url: str
    license_plate: str
    send_interval: int = 10  # seconds
    c2_data_key: str = "car_data"
    b2_commands_key: str = "car_commands"

class CloudCommunicator:
    """Handles communication between car systems and cloud services"""
    
    def __init__(self, config: CloudConfig):
        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = False
        
    async def initialize(self):
        """Initialize connections to Redis and HTTP client"""
        try:
            # Connect to Redis (C2)
            self.redis_client = redis.from_url(self.config.redis_url)
            await self.redis_client.ping()
            logger.info("Connected to Redis (C2)")
            
            # Create HTTP session for cloud communication
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    'Authorization': f'Bearer {self.config.api_key}',
                    'Content-Type': 'application/json'
                }
            )
            logger.info("HTTP session created for cloud communication")
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            raise
    
    async def cleanup(self):
        """Clean up connections"""
        if self.redis_client:
            await self.redis_client.aclose()
        if self.session:
            await self.session.close()
        logger.info("Connections cleaned up")
    
    async def get_latest_data_from_c2(self) -> Optional[Dict[str, Any]]:
        """Get the latest sensor data from C2 central broker"""
        try:
            if not self.redis_client:
                return None
                
            # Get latest data for this car from C2
            data_key = f"car:{self.config.license_plate}:latest_data"
            data_json = await self.redis_client.get(data_key)
            
            if data_json:
                data = json.loads(data_json)
                logger.debug(f"Retrieved data from C2: {data}")
                return data
            else:
                logger.warning(f"No data found in C2 for car {self.config.license_plate}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting data from C2: {e}")
            return None
    
    async def send_data_to_cloud(self, car_data: Dict[str, Any]) -> bool:
        """Send car data to cloud endpoint"""
        try:
            if not self.session:
                logger.error("HTTP session not initialized")
                return False
            
            # Prepare payload for cloud
            payload = {
                'timestamp': datetime.utcnow().isoformat(),
                'license_plate': self.config.license_plate,
                'data': car_data,
                'source': 'C1_cloud_communicator'
            }
            
            # Send to cloud
            async with self.session.post(
                f"{self.config.cloud_endpoint}/api/car-data",
                json=payload
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Successfully sent data to cloud: {result.get('message', 'OK')}")
                    
                    # Check for commands in response
                    commands = result.get('commands', [])
                    if commands:
                        await self.process_cloud_commands(commands)
                    
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to send data to cloud: {response.status} - {error_text}")
                    return False
                    
        except asyncio.TimeoutError:
            logger.error("Timeout sending data to cloud")
            return False
        except Exception as e:
            logger.error(f"Error sending data to cloud: {e}")
            return False
    
    async def process_cloud_commands(self, commands: list):
        """Process commands received from cloud"""
        try:
            for command in commands:
                logger.info(f"Processing cloud command: {command}")
                
                # Store command in Redis for other components
                command_data = {
                    'command': command.get('action'),
                    'parameters': command.get('parameters', {}),
                    'source': 'cloud',
                    'timestamp': datetime.utcnow().isoformat(),
                    'license_plate': self.config.license_plate
                }
                
                # Publish to Redis for B2 to pick up
                await self.redis_client.publish(
                    f"car:{self.config.license_plate}:commands",
                    json.dumps(command_data)
                )
                
                logger.info(f"Command forwarded to B2: {command_data['command']}")
                
        except Exception as e:
            logger.error(f"Error processing cloud commands: {e}")
    
    async def check_b2_for_commands(self) -> Optional[list]:
        """Optional: Check B2 for new commands"""
        try:
            if not self.redis_client:
                return None
            
            # Check for pending commands from B2
            command_key = f"car:{self.config.license_plate}:pending_commands"
            commands_json = await self.redis_client.get(command_key)
            
            if commands_json:
                commands = json.loads(commands_json)
                # Clear the pending commands
                await self.redis_client.delete(command_key)
                logger.info(f"Retrieved {len(commands)} commands from B2")
                return commands
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking B2 for commands: {e}")
            return None
    
    async def send_status_update(self, status: str, details: Dict[str, Any] = None):
        """Send status update to cloud"""
        try:
            if not self.session:
                return False
            
            payload = {
                'timestamp': datetime.utcnow().isoformat(),
                'license_plate': self.config.license_plate,
                'status': status,
                'details': details or {},
                'source': 'C1_cloud_communicator'
            }
            
            async with self.session.post(
                f"{self.config.cloud_endpoint}/api/car-status",
                json=payload
            ) as response:
                
                if response.status == 200:
                    logger.info(f"Status update sent: {status}")
                    return True
                else:
                    logger.error(f"Failed to send status update: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending status update: {e}")
            return False
    
    async def main_loop(self):
        """Main communication loop"""
        logger.info(f"Starting cloud communication for car {self.config.license_plate}")
        self.running = True
        
        # Send initial status
        await self.send_status_update("online", {"component": "C1_cloud_communicator"})
        
        consecutive_failures = 0
        max_failures = 5
        
        while self.running:
            try:
                start_time = time.time()
                
                # 1. Get latest data from C2
                car_data = await self.get_latest_data_from_c2()
                
                if car_data:
                    # 2. Send data to cloud
                    success = await self.send_data_to_cloud(car_data)
                    
                    if success:
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                        
                        if consecutive_failures >= max_failures:
                            logger.error(f"Too many consecutive failures ({consecutive_failures})")
                            await self.send_status_update("error", {
                                "message": "Cloud communication failed",
                                "consecutive_failures": consecutive_failures
                            })
                            break
                else:
                    logger.warning("No data available from C2")
                
                # 3. Optional: Check B2 for new commands
                b2_commands = await self.check_b2_for_commands()
                if b2_commands:
                    # Forward commands to cloud for logging/processing
                    for command in b2_commands:
                        logger.info(f"B2 command: {command}")
                
                # 4. Wait for next interval
                elapsed = time.time() - start_time
                sleep_time = max(0, self.config.send_interval - elapsed)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    
            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                consecutive_failures += 1
                await asyncio.sleep(5)  # Brief pause before retry
        
        self.running = False
        await self.send_status_update("offline", {"reason": "shutdown"})
        logger.info("Cloud communication stopped")

async def simulate_cloud_server():
    """Simulate a cloud server for testing"""
    from aiohttp import web
    
    async def handle_car_data(request):
        data = await request.json()
        logger.info(f"Cloud received data: {data}")
        
        # Simulate cloud response with commands
        response = {
            'status': 'received',
            'message': 'Data processed successfully',
            'commands': []
        }
        
        # Sometimes send commands back
        import random
        if random.random() < 0.1:  # 10% chance
            response['commands'] = [{
                'action': 'start_heating',
                'parameters': {'target_temp': 22}
            }]
        
        return web.json_response(response)
    
    async def handle_car_status(request):
        data = await request.json()
        logger.info(f"Cloud received status: {data}")
        return web.json_response({'status': 'received'})
    
    app = web.Application()
    app.router.add_post('/api/car-data', handle_car_data)
    app.router.add_post('/api/car-status', handle_car_status)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8888)
    await site.start()
    
    logger.info("Mock cloud server started on http://localhost:8888")
    return runner

async def main():
    """Main function to run the cloud communicator"""
    
    # Configuration
    config = CloudConfig(
        cloud_endpoint=os.getenv('CLOUD_ENDPOINT', 'http://localhost:8888'),
        api_key=os.getenv('CLOUD_API_KEY', 'demo-api-key'),
        redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379'),
        license_plate=os.getenv('LICENSE_PLATE', 'ABC-123'),
        send_interval=int(os.getenv('SEND_INTERVAL', '10'))
    )
    
    # Start mock cloud server for demo
    cloud_runner = await simulate_cloud_server()
    
    try:
        # Initialize and run cloud communicator
        communicator = CloudCommunicator(config)
        await communicator.initialize()
        
        try:
            await communicator.main_loop()
        finally:
            await communicator.cleanup()
            
    finally:
        # Clean up mock server
        await cloud_runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())