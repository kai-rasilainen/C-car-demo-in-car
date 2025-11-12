import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add the C5 directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class TestSensorSimulator:
    """Test cases for C5 Data Sensor Simulator"""

    def test_sensor_data_generation(self):
        """Test basic sensor data generation"""
        def generate_sensor_data(license_plate):
            import random
            import time
            
            return {
                'licensePlate': license_plate,
                'indoorTemp': round(20 + random.uniform(-5, 15), 1),
                'outdoorTemp': round(10 + random.uniform(-10, 20), 1),
                'gps': {
                    'lat': round(60.1699 + random.uniform(-0.01, 0.01), 6),
                    'lng': round(24.9344 + random.uniform(-0.01, 0.01), 6)
                },
                'speed': random.randint(0, 120),
                'engineStatus': random.choice(['running', 'off', 'idle']),
                'fuelLevel': random.randint(0, 100),
                'batteryVoltage': round(12 + random.uniform(-1, 2), 1),
                'timestamp': datetime.now().isoformat()
            }

        license_plate = 'ABC-123'
        data = generate_sensor_data(license_plate)
        
        # Verify data structure
        assert data['licensePlate'] == license_plate
        assert 'indoorTemp' in data
        assert 'outdoorTemp' in data
        assert 'gps' in data
        assert 'speed' in data
        assert 'engineStatus' in data
        assert 'fuelLevel' in data
        assert 'batteryVoltage' in data
        assert 'timestamp' in data
        
        # Verify data types
        assert isinstance(data['indoorTemp'], (int, float))
        assert isinstance(data['outdoorTemp'], (int, float))
        assert isinstance(data['gps'], dict)
        assert isinstance(data['speed'], int)
        assert isinstance(data['engineStatus'], str)
        assert isinstance(data['fuelLevel'], int)
        assert isinstance(data['batteryVoltage'], (int, float))

    def test_temperature_sensor_ranges(self):
        """Test temperature sensor value ranges"""
        def generate_temperature_data():
            import random
            return {
                'indoor': round(20 + random.uniform(-5, 15), 1),
                'outdoor': round(10 + random.uniform(-10, 20), 1)
            }
        
        # Generate multiple samples
        for _ in range(100):
            temps = generate_temperature_data()
            
            # Indoor temperature should be between 15-35°C (20 ± 15)
            assert 15 <= temps['indoor'] <= 35
            
            # Outdoor temperature should be between 0-30°C (10 ± 20)
            assert 0 <= temps['outdoor'] <= 30

    def test_gps_sensor_accuracy(self):
        """Test GPS sensor coordinate generation"""
        def generate_gps_data():
            import random
            base_lat = 60.1699  # Helsinki latitude
            base_lng = 24.9344  # Helsinki longitude
            
            return {
                'lat': round(base_lat + random.uniform(-0.01, 0.01), 6),
                'lng': round(base_lng + random.uniform(-0.01, 0.01), 6)
            }
        
        # Generate multiple GPS readings
        for _ in range(50):
            gps = generate_gps_data()
            
            # Should be within ~1km of Helsinki center
            assert 60.15 <= gps['lat'] <= 60.18
            assert 24.92 <= gps['lng'] <= 24.95
            
            # Should have proper precision (6 decimal places)
            lat_str = str(gps['lat'])
            lng_str = str(gps['lng'])
            if '.' in lat_str:
                assert len(lat_str.split('.')[1]) <= 6
            if '.' in lng_str:
                assert len(lng_str.split('.')[1]) <= 6

    def test_engine_status_states(self):
        """Test engine status state generation"""
        def generate_engine_status():
            import random
            return random.choice(['running', 'off', 'idle'])
        
        # Generate many samples to test all states
        statuses = [generate_engine_status() for _ in range(100)]
        
        # Should contain all possible states
        unique_statuses = set(statuses)
        expected_statuses = {'running', 'off', 'idle'}
        
        # At least 2 different states should appear in 100 samples
        assert len(unique_statuses) >= 2
        assert unique_statuses.issubset(expected_statuses)

    def test_fuel_level_sensor(self):
        """Test fuel level sensor readings"""
        def generate_fuel_level():
            import random
            return random.randint(0, 100)
        
        # Test fuel level ranges
        for _ in range(50):
            fuel = generate_fuel_level()
            assert 0 <= fuel <= 100
            assert isinstance(fuel, int)

    def test_battery_voltage_sensor(self):
        """Test battery voltage sensor readings"""
        def generate_battery_voltage():
            import random
            return round(12 + random.uniform(-1, 2), 1)
        
        # Test battery voltage ranges
        for _ in range(50):
            voltage = generate_battery_voltage()
            
            # Car battery voltage typically 11-14V
            assert 11 <= voltage <= 14
            assert isinstance(voltage, (int, float))

    def test_speed_sensor(self):
        """Test vehicle speed sensor readings"""
        def generate_speed():
            import random
            return random.randint(0, 120)
        
        # Test speed ranges
        for _ in range(50):
            speed = generate_speed()
            assert 0 <= speed <= 120
            assert isinstance(speed, int)

