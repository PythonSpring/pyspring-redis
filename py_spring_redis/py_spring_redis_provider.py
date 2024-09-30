from py_spring import EntityProvider

from py_spring_redis.redis_client import RedisClient, RedisProperties
from py_spring_redis.redis_crud_repository import RedisCrudRepository


def provide_py_spring_redis() -> EntityProvider:
    provider = EntityProvider(
        component_classes=[RedisClient, RedisCrudRepository],
        properties_classes=[RedisProperties],
    )
    return provider
