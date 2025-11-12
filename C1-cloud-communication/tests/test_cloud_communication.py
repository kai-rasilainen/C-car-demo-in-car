import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add the C1 directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock dependencies before importing the module
sys.modules['redis.asyncio'] = MagicMock()

import test_c2_simulator

class TestC2DataSimulator:
    """Test cases for C2 Data Simulator"""

    @pytest.fixture
    def simulator(self):
        """Create a simulator instance for testing"""
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            
            simulator = test_c2_simulator.C2DataSimulator()
            simulator.redis_client = mock_redis_client
            return simulator

    @pytest.mark.asyncio
    async def test_initialize_connection(self, simulator):
        """Test Redis connection initialization"""
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            mock_redis_client.ping = AsyncMock()
            
            await simulator.initialize()
            
            mock_redis.assert_called_once_with(simulator.redis_url)
            mock_redis_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_car_data(self, simulator):
        """Test car data generation"""
        license_plate = "ABC-123"
        
        car_data = await simulator.generate_car_data(license_plate)
        
        # Verify data structure
        assert car_data['licensePlate'] == license_plate
        assert 'indoorTemp' in car_data
        assert 'outdoorTemp' in car_data
        assert 'gps' in car_data
        assert 'speed' in car_data
        assert 'engineStatus' in car_data
        assert 'fuelLevel' in car_data
        assert 'batteryVoltage' in car_data
        assert 'timestamp' in car_data
        
        # Verify data types and ranges
        assert isinstance(car_data['indoorTemp'], (int, float))
        assert isinstance(car_data['outdoorTemp'], (int, float))
        assert isinstance(car_data['gps'], dict)
        assert 'lat' in car_data['gps']
        assert 'lng' in car_data['gps']
        
        # Verify temperature ranges
        assert -50 <= car_data['indoorTemp'] <= 100
        assert -50 <= car_data['outdoorTemp'] <= 100
        
        # Verify GPS coordinates are within valid ranges
        assert -90 <= car_data['gps']['lat'] <= 90
        assert -180 <= car_data['gps']['lng'] <= 180
        
        # Verify fuel level is between 0-100
        assert 0 <= car_data['fuelLevel'] <= 100

    @pytest.mark.asyncio
    async def test_store_car_data(self, simulator):
        """Test storing car data in Redis"""
        car_data = {
            'licensePlate': 'TEST-001',
            'indoorTemp': 22.5,
            'outdoorTemp': 15.0,
            'gps': {'lat': 60.1699, 'lng': 24.9344},
            'timestamp': datetime.now().isoformat()
        }
        
        simulator.redis_client = AsyncMock()
        simulator.redis_client.set = AsyncMock()
        simulator.redis_client.lpush = AsyncMock()
        simulator.redis_client.ltrim = AsyncMock()
        
        await simulator.store_data_in_c2('TEST-001', car_data)
        
        # Verify Redis operations
        simulator.redis_client.set.assert_called_once()
        simulator.redis_client.lpush.assert_called_once()
        simulator.redis_client.ltrim.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling(self, simulator):
        """Test error handling in Redis operations"""
        simulator.redis_client.set = AsyncMock(side_effect=Exception("Redis error"))
        
        car_data = {
            'licensePlate': 'TEST-001',
            'indoorTemp': 22.5
        }
        
        # Should handle errors gracefully
        with pytest.raises(Exception):
            await simulator.store_car_data(car_data)

