import time

from redis import Redis

from app.core.config import settings


class LoginRateLimiter:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    @staticmethod
    def _bucket(window_seconds: int) -> int:
        return int(time.time() // window_seconds)

    def _incr_window(self, key: str, ttl_seconds: int) -> int:
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl_seconds)
        value, _ = pipe.execute()
        return int(value)

    def check_allow(self, ip_address: str, username: str) -> tuple[bool, str | None]:
        normalized_username = username.strip().lower()

        ip_block_key = f"rl:login:block:ip:{ip_address}"
        user_block_key = f"rl:login:block:user:{normalized_username}:ip:{ip_address}"
        if self.redis.exists(ip_block_key) or self.redis.exists(user_block_key):
            return False, "Too many failed attempts. Try again later."

        minute_bucket = self._bucket(60)
        ip_key = f"rl:login:ip:{ip_address}:{minute_bucket}"
        user_key = f"rl:login:user:{normalized_username}:ip:{ip_address}:{minute_bucket}"

        ip_count = self._incr_window(ip_key, 61)
        user_count = self._incr_window(user_key, 61)

        if ip_count > settings.login_attempts_per_minute:
            return False, "Rate limit exceeded for IP."
        if user_count > settings.login_attempts_per_user_per_minute:
            return False, "Rate limit exceeded for username."
        return True, None

    def record_failure(self, ip_address: str, username: str) -> None:
        normalized_username = username.strip().lower()
        key = f"rl:login:fail:user:{normalized_username}:ip:{ip_address}"
        failures = self._incr_window(key, settings.login_failure_window_seconds)

        if failures >= settings.login_max_failures_before_block:
            ip_block_key = f"rl:login:block:ip:{ip_address}"
            user_block_key = f"rl:login:block:user:{normalized_username}:ip:{ip_address}"
            self.redis.setex(ip_block_key, settings.login_block_seconds, "1")
            self.redis.setex(user_block_key, settings.login_block_seconds, "1")

    def clear_failures(self, ip_address: str, username: str) -> None:
        normalized_username = username.strip().lower()
        key = f"rl:login:fail:user:{normalized_username}:ip:{ip_address}"
        user_block_key = f"rl:login:block:user:{normalized_username}:ip:{ip_address}"
        self.redis.delete(key, user_block_key)
