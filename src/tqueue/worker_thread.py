import asyncio
import copy
import threading
import queue
import time
import inspect
from typing import Any

from .simple_logger import SimpleLogger


async def execute_func(func, *args, **kwargs):
    if func:
        ret = func(*args, **kwargs)
        if inspect.iscoroutine(ret):
            return await ret
        return ret
    return None


async def execute_func_safe(func, *args, **kwargs):
    try:
        return await execute_func(func, *args, **kwargs)
    except Exception as ex:
        return ex


class WorkerThread(threading.Thread):

    def __init__(self, thread_id: str, func_is_expired, message_queue: queue.Queue, queue_lock: threading.Lock, handler,
                 logger: SimpleLogger, params: dict = None, worker_params_builder=None, on_close=None,
                 retry_count: int = 0, on_restart=None, on_fail=None, should_restart=None):
        threading.Thread.__init__(self)
        self.func_is_expired = func_is_expired
        self.thread_id = thread_id
        self.name = "Thread-" + thread_id
        self.message_queue = message_queue
        self.queue_lock = queue_lock
        self.logger = logger
        self.handler_params = params or {}
        self.worker_params_builder = worker_params_builder
        self.handler = handler
        self.on_close = on_close
        self.on_restart = on_restart
        self.on_fail = on_fail
        self.should_restart = should_restart
        self.retry_count = retry_count

    def run(self):
        self.info("Starting")
        start_time = time.time()

        asyncio.run(self.process_data())

        self.info(f"Exiting in {round(time.time() - start_time, 4)} seconds")

    async def process_data(self):
        params = copy.deepcopy(self.handler_params)
        await self._build_params(params)

        empty_queue_waiting_time = 0.1
        while not self.func_is_expired():
            start_acquire_time = time.time()
            sleep_time = 0.001
            while not self.queue_lock.acquire():
                await asyncio.sleep(sleep_time)
                if sleep_time < 0.1:
                    sleep_time += 0.001

            acquire_time = time.time() - start_acquire_time
            if acquire_time > 1:
                self.warn(f"acquire lock time: {acquire_time}")

            if not self.message_queue.empty():
                data = self.message_queue.get()
                self.queue_lock.release()
                self.debug(f"processing {data}")

                try:
                    await execute_func(self.handler, data, **params)
                except Exception as ex:
                    if self.retry_count > 0:
                        for i in range(self.retry_count):
                            ex = await self.retry(data, params)
                            if not ex:
                                break
                    if ex and isinstance(ex, Exception):
                        if self.should_restart and self.should_restart(ex):
                            self.on_restart(self.thread_id, data, ex)
                            return
                        self.error(exception=ex)
                        self.on_fail(self.thread_id, data)

                empty_queue_waiting_time = 0.1
            else:
                self.queue_lock.release()
                await asyncio.sleep(empty_queue_waiting_time)
                empty_queue_waiting_time += 0.1

        await execute_func(self.on_close, **params)

    async def _build_params(self, params: dict):
        built_params = await execute_func(self.worker_params_builder)
        if isinstance(built_params, dict):
            params.update(built_params)

    async def retry(self, data: Any, params: dict):
        self.debug(f"RETRY processing {data}")

        await execute_func_safe(self.on_close, **params)

        await self._build_params(params)

        return await execute_func_safe(self.handler, data, **params)

    def debug(self, msg: str = "", exception: Exception = None):
        msg = f"{self.name} -> {msg} {'[' + str(type(exception)) + ']' + str(exception) if exception else ''}"
        self.logger.debug(msg, exception=exception)

    def info(self, msg: str = "", exception: Exception = None):
        msg = f"{self.name} -> {msg} {'[' + str(type(exception)) + ']' + str(exception) if exception else ''}"
        self.logger.info(msg, exception=exception)

    def warn(self, msg: str = "", exception: Exception = None):
        msg = f"{self.name} -> {msg} {'[' + str(type(exception)) + ']' + str(exception) if exception else ''}"
        self.logger.warn(msg, exception=exception)

    def error(self, msg: str = "", exception: Exception = None):
        msg = f"{self.name} -> {msg} {'[' + str(type(exception)) + ']' + str(exception) if exception else ''}"
        self.logger.error(msg, exception=exception)
