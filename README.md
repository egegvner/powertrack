# PowerTrack

> **Measure energy consumption of Python code** — CPU · GPU · RAPL · Time-based estimates

PowerTrack provides a unified API to profile power usage with multiple backends—from simple time-based estimates to hardware Intel RAPL counters and NVIDIA GPU power sampling. Use it as a decorator or function call to measure joules, watts, and execution time of any callable.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Backends](#backends)
- [Usage Examples](#usage-examples)
- [Measurement Output](#measurement-output)
- [Contributing](#contributing)

---

## Features

- **Multiple backends**: Time-based, CPU-weighted, Intel RAPL, and NVIDIA GPU
- **Auto-detection**: Automatically uses the best available backend on your system
- **Concurrent measurement**: Run multiple backends simultaneously and aggregate results
- **Flexible API**: Use as a function call or decorator
- **Zero-config fallback**: Works out of the box with the time-based backend (no hardware required)

---

## Installation

### From source

Place the `powertrack` package in your Python path. From the directory containing `powertrack`:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python -c "from powertrack import measure_power; print('OK')"
```

### Core (minimal)

The core package works with the **time-based** backend only—no extra dependencies required.

### Optional backends

| Backend        | Package   | Command                    |
|----------------|-----------|----------------------------|
| CPU-weighted   | `psutil`  | `pip install psutil`       |
| Intel RAPL     | `pyRAPL`  | `pip install pyRAPL`       |
| NVIDIA GPU     | `pynvml`  | `pip install pynvml`       |

Install all optional backends:

```bash
pip install powertrack psutil pyRAPL pynvml
```

---

## Quick Start

### Using the decorator

```python
from powertrack import measure_power

@measure_power(backend="time_based")
def compute_sum(n):
    return sum(i**2 for i in range(n))

result = compute_sum(1_000_000)
print(f"Energy: {result.energy_j:.2f} J")
print(f"Time:   {result.time_s:.3f} s")
print(f"Power:  {result.avg_power_w:.2f} W")
print(f"Output: {result.result}")
```

### Using the function API

```python
from powertrack import measure_callable

def heavy_work(x):
    return sum(i**2 for i in range(x))

m = measure_callable(heavy_work, 1_000_000, backend="time_based", return_result=True)
print(f"Energy: {m.energy_j:.2f} J, Result: {m.result}")
```

### Auto backend selection

```python
from powertrack import measure_power

@measure_power(backend="auto")  # Uses best available: RAPL → GPU → CPU-weighted → time-based
def my_function():
    # your code here
    pass
```

---

## API Reference

### `measure_callable(func, *args, backend="auto", backend_opts=None, runs=1, warmup=0, return_result=True, **kwargs) -> Measurement`

Measure energy consumption of a callable.

| Parameter      | Type                    | Default   | Description                                                                 |
|----------------|-------------------------|-----------|-----------------------------------------------------------------------------|
| `func`         | `Callable`              | —         | The function or callable to measure                                         |
| `*args`        | —                       | —         | Positional arguments passed to `func`                                       |
| `backend`      | `str \| List \| type`   | `"auto"`  | Backend name(s), class(es), or instance(s). See [Backend selection](#backend-selection). |
| `backend_opts` | `Dict`                  | `None`    | Options passed to backend constructors. See [Backend options](#backend-options). |
| `runs`         | `int`                   | `1`       | Number of measured runs (results are averaged)                              |
| `warmup`       | `int`                   | `0`       | Number of warmup runs (not measured, used to stabilize caches/CPU)          |
| `return_result`| `bool`                  | `True`    | If `True`, include the function's return value in `Measurement.result`      |
| `**kwargs`     | —                       | —         | Keyword arguments passed to `func`                                          |

**Returns:** A `Measurement` instance with aggregated energy, time, and power data.

**Example:**

```python
m = measure_callable(my_func, arg1, arg2, kwarg=3, backend="cpu_weighted", runs=3)
```

---

### `measure(func, *args, **kwargs) -> Measurement`

Alias for `measure_callable`. Same signature and behavior.

---

### `measure_power(backend="auto", backend_opts=None, runs=1, warmup=0, return_result=True)`

Decorator that measures a function's energy consumption.

| Parameter      | Type   | Default   | Description                                              |
|----------------|--------|-----------|----------------------------------------------------------|
| `backend`      | `str`  | `"auto"`  | Backend to use                                           |
| `backend_opts` | `Dict` | `None`    | Options for the backend                                  |
| `runs`         | `int`  | `1`       | Number of measured runs                                  |
| `warmup`       | `int`  | `0`       | Number of warmup runs                                    |
| `return_result`| `bool` | `True`    | Include return value in `Measurement.result`             |

**Example:**

```python
@measure_power(backend="cpu_weighted", backend_opts={"tdp_w": 45}, runs=3, warmup=1)
def train_model():
    # ...
    return model
```

---

### `Measurement`

Dataclass holding measurement results.

| Attribute    | Type              | Description                                      |
|--------------|-------------------|--------------------------------------------------|
| `time_s`     | `float`           | Average wall-clock time in seconds                |
| `energy_j`   | `float`           | Average energy in joules                         |
| `avg_power_w`| `float`           | Average power in watts (energy / time)           |
| `backend`    | `str`             | Always `"combined"` when using `measure_callable`|
| `details`    | `Dict \| None`     | Per-run and per-backend breakdown                |
| `result`     | `Any`             | Return value of the measured function (if `return_result=True`) |

**Methods:**

- **`to_dict() -> Dict`** — Convert to a dictionary (excludes `result`). Useful for JSON serialization.

**Example:**

```python
m = measure_callable(foo, backend="time_based")
print(m.to_dict())
# {'time_s': 0.5, 'energy_j': 7.5, 'avg_power_w': 15.0, 'backend': 'combined', 'details': {...}}
```

---

## Backends

### Backend selection

The `backend` parameter accepts:

| Value        | Behavior                                                                 |
|--------------|--------------------------------------------------------------------------|
| `"auto"`     | Try, in order: `rapl` → `nvidia_gpu` → `cpu_weighted` → `time_based`     |
| `"time_based"` | Simple duration × constant power (no sensors)                          |
| `"cpu_weighted"` | CPU-time–weighted estimate (requires `psutil`)                       |
| `"rapl"`     | Intel RAPL hardware counters (requires `pyRAPL`, Intel CPU)             |
| `"nvidia_gpu"` | NVIDIA GPU power sampling (requires `pynvml`, NVIDIA GPU)             |
| `["a", "b"]` | List of backends; all run concurrently, energies summed                 |
| Class/instance | Custom backend class or instance                                    |

### Backend options

Pass options via `backend_opts`:

**Global (all backends):**
```python
measure_callable(func, backend="time_based", backend_opts={"avg_power_w": 25})
```

**Per-backend:**
```python
measure_callable(func, backend=["time_based", "cpu_weighted"],
                 backend_opts={
                     "time_based": {"avg_power_w": 20},
                     "cpu_weighted": {"tdp_w": 45}
                 })
```

---

### Time-based backend (`time_based`)

**No dependencies.** Estimates energy as `duration × avg_power_w`.

| Option         | Type   | Default | Description                    |
|----------------|--------|---------|--------------------------------|
| `avg_power_w`  | `float`| `15.0`  | Assumed average system power (W)|

**Use case:** Baseline, CI, or environments without sensors.

```python
from powertrack.backends import TimeBackend

@measure_power(backend="time_based", backend_opts={"avg_power_w": 25.0})
def my_func():
    pass
```

---

### CPU-weighted backend (`cpu_weighted`)

**Requires:** `psutil`

Estimates power as `TDP × (cpu_time / wall_time)`. Calibrate `tdp_w` for your CPU.

| Option   | Type   | Default | Description                    |
|----------|--------|---------|--------------------------------|
| `tdp_w`  | `float`| `28.0`  | CPU TDP in watts (thermal design power) |

**Use case:** Better CPU-bound workload estimates than time-based.

```python
@measure_power(backend="cpu_weighted", backend_opts={"tdp_w": 65})
def cpu_intensive():
    return sum(i**2 for i in range(10**7))
```

---

### RAPL backend (`rapl`)

**Requires:** `pyRAPL`, Intel CPU with RAPL support (Linux)

Uses hardware energy counters for package (PKG) and DRAM.

| Option       | Type        | Default | Description                          |
|--------------|-------------|---------|--------------------------------------|
| `devices`    | `List[str]` | `None`  | e.g. `["PKG", "DRAM"]` (pyRAPL.Device)|
| `socket_ids` | `List[int]` | `None`  | Socket IDs to measure                 |

**Use case:** Accurate CPU/DRAM energy on supported Intel systems.

```python
@measure_power(backend="rapl", backend_opts={"devices": ["PKG", "DRAM"]})
def measured_code():
    pass
```

---

### NVIDIA GPU backend (`nvidia_gpu`)

**Requires:** `pynvml`, NVIDIA GPU and drivers

Samples GPU power during execution via NVML.

| Option             | Type   | Default | Description                    |
|--------------------|--------|---------|--------------------------------|
| `index`            | `int`  | `0`     | GPU device index                |
| `sampling_interval` | `float`| `0.1`   | Sampling interval in seconds    |

**Use case:** GPU workload energy profiling.

```python
@measure_power(backend="nvidia_gpu", backend_opts={"index": 0, "sampling_interval": 0.05})
def gpu_inference():
    # CUDA/GPU code
    pass
```

---

## Usage Examples

### Multiple runs and warmup

```python
@measure_power(backend="time_based", runs=5, warmup=2)
def benchmark():
    return expensive_computation()

# 2 warmup runs (not measured) + 5 measured runs; results averaged
m = benchmark()
```

### Multiple backends (concurrent)

```python
m = measure_callable(
    my_func,
    backend=["time_based", "cpu_weighted"],
    backend_opts={
        "time_based": {"avg_power_w": 20},
        "cpu_weighted": {"tdp_w": 45}
    }
)
# Energies from both backends are summed
print(m.details["per_run"][0]["per_backend"])
```

### Discard return value

```python
@measure_power(backend="time_based", return_result=False)
def side_effect_only():
    write_to_disk()
    # No need to store return value
```

### Custom backend instance

```python
from powertrack import measure_callable
from powertrack.backends import TimeBackend

be = TimeBackend(avg_power_w=30.0)
m = measure_callable(my_func, backend=be)
```

---

## Measurement Output

### Structure

```python
Measurement(
    time_s=0.123,           # Average wall time (s)
    energy_j=1.85,          # Average energy (J)
    avg_power_w=15.04,      # energy / time (W)
    backend="combined",
    details={
        "runs": 1,
        "active_backends": ["time_based"],
        "per_run": [
            {
                "wall_time_s": 0.123,
                "run_energy_j": 1.85,
                "per_backend": {
                    "time_based": {
                        "duration": 0.123,
                        "energy_j": 1.85,
                        "avg_power_w": 15.0
                    }
                }
            }
        ]
    },
    result=333332833333500  # Function return value
)
```

### Backend-specific fields in `per_backend`

| Backend        | Extra keys in `per_backend[name]`      |
|----------------|----------------------------------------|
| `time_based`   | —                                      |
| `cpu_weighted` | `cpu_time_s`                           |
| `rapl`         | `pkg_j`, `dram_j`                      |
| `nvidia_gpu`   | `samples_count`, `samples`             |

---

## Project Structure

```
powertrack/
├── __init__.py          # Public API: measure, measure_callable, measure_power, Measurement
├── core.py              # measure_callable, backend resolution
├── decorators.py        # measure_power decorator
├── types.py             # Measurement dataclass
├── backends/
│   ├── __init__.py      # TimeBackend, CPUWeightedBackend
│   ├── time_based.py    # Time-based backend
│   ├── cpu_weighted.py  # CPU-weighted backend (psutil)
│   ├── rapl.py          # Intel RAPL backend (pyRAPL)
│   └── gpu.py           # NVIDIA GPU backend (pynvml)
└── README.md
```

---

## Testing

Run the test suite:

```bash
pytest powertrack/test.py -v
```

From the project root with `PYTHONPATH` set:

```bash
PYTHONPATH=. pytest powertrack/test.py -v
```

---

## Contributing

Contributions are welcome. Please open an issue or pull request on GitHub.

---

## License

MIT License
