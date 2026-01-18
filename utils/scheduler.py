# Core_Files/scheduler.py
# Edited Version: 1.42.20260111

"""
Central scheduler - runs all periodic tasks reliably in main asyncio loop
"""

import asyncio
from datetime import datetime

_tasks = {}  # name -> (coro, interval_sec, last_run)

async def _run_periodic(name, coro, interval):
    """Internal runner for a single periodic task"""
    while True:
        start = datetime.utcnow()
        try:
            await coro()
        except Exception as e:
            print(f"[scheduler] Error in task '{name}': {e}")
        elapsed = (datetime.utcnow() - start).total_seconds()
        sleep_time = max(0, interval - elapsed)
        await asyncio.sleep(sleep_time)

def register(name: str, coro, interval_seconds: float):
    """
    Register a periodic coroutine to run every interval_seconds.
    Example: scheduler.register("uptime_print", my_print_func, 60)
    """
    if name in _tasks:
        print(f"[scheduler] Task '{name}' already registered - skipping")
        return

    task = asyncio.create_task(_run_periodic(name, coro, interval_seconds))
    _tasks[name] = (task, interval_seconds)
    print(f"[scheduler] Registered task '{name}' every {interval_seconds}s")

async def shutdown():
    """Cancel all scheduled tasks on shutdown"""
    for name, (task, _) in _tasks.items():
        task.cancel()
        print(f"[scheduler] Cancelled task '{name}'")
    _tasks.clear()