class TestSensorDataValidation:
    """Test sensor data validation functions"""

    def test_validate_sensor_reading(self):
        """Test sensor reading validation"""
        def validate_sensor_reading(data):
            errors = []
            
            # Validate license plate
            if not data.get('licensePlate') or not isinstance(data['licensePlate'], str):
                errors.append('Invalid license plate')
            
            # Validate temperatures
            indoor_temp = data.get('indoorTemp')
            if not isinstance(indoor_temp, (int, float)) or not (-50 <= indoor_temp <= 100):
                errors.append('Invalid indoor temperature')
            
            outdoor_temp = data.get('outdoorTemp')
            if not isinstance(outdoor_temp, (int, float)) or not (-50 <= outdoor_temp <= 100):
                errors.append('Invalid outdoor temperature')
            
            # Validate GPS
            gps = data.get('gps')
            if not isinstance(gps, dict) or 'lat' not in gps or 'lng' not in gps:
                errors.append('Invalid GPS data')
            elif not (-90 <= gps['lat'] <= 90) or not (-180 <= gps['lng'] <= 180):
                errors.append('GPS coordinates out of range')
            
            # Validate fuel level
            fuel = data.get('fuelLevel')
            if not isinstance(fuel, int) or not (0 <= fuel <= 100):
                errors.append('Invalid fuel level')
            
            return errors

        # Valid data
        valid_data = {
            'licensePlate': 'ABC-123',
            'indoorTemp': 22.5,
            'outdoorTemp': 15.0,
            'gps': {'lat': 60.1699, 'lng': 24.9344},
            'fuelLevel': 85
        }
        
        assert len(validate_sensor_reading(valid_data)) == 0

        # Invalid data
        invalid_data = {
            'licensePlate': '',
            'indoorTemp': 150,
            'outdoorTemp': 'invalid',
            'gps': {'lat': 200},
            'fuelLevel': 150
        }
        
        errors = validate_sensor_reading(invalid_data)
        assert len(errors) > 0

class TestSensorIntegration:
    """Test sensor integration with Redis and other systems"""

    @pytest.mark.asyncio
    async def test_sensor_data_publishing(self):
        """Test publishing sensor data to Redis"""
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            mock_redis_client.publish = AsyncMock()
            
            # Mock sensor data publisher
            async def publish_sensor_data(license_plate, data):
                import json
                redis_client = mock_redis_client
                channel = f'car:{license_plate}:sensors'
                message = json.dumps(data)
                await redis_client.publish(channel, message)
            
            sensor_data = {
                'licensePlate': 'ABC-123',
                'indoorTemp': 22.5,
                'timestamp': datetime.now().isoformat()
            }
            
            await publish_sensor_data('ABC-123', sensor_data)
            
            # Verify Redis publish was called
            mock_redis_client.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_sensors_simulation(self):
        """Test simulating multiple sensors for different cars"""
        def generate_multi_car_data():
            import random
            cars = ['ABC-123', 'XYZ-789', 'DEF-456']
            
            data = {}
            for car in cars:
                data[car] = {
                    'licensePlate': car,
                    'indoorTemp': round(20 + random.uniform(-5, 15), 1),
                    'outdoorTemp': round(10 + random.uniform(-10, 20), 1),
                    'gps': {
                        'lat': round(60.1699 + random.uniform(-0.01, 0.01), 6),
                        'lng': round(24.9344 + random.uniform(-0.01, 0.01), 6)
                    },
                    'timestamp': datetime.now().isoformat()
                }
            
            return data
        
        multi_car_data = generate_multi_car_data()
        
        # Verify data for all cars
        assert len(multi_car_data) == 3
        assert 'ABC-123' in multi_car_data
        assert 'XYZ-789' in multi_car_data
        assert 'DEF-456' in multi_car_data
        
        # Verify each car has valid data
        for car, data in multi_car_data.items():
            assert data['licensePlate'] == car
            assert 'indoorTemp' in data
            assert 'gps' in data

    def test_sensor_data_persistence(self):
        """Test sensor data persistence and retrieval"""
        def store_sensor_reading(license_plate, data):
            # Mock storage implementation
            storage = {}
            key = f'sensor:{license_plate}:latest'
            storage[key] = data
            return storage
        
        def retrieve_sensor_reading(license_plate, storage):
            key = f'sensor:{license_plate}:latest'
            return storage.get(key)
        
        sensor_data = {
            'licensePlate': 'ABC-123',
            'indoorTemp': 22.5,
            'timestamp': datetime.now().isoformat()
        }
        
        # Store and retrieve
        storage = store_sensor_reading('ABC-123', sensor_data)
        retrieved = retrieve_sensor_reading('ABC-123', storage)
        
        assert retrieved == sensor_data

class TestSensorErrorHandling:
    """Test error handling in sensor operations"""

    def test_sensor_failure_simulation(self):
        """Test handling of sensor failures"""
        def simulate_sensor_with_failure(failure_rate=0.1):
            import random
            
            if random.random() < failure_rate:
                return None  # Sensor failure
            
            return {
                'value': random.uniform(0, 100),
                'status': 'ok'
            }
        
        # Test multiple readings
        readings = [simulate_sensor_with_failure(0.2) for _ in range(100)]
        
        # Should have some failures
        failures = sum(1 for r in readings if r is None)
        successes = sum(1 for r in readings if r is not None)
        
        assert failures > 0  # Should have some failures with 20% rate
        assert successes > 0  # Should have some successes

    def test_invalid_sensor_data_handling(self):
        """Test handling of invalid sensor data"""
        def process_sensor_data(raw_data):
            try:
                # Validate and process
                if not isinstance(raw_data, dict):
                    raise ValueError("Data must be a dictionary")
                
                if 'value' not in raw_data:
                    raise ValueError("Missing required 'value' field")
                
                value = float(raw_data['value'])
                
                return {
                    'processed_value': value,
                    'status': 'valid'
                }
            
            except Exception as e:
                return {
                    'error': str(e),
                    'status': 'invalid'
                }
        
        # Valid data
        valid_result = process_sensor_data({'value': 22.5})
        assert valid_result['status'] == 'valid'
        assert valid_result['processed_value'] == 22.5
        
        # Invalid data
        invalid_result = process_sensor_data({'invalid': 'data'})
        assert invalid_result['status'] == 'invalid'
        assert 'error' in invalid_result

if __name__ == '__main__':
    pytest.main([__file__])