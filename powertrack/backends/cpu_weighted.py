"""CPU-weighted backend using psutil to estimate CPU time consumed by process.
Estimates average power as: TDP * (cpu_time / wall_time).
Note: TDP should be calibrated for host machine.
"""
import time
import os
try:
    import psutil
except Exception:
    psutil = None

from typing import Dict, Optional

class CPUWeightedBackend:
    name = "cpu_weighted"

    def __init__(self, tdp_w: float = 28.0):
        self.tdp_w = tdp_w
        if psutil is None:
            raise RuntimeError("psutil is required for CPUWeightedBackend. Install with `pip install psutil`")
        self._proc = psutil.Process(os.getpid())

    def start(self):
        self._t0 = time.perf_counter()
        self._cpu_start = self._proc.cpu_times()

    def stop(self) -> Dict[str, float]:
        cpu_end = self._proc.cpu_times()
        t1 = time.perf_counter()
        duration = t1 - self._t0
        cpu_time = (cpu_end.user - self._cpu_start.user) + (cpu_end.system - self._cpu_start.system)
        # protect against zero-duration
        if duration <= 0:
            avg_power = 0.0
            energy = 0.0
        else:
            avg_power = self.tdp_w * (cpu_time / duration)
            energy = avg_power * duration
        return {"duration": duration, "energy_j": energy, "avg_power_w": avg_power, "cpu_time_s": cpu_time}
