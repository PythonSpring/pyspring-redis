import time
import pytest
from unittest.mock import MagicMock, patch
from redis import RedisError, ConnectionError
from threading import Lock
from redis import Redis

from py_spring_redis.redis_client import RedisBeanCollection, RedisClient, RedisProperties


@pytest.fixture
def redis_properties() -> RedisProperties:
    # Mock RedisProperties
    return RedisProperties(host="localhost", port=6379, db=0, heartbeat_interval=1)


@pytest.fixture
def redis_client(redis_properties: RedisProperties) -> RedisClient:
    # Create RedisClient with mock properties
    client = RedisClient()
    client.redis_properties = redis_properties
    client._lock = Lock()
    RedisBeanCollection.redis_properties = redis_properties
    return client


@patch("py_spring_redis.redis_client.RedisBeanCollection.create_redis")
def test_redis_client_init(mock_create_redis: MagicMock, redis_client: RedisClient) -> None:
    # Mock Redis instance
    mock_redis = MagicMock(spec=Redis)
    mock_create_redis.return_value = mock_redis

    # Call post_construct to initialize redis and start heartbeat thread
    redis_client.post_construct()

    # Check that Redis connection is established
    assert redis_client._redis == mock_redis
    mock_create_redis.assert_called_once()


@patch("py_spring_redis.redis_client.Redis")
def test_redis_set(mock_redis_class: MagicMock, redis_client: RedisClient) -> None:
    # Mock Redis instance and its 'set' method
    mock_redis = MagicMock(spec=Redis)
    redis_client._redis = mock_redis

    # Call the set method
    redis_client.set("test_key", "test_value")

    # Ensure Redis 'set' was called with the correct arguments
    mock_redis.set.assert_called_once_with("test_key", "test_value")


@patch("py_spring_redis.redis_client.Redis")
def test_redis_get(mock_redis_class: MagicMock, redis_client: RedisClient) -> None:
    # Mock Redis instance and its 'get' method
    mock_redis = MagicMock(spec=Redis)
    redis_client._redis = mock_redis
    mock_redis.get.return_value = b"test_value"

    # Call the get method
    result = redis_client.get("test_key")

    # Ensure Redis 'get' was called with the correct key
    mock_redis.get.assert_called_once_with("test_key")

    # Check the result is decoded correctly
    assert result == "test_value"


@patch("py_spring_redis.redis_client.Redis")
def test_redis_delete(mock_redis_class: MagicMock, redis_client: RedisClient) -> None:
    # Mock Redis instance and its 'delete' method
    mock_redis = MagicMock(spec=Redis)
    redis_client._redis = mock_redis

    # Call the delete method
    redis_client.delete("test_key")

    # Ensure Redis 'delete' was called with the correct key
    mock_redis.delete.assert_called_once_with("test_key")


@patch("py_spring_redis.redis_client.Redis")
def test_redis_get_key_not_found(mock_redis_class: MagicMock, redis_client: RedisClient) -> None:
    # Mock Redis instance and its 'get' method
    mock_redis = MagicMock(spec=Redis)
    redis_client._redis = mock_redis
    mock_redis.get.return_value = None  # Simulate key not found

    # Call the get method
    result = redis_client.get("missing_key")

    # Ensure Redis 'get' was called
    mock_redis.get.assert_called_once_with("missing_key")

    # Ensure result is None for missing key
    assert result is None


@patch("py_spring_redis.redis_client.Redis")
def test_redis_error_handling(mock_redis_class: MagicMock, redis_client: RedisClient) -> None:
    # Mock Redis instance and its methods
    mock_redis = MagicMock(spec=Redis)
    redis_client._redis = mock_redis

    # Simulate RedisError for set operation
    mock_redis.set.side_effect = RedisError("Redis error")

    # Call set method, expect no exception due to error handler
    redis_client.set("test_key", "test_value")

    # Ensure Redis 'set' was called but handled the error
    mock_redis.set.assert_called_once_with("test_key", "test_value")


@patch("py_spring_redis.redis_client.Redis")
def test_is_connected_success(mock_redis: MagicMock, redis_client: RedisClient) -> None:
    # Mock Redis instance and ping method

    redis_client._redis = mock_redis

    # Simulate successful ping
    mock_redis.ping.return_value = True

    # Call is_connected and ensure it returns True
    assert redis_client.is_connected() is True
    mock_redis.ping.assert_called_once()


@patch("py_spring_redis.redis_client.Redis")
def test_is_connected_failure(mock_redis: MagicMock, redis_client: RedisClient) -> None:
    redis_client._redis = mock_redis

    mock_redis.ping.side_effect = ConnectionError("Connection error")

    # Call is_connected and ensure it returns False
    assert redis_client.is_connected() is False
    mock_redis.ping.assert_called_once()