import json
import time
from threading import Thread
from typing import Optional, Type, TypeVar, cast

from loguru import logger
from py_spring import Component, Properties
from pydantic import Field
from redis import Redis

from py_spring_redis.commons import RedisKeyDocument

T = TypeVar("T", bound=RedisKeyDocument)


class RedisProperties(Properties):
    __key__ = "py_spring_redis"
    host: str
    port: int
    password: Optional[str] = Field(default=None)
    db: int
    heartbeat_interval: int = Field(default=10)


class RedisClient(Component):
    redis_properties: RedisProperties

    def _init_redis(self) -> Redis:
        redis = Redis(
            host=self.redis_properties.host,
            port=self.redis_properties.port,
            db=self.redis_properties.db,
            password=self.redis_properties.password,
        )
        logger.debug(
            f"[INIT REDIS CONNECTION] Redis connection established to {self.redis_properties.host}:{self.redis_properties.port}"
        )
        return redis

    def post_construct(self) -> None:
        self._redis = self._init_redis()
        self.start_redis_heart_beat_thread()

    def delete(self, key: str) -> None:
        self._redis.delete(key)

    def set(self, key: str, value: str):
        self._redis.set(key, value)

    def get(self, key: str) -> Optional[str]:
        value = self._redis.get(key)
        if value is None:
            return
        return cast(bytes, value).decode("utf-8")

    def get_all_values_by_document_type(self, document_type: Type[T]) -> list[T]:
        docs: list[T] = []
        for key in self._redis.scan_iter(
            f"{document_type.get_document_key_base_name()}:*"
        ):
            value = self._redis.get(key)
            if value is None:
                continue
            json_value = cast(bytes, value).decode("utf-8")
            current_doc = document_type.model_validate(
                {"id": key, **json.loads(json_value)}
            )
            docs.append(current_doc)
        return docs

    def is_connected(self) -> bool:
        try:
            self._redis.ping()
            return True
        except Exception:
            return False

    def start_redis_heart_beat_thread(self) -> None:
        logger.info("[REDIS HEARTBEAT THREAD] Starting redis heartbeat thread...")
        is_logged = False

        def wrapper():
            while True:
                nonlocal is_logged
                time.sleep(self.redis_properties.heartbeat_interval)
                if not self.is_connected():
                    logger.warning(
                        "[REDIS HEARTBEAT THREAD] Redis connection lost, reconnecting..."
                    )
                    self._init_redis()
                    is_logged = False
                if not is_logged:
                    logger.success(
                        "[REDIS HEARTBEAT THREAD] Redis connection reestablished"
                    )
                    is_logged = True

        Thread(target=wrapper, daemon=True).start()
