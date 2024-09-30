import json
from typing import Generic, Optional, Type, TypeVar, get_args
from loguru import logger

from py_spring import Component

from py_spring_redis.commons import RedisKeyDocument
from py_spring_redis.redis_client import RedisClient

T = TypeVar("T", bound=RedisKeyDocument)


class RedisCrudRepository(Component, Generic[T]):
    _redis_client: RedisClient

    def __init__(self) -> None:
        self._model_cls = self._get_model_class()
        if self._model_cls is None:
            return
        self._key_prefix = self._model_cls.get_document_key_base_name()

    @classmethod
    def _get_model_class(cls) -> Optional[Type[T]]:
        generic_type: tuple[Type[T]] = get_args(tp=cls.__mro__[0].__orig_bases__[0])
        if len(generic_type) == 0:
            return

        return generic_type[-1]

    def save(self, document: T) -> Optional[T]:
        value = self._redis_client.set(
            document.get_document_id(), document.model_dump_json()
        )
        if value is None:
            logger.error(f"[SAVE DOCUMENT FAIELD] Failed to save document {document}")
            return

        return document

    def find_by_id(self, id: str) -> Optional[T]:
        _key = f"{self._key_prefix}:{id}"
        value = self._redis_client.get(_key)
        if value is None:
            return
        if self._model_cls is None:
            return

        return self._model_cls.model_validate({"id": _key, **json.loads(value)})

    def find_all(self) -> list[T]:
        if self._model_cls is None:
            return []

        return self._redis_client.get_all_values_by_document_type(self._model_cls)

    def delete(self, document: T) -> None:
        self._redis_client.delete(document.get_document_id())
