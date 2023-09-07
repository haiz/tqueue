import asyncio
import copy
import queue
import threading
import time
from typing import List, Any

from .worker_thread import WorkerThread
from .simple_logger import SimpleLogger


class ThreadingQueue:
    expired: bool = False
    work_queue = None
    queue_lock = None
    logger = None
    threads = []
    start_time = 0

    def __init__(self, num_of_threads: int, worker, log_dir: str = "", worker_params_builder=None, worker_params: dict = None, on_close_thread=None):

        queue_size = 3 * num_of_threads

        self.logger = SimpleLogger()
        self.work_queue = queue.Queue(queue_size)
        self.queue_lock = threading.Lock()
        self.start_time = time.time()

        thread_log_dir = ""
        if log_dir:
            thread_log_dir = f"{log_dir}/threads"

        wparams = worker_params if worker_params else {}

        self.threads = self.create_threads(worker, num_of_threads, thread_log_dir=thread_log_dir,
                                           worker_params_builder=worker_params_builder, on_close_thread=on_close_thread,
                                           **wparams)

    def is_expired(self) -> bool:
        return self.expired

    def create_threads(
            self, handler, num_of_threads, thread_log_dir: str = "", worker_params_builder=None, on_close_thread=None, **kwargs
    ) -> List:
        # Create new threads
        thread_log_dir = f"{thread_log_dir}/{int(time.time())}-{num_of_threads}" if thread_log_dir else ""

        params = copy.deepcopy(kwargs)
        for tid in range(num_of_threads):
            log_file_path = f"{thread_log_dir}/Thread-{str(tid + 1)}" if thread_log_dir else ""
            logger = SimpleLogger(file_path=log_file_path)
            thread = WorkerThread(tid, self.is_expired, self.work_queue, self.queue_lock, handler, logger,
                                  params=params, worker_params_builder=worker_params_builder, on_close=on_close_thread)
            thread.start()
            self.threads.append(thread)
        return self.threads

    async def put(self, data: Any):
        queue_full_waiting_time = 0.01
        while True:
            acquire_waiting_time = 0.0002
            while not self.queue_lock.acquire():
                time.sleep(acquire_waiting_time)
                acquire_waiting_time += 0.0002
            if self.work_queue.full():
                self.queue_lock.release()
                await asyncio.sleep(queue_full_waiting_time)
                queue_full_waiting_time += 0.01
            else:
                break

        self.work_queue.put(data)
        self.queue_lock.release()

    def stop(self):
        # Wait for queue to empty
        while not self.work_queue.empty():
            self.logger.debug(f"QSIZE: {self.work_queue.qsize()}")
            time.sleep(1)
            threads = [t for t in self.threads if t.is_alive()]
            if not threads:
                break
        self.logger.debug("Queue is empty")

        self.expired = True

        # Wait for all threads to complete
        for t in self.threads:
            t.join()
        self.logger.info(f"Exiting Main Thread in {round(time.time() - self.start_time, 4)} seconds")
