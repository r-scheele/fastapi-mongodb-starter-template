from typing import TypeVar, Type, Callable

from aioredis import Redis
from injector import Injector, singleton

from common.database.redis import RedisManager
from common.config import cfg

injector = Injector()
T = TypeVar("T")


def on(dependency_class: Type[T]) -> Callable[[], T]:
    """Bridge between FastAPI injection and 'injector' DI framework."""
    return lambda: injector.get(dependency_class)


class Cache(Redis):
    """Cache injection token with code completion for Redis instance."""

    pass


class PubSubStore(Redis):
    """PubSubStore injection token with code completion for Redis instance."""

    pass


async def configure():
    """Create dependency injection graph and init services."""
    cache, pubsub = RedisManager(cfg.cache_uri), RedisManager(cfg.pubsub_uri)
    await cache.start()
    await pubsub.start()
    injector.binder.bind(Cache, to=cache.redis, scope=singleton)
    injector.binder.bind(PubSubStore, to=pubsub.redis, scope=singleton)
