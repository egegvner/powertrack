"""RAPL backend using pyRAPL (Intel RAPL counters).

This backend measures energy using the pyRAPL package (which wraps the kernel RAPL interface).
It reports package (PKG) and dram (DRAM) energies when available and returns their sum as energy_j.

Requirements: `pip install pyRAPL`

References:
- pyRAPL quickstart and API (pyrapl.readthedocs.io). 
"""
import time
from typing import Dict, List, Optional

try:
    import pyRAPL
except Exception:
    pyRAPL = None


class RAPLBackend:
    name = "rapl"

    def __init__(self, devices: Optional[List[str]] = None, socket_ids: Optional[List[int]] = None):
        if pyRAPL is None:
            raise RuntimeError("pyRAPL is required for RAPLBackend. Install with `pip install pyRAPL`")

        # Map simple strings to pyRAPL.Device constants if given
        devs = []
        if devices:
            for d in devices:
                key = d.upper()
                if hasattr(pyRAPL.Device, key):
                    devs.append(getattr(pyRAPL.Device, key))
        # if no devices specified, default to pyRAPL's default (all available)
        if devs:
            pyRAPL.setup(devices=devs, socket_ids=socket_ids)
        else:
            pyRAPL.setup(socket_ids=socket_ids)

        self._measure = None

    def start(self):
        # create the measurement object and begin recording
        self._measure = pyRAPL.Measurement("powertrack")
        self._measure.begin()
        self._t0 = time.time()

    def stop(self) -> Dict[str, float]:
        # end the measurement and extract results
        self._measure.end()
        self._t1 = time.time()
        duration = self._t1 - self._t0

        res = getattr(self._measure, "result", None)
        # Result has attributes: pkg (joules) and dram (joules) when available
        pkg = getattr(res, "pkg", 0.0) or 0.0
        dram = getattr(res, "dram", 0.0) or 0.0

        total_energy = float(pkg) + float(dram)
        avg_power = (total_energy / duration) if duration > 0 else 0.0

        return {"duration": duration, "energy_j": total_energy, "avg_power_w": avg_power, "pkg_j": float(pkg), "dram_j": float(dram)}
