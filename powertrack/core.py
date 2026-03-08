"""Core measurement runner. Provides measure_callable and a small runner for multiple runs and warmups.

This updated runner supports multiple backends running concurrently and an "auto" selection
that will try to use RAPL and NVIDIA GPU backends when available, in addition to CPU-weighted
and time-based backends. It aggregates per-backend measurements into a combined Measurement.
"""
import time
from typing import Callable, Any, Optional, Dict, List, Union
from .types import Measurement
from .backends import TimeBackend, CPUWeightedBackend

# Import optional backends lazily to avoid hard dependency errors at import time
try:
    from .backends.rapl import RAPLBackend  # type: ignore
except Exception:
    RAPLBackend = None  # type: ignore

try:
    from .backends.gpu import GPUBackend  # type: ignore
except Exception:
    GPUBackend = None  # type: ignore

_BACKENDS = {
    "time_based": TimeBackend,
    "cpu_weighted": CPUWeightedBackend,
    "rapl": RAPLBackend,
    "nvidia_gpu": GPUBackend,
}


def _instantiate_backend(entry: Union[str, type, object], opts: Optional[Dict] = None):
    """Instantiate a backend entry which can be:
    - an instance -> returned as-is
    - a class -> instantiated with opts
    - a string key -> looked up in _BACKENDS and instantiated with opts

    If instantiation fails (missing dependency), returns None.
    """
    opts = opts or {}
    # already an instance
    if not isinstance(entry, (str, type)):
        return entry

    # class
    if isinstance(entry, type):
        try:
            return entry(**opts)
        except Exception:
            return None

    # string name
    cls = _BACKENDS.get(entry)
    if cls is None:
        return None
    try:
        return cls(**opts)
    except Exception:
        return None


def _resolve_backend_list(backend: Optional[Union[str, List, object]], backend_opts: Optional[Dict] = None) -> List[object]:
    """Resolve the requested backend(s) into a list of instantiated backend objects.

    backend can be:
      - None or "auto": try to auto-detect ['rapl','nvidia_gpu','cpu_weighted','time_based'] in that order
      - a string name (single)
      - a list/tuple of names/classes/instances
      - a class or instance

    backend_opts may be either a dict of options applied to all backends or a mapping from backend-name to opts.
    """
    backend_opts = backend_opts or {}
    desired: List[Union[str, type, object]] = []

    if backend is None or backend == "auto":
        desired = ["rapl", "nvidia_gpu", "cpu_weighted", "time_based"]
    elif isinstance(backend, (list, tuple)):
        desired = list(backend)
    else:
        desired = [backend]

    instances = []
    for item in desired:
        # determine opts for this backend
        name = item if isinstance(item, str) else getattr(item, "name", None)
        if isinstance(backend_opts, dict) and name in backend_opts:
            opts = backend_opts[name]
        else:
            # global opts (apply to all backends)
            opts = backend_opts if isinstance(backend_opts, dict) else {}

        inst = _instantiate_backend(item, opts)
        if inst is not None:
            instances.append(inst)
    return instances


def measure_callable(func: Callable, *args, backend: Optional[Union[str, List, object]] = "auto", backend_opts: Optional[Dict] = None, runs: int = 1, warmup: int = 0, return_result: bool = True, **kwargs) -> Measurement:
    """Measure energy of a callable using one or more backends concurrently.

    - func: callable to run
    - backend: name/class/instance or list of them, or "auto"
    - backend_opts: dict passed to backend constructors. Can be a mapping of backend-name -> opts or a single dict for all.
    - runs: number of measured runs (averaged)
    - warmup: number of warmup runs (not measured)
    - return_result: include the function's return value in Measurement.result (only last run)
    - kwargs: passed to func

    Returns a Measurement whose `details` field contains a mapping of per-backend results.
    Total energy is the sum of energies reported by active backends; total time uses wall-clock timing.
    """
    backend_opts = backend_opts or {}
    backends = _resolve_backend_list(backend, backend_opts)

    if len(backends) == 0:
        # as a fallback, always include the time-based backend
        backends = [TimeBackend()]

    # warmup runs (no measurement)
    for _ in range(warmup):
        func(*args, **kwargs)

    total_energy_accum = 0.0
    total_time_accum = 0.0
    last_result = None
    per_run_details: List[Dict] = []

    for _ in range(max(1, runs)):
        # Start all backends
        for be in backends:
            try:
                be.start()
            except Exception:
                # ignore failing backend starts
                pass

        # wall-clock start
        t0 = time.perf_counter()
        last_result = func(*args, **kwargs)
        t1 = time.perf_counter()
        wall_duration = t1 - t0

        # Stop backends and collect their info
        run_info: Dict[str, Dict] = {}
        run_total_energy = 0.0
        run_total_time = wall_duration

        for be in backends:
            try:
                info = be.stop() or {}
            except Exception:
                info = {}
            name = getattr(be, "name", type(be).__name__)
            run_info[name] = info
            run_total_energy += info.get("energy_j", 0.0)

        total_energy_accum += run_total_energy
        total_time_accum += run_total_time
        per_run_details.append({"wall_time_s": wall_duration, "per_backend": run_info, "run_energy_j": run_total_energy})

    avg_energy = total_energy_accum / max(1, runs)
    avg_time = total_time_accum / max(1, runs)
    avg_power = (avg_energy / avg_time) if avg_time > 0 else 0.0

    details = {
        "runs": runs,
        "per_run": per_run_details,
        "active_backends": [getattr(be, "name", type(be).__name__) for be in backends],
    }

    meas = Measurement(time_s=avg_time, energy_j=avg_energy, avg_power_w=avg_power, backend="combined", details=details, result=(last_result if return_result else None))
    return meas

# convenience alias
measure = measure_callable
