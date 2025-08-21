# app/services/stats.py
import time
import threading


class Stats:
    """
    Tracks runtime statistics for the scoring service.
    Provides counters for monitoring and debugging.
    Thread-safe using a lock.
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.start_time = time.time()

        # Counters
        self.total_consumed = 0
        self.total_scored = 0
        self.total_failed = 0
        self.total_produced = 0

    def snapshot(self) -> dict:
        """
        Return a snapshot of current statistics.
        Useful for exposing via FastAPI /stats endpoint or Prometheus.
        """
        with self.lock:
            uptime = time.time() - self.start_time
            return {
                "uptime_seconds": round(uptime, 2),
                "total_consumed": self.total_consumed,
                "total_scored": self.total_scored,
                "total_failed": self.total_failed,
                "total_produced": self.total_produced,
            }

    def reset(self):
        """
        Reset counters (not uptime).
        Can be useful in testing.
        """
        with self.lock:
            self.total_consumed = 0
            self.total_scored = 0
            self.total_failed = 0
            self.total_produced = 0


# Global stats instance (shared across service)
stats = Stats()
