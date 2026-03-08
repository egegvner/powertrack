"""Very simple backend: multiply duration by a provided constant power (W).
Useful as a baseline and for environments without sensors.
"""
import time
from typing import Dict, Optional

class TimeBackend:
    name = "time_based"

    def __init__(self, avg_power_w: float = 15.0):
        self.avg_power_w = avg_power_w

    def start(self):
        self._t0 = time.perf_counter()

    def stop(self) -> Dict[str, float]:
        t1 = time.perf_counter()
        duration = t1 - self._t0
        energy = duration * self.avg_power_w
        return {"duration": duration, "energy_j": energy, "avg_power_w": self.avg_power_w}
