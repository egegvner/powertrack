
"""GPU backend using NVIDIA Management Library (NVML) via pynvml.

This backend samples GPU power draw (in watts) during the measured period using pynvml.
It runs a background sampler thread to collect power samples while the measured function executes.

Requirements: `pip install pynvml` (package name may be `pynvml` or `nvidia-ml-py3` depending on platform).
Notes: NVIDIA drivers expose power in milliwatts via nvmlDeviceGetPowerUsage; divide by 1000 to get watts.
Sampling rate depends on driver/hardware (some devices only update at ~1 Hz, newer drivers may provide faster samples). See NVML docs and driver notes.
"""
import time
import threading
from typing import Dict, List, Optional

try:
    import pynvml
except Exception:
    pynvml = None


class GPUBackend:
    name = "nvidia_gpu"

    def __init__(self, index: int = 0, sampling_interval: float = 0.1):
        if pynvml is None:
            raise RuntimeError("pynvml is required for GPUBackend. Install with `pip install pynvml` or `pip install nvidia-ml-py3`")
        self.index = index
        self.sampling_interval = sampling_interval
        pynvml.nvmlInit()
        try:
            self._handle = pynvml.nvmlDeviceGetHandleByIndex(self.index)
        except pynvml.NVMLError as e:
            raise RuntimeError(f"NVML error getting device {index}: {e}")

        self._samples: List[float] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _sampler(self):
        while self._running:
            try:
                # nvmlDeviceGetPowerUsage returns milliwatts
                power_mw = pynvml.nvmlDeviceGetPowerUsage(self._handle)
                # convert to watts
                p_w = float(power_mw) / 1000.0
                self._samples.append(p_w)
            except Exception:
                # if a sample fails, skip it
                pass
            time.sleep(self.sampling_interval)

    def start(self):
        # clear samples and start background sampling
        self._samples = []
        self._running = True
        self._t0 = time.time()
        self._thread = threading.Thread(target=self._sampler, daemon=True)
        self._thread.start()

    def stop(self) -> Dict[str, float]:
        # stop and join sampler
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._t1 = time.time()
        duration = self._t1 - self._t0

        if len(self._samples) == 0:
            avg_power = 0.0
        else:
            avg_power = sum(self._samples) / len(self._samples)

        energy = avg_power * duration

        return {"duration": duration, "energy_j": energy, "avg_power_w": avg_power, "samples_count": len(self._samples), "samples": self._samples}

