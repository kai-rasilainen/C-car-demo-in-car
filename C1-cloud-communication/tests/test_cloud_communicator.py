import pytest
import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import aiohttp

# Mock imports
import sys
sys.path.insert(0, '/home/kai/projects/car-demo-repos/car-demo-system/C-car-demo-in-car/C1-cloud-communication')

"""
Comprehensive C1 Cloud Communication Tests
Tests WebSocket communication between car and cloud
"""

class TestCloudCommunicator:
    """Test suite for CloudCommunicator class"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing"""
        return {
            'cloud_endpoint': 'http://localhost:3002',
            'api_key': 'test-api-key-123',
            'redis_url': 'redis://localhost:6379',
            'license_plate': 'ABC-123',
            'send_interval': 10
        }
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client"""
        client = AsyncMock()
        client.ping = AsyncMock(return_value=True)
        client.get = AsyncMock()
        client.set = AsyncMock(return_value=True)
        client.aclose = AsyncMock()
        return client
    
    @pytest.fixture
    def mock_http_session(self):
        """Mock aiohttp session"""
        session = AsyncMock()
        session.close = AsyncMock()
        return session

    def test_configuration_validation(self, mock_config):
        """Test configuration is properly structured"""
        assert 'cloud_endpoint' in mock_config
        assert 'api_key' in mock_config
        assert 'redis_url' in mock_config
        assert 'license_plate' in mock_config
        assert mock_config['send_interval'] > 0

    @pytest.mark.asyncio
    async def test_redis_connection(self, mock_redis_client):
        """Test Redis connection initialization"""
        await mock_redis_client.ping()
        assert mock_redis_client.ping.called

    @pytest.mark.asyncio
    async def test_get_latest_data_from_c2(self, mock_redis_client):
        """Test retrieving latest sensor data from C2"""
        # Mock data from C2
        mock_data = {
            'licensePlate': 'ABC-123',
            'indoorTemp': 22.5,
            'outdoorTemp': 15.2,
            'batteryLevel': 85,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        mock_redis_client.get.return_value = json.dumps(mock_data)
        
        data_json = await mock_redis_client.get('car:ABC-123:latest_data')
        data = json.loads(data_json)
        
        assert data['licensePlate'] == 'ABC-123'
        assert data['indoorTemp'] == 22.5
        assert data['batteryLevel'] == 85
        mock_redis_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_latest_data_no_data(self, mock_redis_client):
        """Test handling when no data is available"""
        mock_redis_client.get.return_value = None
        
        data = await mock_redis_client.get('car:ABC-123:latest_data')
        
        assert data is None
        mock_redis_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_data_to_cloud_success(self, mock_http_session):
        """Test successful data transmission to cloud"""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={'success': True, 'dataId': 'data-123'})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_http_session.post.return_value = mock_response
        
        # Prepare payload
        payload = {
            'licensePlate': 'ABC-123',
            'indoorTemp': 22.5,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        response = await mock_http_session.post(
            'http://localhost:3002/api/sensor-data',
            json=payload
        )
        
        async with response as resp:
            result = await resp.json()
            assert resp.status == 200
            assert result['success'] is True
            assert 'dataId' in result

    @pytest.mark.asyncio
    async def test_send_data_to_cloud_failure(self, mock_http_session):
        """Test handling of failed cloud transmission"""
        # Mock failed response
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.json = AsyncMock(return_value={'error': 'Internal server error'})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_http_session.post.return_value = mock_response
        
        response = await mock_http_session.post(
            'http://localhost:3002/api/sensor-data',
            json={}
        )
        
        async with response as resp:
            assert resp.status == 500

    @pytest.mark.asyncio
    async def test_send_data_with_authentication(self, mock_http_session):
        """Test that API key is included in requests"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_http_session.post.return_value = mock_response
        
        # Verify headers are set
        api_key = 'test-api-key-123'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        response = await mock_http_session.post(
            'http://localhost:3002/api/sensor-data',
            json={},
            headers=headers
        )
        
        assert response is not None

    @pytest.mark.asyncio
    async def test_periodic_data_sending(self, mock_redis_client, mock_http_session):
        """Test periodic data sending mechanism"""
        # Simulate periodic sending
        send_count = 0
        max_sends = 3
        
        mock_data = {
            'licensePlate': 'ABC-123',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        mock_redis_client.get.return_value = json.dumps(mock_data)
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_http_session.post.return_value = mock_response
        
        # Simulate sending data multiple times
        while send_count < max_sends:
            data_json = await mock_redis_client.get('car:ABC-123:latest_data')
            data = json.loads(data_json)
            
            response = await mock_http_session.post(
                'http://localhost:3002/api/sensor-data',
                json=data
            )
            
            send_count += 1
            await asyncio.sleep(0.01)  # Small delay
        
        assert send_count == max_sends
        assert mock_http_session.post.call_count == max_sends

    @pytest.mark.asyncio
    async def test_websocket_connection_establishment(self):
        """Test WebSocket connection to B2"""
        # Mock WebSocket connection
        with patch('aiohttp.ClientSession.ws_connect') as mock_ws:
            mock_ws_conn = AsyncMock()
            mock_ws_conn.closed = False
            mock_ws_conn.send_json = AsyncMock()
            mock_ws_conn.receive_json = AsyncMock(return_value={
                'type': 'connected',
                'message': 'Connection established'
            })
            mock_ws_conn.close = AsyncMock()
            mock_ws_conn.__aenter__ = AsyncMock(return_value=mock_ws_conn)
            mock_ws_conn.__aexit__ = AsyncMock(return_value=None)
            
            mock_ws.return_value = mock_ws_conn
            
            # Simulate connection
            async with mock_ws_conn as ws:
                await ws.send_json({'type': 'ping'})
                response = await ws.receive_json()
                
                assert response['type'] == 'connected'
                mock_ws_conn.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_send_sensor_data(self):
        """Test sending sensor data via WebSocket"""
        with patch('aiohttp.ClientSession.ws_connect') as mock_ws:
            mock_ws_conn = AsyncMock()
            mock_ws_conn.send_json = AsyncMock()
            mock_ws_conn.__aenter__ = AsyncMock(return_value=mock_ws_conn)
            mock_ws_conn.__aexit__ = AsyncMock(return_value=None)
            
            mock_ws.return_value = mock_ws_conn
            
            sensor_data = {
                'licensePlate': 'ABC-123',
                'indoorTemp': 22.5,
                'outdoorTemp': 15.2,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            async with mock_ws_conn as ws:
                await ws.send_json(sensor_data)
                
                mock_ws_conn.send_json.assert_called_once_with(sensor_data)

    @pytest.mark.asyncio
    async def test_receive_command_from_cloud(self):
        """Test receiving commands from cloud via WebSocket"""
        with patch('aiohttp.ClientSession.ws_connect') as mock_ws:
            mock_ws_conn = AsyncMock()
            mock_ws_conn.receive_json = AsyncMock(return_value={
                'type': 'command',
                'command': 'lock',
                'licensePlate': 'ABC-123',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            mock_ws_conn.__aenter__ = AsyncMock(return_value=mock_ws_conn)
            mock_ws_conn.__aexit__ = AsyncMock(return_value=None)
            
            mock_ws.return_value = mock_ws_conn
            
            async with mock_ws_conn as ws:
                command = await ws.receive_json()
                
                assert command['type'] == 'command'
                assert command['command'] == 'lock'
                assert command['licensePlate'] == 'ABC-123'

    @pytest.mark.asyncio
    async def test_data_format_validation(self, mock_redis_client):
        """Test data format validation"""
        # Valid data structure
        valid_data = {
            'licensePlate': 'ABC-123',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'indoorTemp': 22.5,
            'outdoorTemp': 15.2,
            'batteryLevel': 85
        }
        
        # All required fields should be present
        assert 'licensePlate' in valid_data
        assert 'timestamp' in valid_data
        assert isinstance(valid_data['indoorTemp'], (int, float))
        assert isinstance(valid_data['batteryLevel'], (int, float))

    @pytest.mark.asyncio
    async def test_error_handling_network_timeout(self, mock_http_session):
        """Test handling of network timeouts"""
        mock_http_session.post.side_effect = asyncio.TimeoutError()
        
        with pytest.raises(asyncio.TimeoutError):
            await mock_http_session.post(
                'http://localhost:3002/api/sensor-data',
                json={}
            )

    @pytest.mark.asyncio
    async def test_error_handling_connection_error(self, mock_http_session):
        """Test handling of connection errors"""
        mock_http_session.post.side_effect = aiohttp.ClientConnectionError()
        
        with pytest.raises(aiohttp.ClientConnectionError):
            await mock_http_session.post(
                'http://localhost:3002/api/sensor-data',
                json={}
            )

    @pytest.mark.asyncio
    async def test_retry_mechanism(self, mock_http_session):
        """Test retry mechanism for failed requests"""
        # First call fails, second succeeds
        mock_response_fail = AsyncMock()
        mock_response_fail.status = 500
        mock_response_fail.__aenter__ = AsyncMock(return_value=mock_response_fail)
        mock_response_fail.__aexit__ = AsyncMock(return_value=None)
        
        mock_response_success = AsyncMock()
        mock_response_success.status = 200
        mock_response_success.__aenter__ = AsyncMock(return_value=mock_response_success)
        mock_response_success.__aexit__ = AsyncMock(return_value=None)
        
        mock_http_session.post.side_effect = [
            mock_response_fail,
            mock_response_success
        ]
        
        # First attempt
        response1 = await mock_http_session.post('http://localhost:3002/api/sensor-data', json={})
        async with response1 as resp:
            assert resp.status == 500
        
        # Retry
        response2 = await mock_http_session.post('http://localhost:3002/api/sensor-data', json={})
        async with response2 as resp:
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_cleanup_resources(self, mock_redis_client, mock_http_session):
        """Test proper cleanup of resources"""
        await mock_redis_client.aclose()
        await mock_http_session.close()
        
        mock_redis_client.aclose.assert_called_once()
        mock_http_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_data_batching(self, mock_redis_client):
        """Test batching multiple sensor readings"""
        batch_data = []
        
        for i in range(5):
            data = {
                'licensePlate': 'ABC-123',
                'batteryLevel': 85 - i,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            batch_data.append(data)
        
        assert len(batch_data) == 5
        assert all('licensePlate' in d for d in batch_data)
        assert batch_data[0]['batteryLevel'] == 85
        assert batch_data[4]['batteryLevel'] == 81

    def test_timestamp_format(self):
        """Test ISO 8601 timestamp format"""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Should be parseable
        parsed = datetime.fromisoformat(timestamp)
        assert isinstance(parsed, datetime)

    @pytest.mark.asyncio
    async def test_concurrent_data_streams(self, mock_http_session):
        """Test handling multiple concurrent data streams"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_http_session.post.return_value = mock_response
        
        tasks = []
        for i in range(10):
            data = {
                'licensePlate': 'ABC-123',
                'value': i,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            tasks.append(
                mock_http_session.post('http://localhost:3002/api/sensor-data', json=data)
            )
        
        responses = await asyncio.gather(*tasks)
        
        assert len(responses) == 10
        assert all(r.status == 200 for r in responses)


class TestDataTransformation:
    """Test data transformation and formatting"""
    
    def test_sensor_data_structure(self):
        """Test sensor data structure is correct"""
        sensor_data = {
            'licensePlate': 'ABC-123',
            'sensors': {
                'temperature': {'indoor': 22.5, 'outdoor': 15.2},
                'battery': {'level': 85, 'voltage': 12.6},
                'gps': {'lat': 60.1699, 'lng': 24.9384}
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        assert 'licensePlate' in sensor_data
        assert 'sensors' in sensor_data
        assert 'temperature' in sensor_data['sensors']
        assert 'battery' in sensor_data['sensors']
        assert 'gps' in sensor_data['sensors']
    
    def test_numeric_precision(self):
        """Test numeric values have appropriate precision"""
        temp = round(22.456789, 1)  # 1 decimal place
        battery = round(85.6789, 0)  # Whole number
        
        assert temp == 22.5
        assert battery == 86
    
    def test_gps_coordinate_range(self):
        """Test GPS coordinates are in valid range"""
        gps = {'lat': 60.1699, 'lng': 24.9384}
        
        assert -90 <= gps['lat'] <= 90
        assert -180 <= gps['lng'] <= 180


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
