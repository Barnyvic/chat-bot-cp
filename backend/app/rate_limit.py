import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.time()
        request_times = self._requests[key]

        while request_times and now - request_times[0] > self.window_seconds:
            request_times.popleft()

        if len(request_times) >= self.limit:
            return False

        request_times.append(now)
        return True
