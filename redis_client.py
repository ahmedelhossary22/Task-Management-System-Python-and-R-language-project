import redis
import os

def get_redis_client():
    try:
        host = "localhost"

        # if running in docker
        if os.getenv("DOCKER_ENV") == "true":
            host = "redis"

        client = redis.Redis(
            host=host,
            port=6379,
            db=0,
            decode_responses=True
        )

        client.ping()
        print(f" Redis connected at {host}")
        return client

    except Exception:
        print(" Redis not available → running without cache")
        return None

redis_client = get_redis_client()