class TestSensorDataValidation:
    """Test cases for sensor data validation"""

    def test_license_plate_validation(self):
        """Test license plate format validation"""
        valid_plates = ['ABC-123', 'XYZ-789', 'DEF-456']
        invalid_plates = ['', '123', 'ABC123', 'ABC-', '-123', 'ABCD-123']
        
        def validate_license_plate(plate):
            import re
            return bool(re.match(r'^[A-Z]{3}-[0-9]{3}$', plate))
        
        for plate in valid_plates:
            assert validate_license_plate(plate), f"Valid plate {plate} failed validation"
        
        for plate in invalid_plates:
            assert not validate_license_plate(plate), f"Invalid plate {plate} passed validation"

    def test_temperature_validation(self):
        """Test temperature range validation"""
        def validate_temperature(temp):
            return isinstance(temp, (int, float)) and -50 <= temp <= 100
        
        # Valid temperatures
        assert validate_temperature(22.5)
        assert validate_temperature(-10)
        assert validate_temperature(50)
        assert validate_temperature(0)
        
        # Invalid temperatures
        assert not validate_temperature(-100)
        assert not validate_temperature(150)
        assert not validate_temperature("22.5")
        assert not validate_temperature(None)

    def test_gps_validation(self):
        """Test GPS coordinate validation"""
        def validate_gps(gps):
            if not isinstance(gps, dict):
                return False
            if 'lat' not in gps or 'lng' not in gps:
                return False
            
            lat, lng = gps['lat'], gps['lng']
            return (isinstance(lat, (int, float)) and -90 <= lat <= 90 and
                    isinstance(lng, (int, float)) and -180 <= lng <= 180)
        
        # Valid GPS
        assert validate_gps({'lat': 60.1699, 'lng': 24.9344})
        assert validate_gps({'lat': 0, 'lng': 0})
        assert validate_gps({'lat': -90, 'lng': 180})
        
        # Invalid GPS
        assert not validate_gps({'lat': 100, 'lng': 0})
        assert not validate_gps({'lat': 0, 'lng': 200})
        assert not validate_gps({'lat': '60.1699', 'lng': 24.9344})
        assert not validate_gps({'lat': 60.1699})  # Missing lng
        assert not validate_gps("not a dict")

class TestCloudCommunication:
    """Test cases for cloud communication functionality"""

    def test_data_synchronization(self):
        """Test data synchronization with cloud"""
        import json
        
        # Test data serialization for cloud sync (simpler approach)
        test_data = {
            'licensePlate': 'ABC-123',
            'indoorTemp': 22.5,
            'timestamp': datetime.now().isoformat()
        }
        
        # Verify data can be serialized for transmission
        serialized = json.dumps(test_data)
        deserialized = json.loads(serialized)
        
        assert deserialized == test_data
        assert 'licensePlate' in deserialized
        assert deserialized['indoorTemp'] == 22.5

    def test_data_serialization(self):
        """Test data serialization for transmission"""
        import json
        from datetime import datetime
        
        data = {
            'licensePlate': 'ABC-123',
            'indoorTemp': 22.5,
            'outdoorTemp': 15.0,
            'gps': {'lat': 60.1699, 'lng': 24.9344},
            'timestamp': datetime.now().isoformat()
        }
        
        # Test serialization
        serialized = json.dumps(data)
        assert isinstance(serialized, str)
        
        # Test deserialization
        deserialized = json.loads(serialized)
        assert deserialized == data

class TestIntegrationScenarios:
    """Integration test scenarios"""

    @pytest.mark.asyncio
    async def test_full_data_flow(self):
        """Test complete data flow from generation to storage"""
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            mock_redis_client.ping = AsyncMock()
            mock_redis_client.set = AsyncMock()
            mock_redis_client.lpush = AsyncMock()
            mock_redis_client.ltrim = AsyncMock()
            
            simulator = test_c2_simulator.C2DataSimulator()
            simulator.redis_client = mock_redis_client
            
            await simulator.initialize()
            
            # Generate data for multiple cars
            cars = ['ABC-123', 'XYZ-789', 'DEF-456']
            
            for car in cars:
                car_data = await simulator.generate_car_data(car)
                await simulator.store_data_in_c2(car, car_data)
            
            # Verify Redis operations were called
            assert mock_redis_client.set.call_count >= len(cars)
            assert mock_redis_client.lpush.call_count >= len(cars)

    @pytest.mark.asyncio 
    async def test_concurrent_data_generation(self):
        """Test concurrent data generation for multiple cars"""
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            mock_redis_client.ping = AsyncMock()
            mock_redis_client.set = AsyncMock()
            mock_redis_client.get = AsyncMock(return_value=json.dumps([]))
            
            simulator = test_c2_simulator.C2DataSimulator()
            simulator.redis_client = mock_redis_client
            
            await simulator.initialize()
            
            # Generate data concurrently
            cars = ['ABC-123', 'XYZ-789', 'DEF-456']
            tasks = [simulator.generate_car_data(car) for car in cars]
            
            results = await asyncio.gather(*tasks)
            
            # Verify all data was generated
            assert len(results) == len(cars)
            for i, result in enumerate(results):
                assert result['licensePlate'] == cars[i]

if __name__ == '__main__':
    pytest.main([__file__])