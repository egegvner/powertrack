from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class Measurement:
    time_s: float
    energy_j: float
    avg_power_w: float
    backend: str
    details: Optional[Dict[str, Any]] = None
    result: Any = None

    def to_dict(self):
        return {
            "time_s": self.time_s,
            "energy_j": self.energy_j,
            "avg_power_w": self.avg_power_w,
            "backend": self.backend,
            "details": self.details,
        }