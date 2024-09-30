import functools
import json
import time
from threading import Lock, Thread
from typing import Any, Callable, Optional, Type, TypeVar, cast

from loguru import logger
from py_spring import Component, Properties, BeanCollection
from pydantic import Field
from redis import Redis, RedisError, ConnectionError

from py_spring_redis.commons import RedisKeyDocument

T = TypeVar("T", bound=RedisKeyDocument)


class RedisProperties(Properties):
    __key__ = "py_spring_redis"
    host: str
    port: int
    password: Optional[str] = Field(default=None)
    db: int
    heartbeat_interval: int = Field(default=10)


def redis_error_handler(func: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except (RedisError, ConnectionError) as error:
            logger.error(f"[REDIS ERROR] {func.__name__} failed: {error}")
            return  # Or handle it according to your needs

    return wrapper


def thread_safe(func: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(func)
    def wrapper(self: "RedisClient", *args, **kwargs) -> Any:
        with self._lock:
            return func(self, *args, **kwargs)

    return wrapper


class RedisBeanCollection(BeanCollection):
    redis_properties: RedisProperties

    @classmethod
    def create_redis(cls) -> Redis:
        return Redis(
            host=cls.redis_properties.host,
            port=cls.redis_properties.port,
            db=cls.redis_properties.db,
            password=cls.redis_properties.password,
            socket_timeout=5,
        )


class RedisClient(Component):
    redis_properties: RedisProperties
    _redis: Redis
    _lock: Lock

    def __init__(self):
        self._lock = Lock()

    def _init_redis(self) -> Redis:
        redis = RedisBeanCollection.create_redis()
        logger.debug(
            f"[INIT REDIS CONNECTION] Redis connection established to {self.redis_properties.host}:{self.redis_properties.port}"
        )
        return redis

    def post_construct(self) -> None:
        self._redis = self._init_redis()
        self.start_redis_heart_beat_thread()

    @thread_safe
    @redis_error_handler
    def delete(self, key: str) -> None:
        self._redis.delete(key)
        logger.info(f"[DELETE] Key '{key}' deleted from Redis")

    @thread_safe
    @redis_error_handler
    def set(self, key: str, value: str) -> str:
        self._redis.set(key, value)
        logger.info(f"[SET] Key '{key}' set to value '{value}'")
        return value

    @thread_safe
    @redis_error_handler
    def get(self, key: str) -> Optional[str]:
        value = self._redis.get(key)
        if value is None:
            logger.warning(f"[GET] Key '{key}' not found")
            return
        result = cast(bytes, value).decode("utf-8")
        logger.info(f"[GET] Retrieved value for key '{key}': {result}")
        return result

    @redis_error_handler
    def get_all_values_by_document_type(self, document_type: Type[T]) -> list[T]:
        docs: list[T] = []
        for key in self._redis.scan_iter(
            f"{document_type.get_document_key_base_name()}:*"
        ):
            value = self._redis.get(key)
            if value is None:
                logger.warning(f"[SCAN ITER] Key '{key}' not found")
                continue
            json_value = cast(bytes, value).decode("utf-8")
            current_doc = document_type.model_validate(
                {"id": key, **json.loads(json_value)}
            )
            docs.append(current_doc)
        logger.info(
            f"[GET ALL] Retrieved {len(docs)} documents of type '{document_type.__name__}'"
        )
        return docs

    def is_connected(self) -> bool:
        try:
            self._redis.ping()
            return True
        except (ConnectionError, RedisError) as e:
            logger.error(f"[IS CONNECTED ERROR] Redis connection error: {e}")
            return False

    def start_redis_heart_beat_thread(self) -> None:
        logger.info("[REDIS HEARTBEAT THREAD] Starting Redis heartbeat thread...")
        is_logged = False

        def wrapper():
            while True:
                nonlocal is_logged
                time.sleep(self.redis_properties.heartbeat_interval)
                if not self.is_connected():
                    logger.warning(
                        "[REDIS HEARTBEAT THREAD] Redis connection lost, reconnecting..."
                    )
                    with self._lock:
                        self._init_redis()
                        is_logged = False
                if not is_logged:
                    logger.success(
                        "[REDIS HEARTBEAT THREAD] Redis connection reestablished"
                    )
                    is_logged = True

        Thread(target=wrapper, daemon=True).start()
