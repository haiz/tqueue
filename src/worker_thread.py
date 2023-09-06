import asyncio
import copy
import threading
import queue
import time
import inspect

from .simple_logger import SimpleLogger


class WorkerThread(threading.Thread):
    def __init__(self, thread_id, func_is_expired, message_queue: queue.Queue, queue_lock: threading.Lock, handler,
                 logger: SimpleLogger, params: dict = None, worker_params_builder=None, on_close=None):
        threading.Thread.__init__(self)
        self.func_is_expired = func_is_expired
        self.thread_id = thread_id
        self.name = "Thread-" + str(thread_id + 1)
        self.message_queue = message_queue
        self.queue_lock = queue_lock
        self.logger = logger
        self.handler_params = params or {}
        self.worker_params_builder = worker_params_builder
        self.handler = handler
        self.on_close = on_close

    def run(self):
        self.logger.info("Starting " + self.name)
        start_time = time.time()

        asyncio.run(self.process_data())

        self.logger.info("Exiting " + self.name + f" in {round(time.time() - start_time, 4)} seconds")

    async def process_data(self):
        params = copy.deepcopy(self.handler_params)
        if self.worker_params_builder:
            built_params = self.worker_params_builder()
            if inspect.iscoroutine(built_params):
                built_params = await built_params
            if isinstance(built_params, dict):
                params.update(built_params)

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
                self.logger.warn(f"{self.name} acquire lock time: {acquire_time}")

            if not self.message_queue.empty():
                data = self.message_queue.get()
                self.queue_lock.release()
                self.logger.debug(f"{self.name} processing {data}")

                try:
                    ret = self.handler(data, **params)
                    if inspect.iscoroutine(ret):
                        await ret
                except Exception as ex:
                    self.logger.error(exception=ex)

                empty_queue_waiting_time = 0.1
            else:
                self.queue_lock.release()
                await asyncio.sleep(empty_queue_waiting_time)
                empty_queue_waiting_time += 0.1

        if self.on_close:
            ret = self.on_close(**params)
            if inspect.iscoroutine(ret):
                await ret
