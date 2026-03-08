from functools import wraps
from typing import Optional, Dict
from .core import measure_callable


def measure_power(backend: Optional[object] = "auto", backend_opts: Optional[Dict] = None, runs: int = 1, warmup: int = 0, return_result: bool = True):
    """Decorator to measure a function. Delegates to core.measure_callable.

    Usage:
        @measure_power(backend='cpu_weighted', backend_opts={'tdp_w': 28}, runs=3)
        def f(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return measure_callable(func, *args, backend=backend, backend_opts=backend_opts, runs=runs, warmup=warmup, return_result=return_result, **kwargs)
        return wrapper
    return decorator