import time
from tools.logger import logger

def time_it(label: str, fn , *args, **kwargs):
    """
    Measure execution time of a function.
    Logs latency automatically.
    """
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    end = time.perf_counter()

    duration_ms = round((end - start)*1000, 2)

    logger.info(f"[PERF] {label} took {duration_ms} ms")

    return result, duration_ms