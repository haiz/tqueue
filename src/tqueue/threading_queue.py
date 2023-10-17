import asyncio
import copy
import json
import logging
import queue
import threading
import time
from datetime import datetime
from typing import List, Any, Callable

from .worker_thread import WorkerThread
from .simple_logger import SimpleLogger


class ThreadingQueueBase:
    expired: bool = False
    work_queue = None
    queue_lock = None
    logger = None
    threads = []
    start_time = 0
    requeue_data = []
    restarting_thread_ids = []

    # Restart thread when the exception occurs and it includes one of these messages
    restart_on_errors = [
        "got Future <Future pending> attached to a different loop",  # SqlAlchemy Async
        "Command Out of Sync",  # SqlAlchemy
    ]

    def __init__(self, num_of_threads: int, worker: Callable = None, log_dir: str = "", worker_params: dict = None,
                 worker_params_builder: Callable = None, on_close_thread: Callable = None, retry_count: int = 0,
                 console_log_level: int = logging.INFO, file_log_level: int = logging.ERROR):

        queue_size = 3 * num_of_threads

        self.work_queue = queue.Queue(queue_size)
        self.queue_lock = threading.Lock()
        self.start_time = time.time()

        time_str = datetime.utcnow().strftime('%Y-%m-%d-%H-%M-%S')
        log_file_path = f"{log_dir + '/' if log_dir else ''}{time_str}.main.log"
        self.logger = SimpleLogger(file_path=log_file_path, console_log_level=console_log_level, file_log_level=file_log_level)

        log_file_path = ""
        if log_dir:
            log_file_path = f"{log_dir}/{time_str}.{num_of_threads}_threads.log"
        self.thread_logger = SimpleLogger(file_path=log_file_path, console_log_level=console_log_level, file_log_level=file_log_level)

        self.settings = {
            "worker": worker,
            "worker_params_builder": worker_params_builder,
            "on_close_thread": on_close_thread,
            "retry_count": retry_count,
            "worker_params": worker_params if worker_params else {},
        }

        self.threads = self.create_threads(num_of_threads)

    def is_expired(self) -> bool:
        return self.expired

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

    def should_restart(self, ex: Exception):
        if len(self.restart_on_errors) > 0:
            error = str(ex)
            for e_msg in self.restart_on_errors:
                if e_msg in error:
                    return True
        return False

    def new_thread_id(self, thread_id: str) -> str:
        parts = thread_id.split(".")
        if len(parts) >= 2:
            parts[-1] = str(int(parts[-1]) + 1)
        else:
            parts.append("1")
        return ".".join(parts)

    def on_restart_thread(self, tid: str, data: Any, ex: Exception = None):
        self.restarting_thread_ids.append(tid)
        self.requeue_data.append(data)
        if self.work_queue.full():
            self.work_queue.maxsize = self.work_queue.maxsize + 1

    def on_thread_failed(self, tid: str, data: Any):
        try:
            msg = json.dumps(data)
        except Exception as ex:
            msg = str(data)
        self.logger.error(f"Thread {tid} ==> {msg}")

    def create_threads(self, num_of_threads: int) -> List:
        for tid in range(num_of_threads):
            thread = self.create_thread(str(tid + 1))
            self.threads.append(thread)
        return self.threads

    def create_thread(self, thread_id: str):
        handler = self.settings["worker"]
        worker_params_builder = self.settings["worker_params_builder"]
        on_close_thread = self.settings["on_close_thread"]
        retry_count = self.settings["retry_count"]
        worker_params = self.settings["worker_params"]

        params = copy.deepcopy(worker_params)
        thread = WorkerThread(thread_id, self.is_expired, self.work_queue, self.queue_lock, handler, self.thread_logger,
                              params=params, worker_params_builder=worker_params_builder, on_close=on_close_thread,
                              retry_count=retry_count, on_restart=self.on_restart_thread, on_fail=self.on_thread_failed,
                              should_restart=self.should_restart
                              )
        thread.start()
        return thread

    def _restart_failed_threads(self):
        while len(self.restarting_thread_ids) > 0:
            thread_id = self.restarting_thread_ids.pop(0)
            thread = self.create_thread(self.new_thread_id(thread_id))
            self.threads.append(thread)

    # Handle restarting threads
    def _check_requeue(self):
        if len(self.requeue_data) > 0:
            self.threads = [t for t in self.threads if t.is_alive()]
            if len(self.threads) > 0:
                return self.requeue_data.pop(0)
        return None

    def _wait_for_acquire_lock(self, waited_time: float = 0) -> float:
        acquire_waiting_time = waited_time + 0.0002
        if waited_time >= 0.1:
            acquire_waiting_time = 0.1
        if not self.queue_lock.acquire():
            return acquire_waiting_time
        return 0

    def _wait_for_not_full_queue(self, waited_time: float = 0) -> float:
        queue_full_waiting_time = waited_time + 0.01
        if waited_time >= 1:
            queue_full_waiting_time = 1
        if self.work_queue.full():
            self.queue_lock.release()
            return queue_full_waiting_time
        return 0


class SyncThreadingQueue(ThreadingQueueBase):
    def _put(self, data: Any):
        qfull_waited_time = 0
        while True:
            wait_time = self._wait_for_acquire_lock()
            while wait_time > 0:
                time.sleep(wait_time)
                wait_time = self._wait_for_acquire_lock(wait_time)

            wait_time = self._wait_for_not_full_queue(qfull_waited_time)
            if wait_time > 0:
                time.sleep(wait_time)
                qfull_waited_time += wait_time
            else:
                break

        self.work_queue.put(data)
        self.queue_lock.release()

    def put(self, data: Any):
        self._put(data)

        self._restart_failed_threads()
        requeue_data = self._check_requeue()
        if requeue_data:
            self.put(data)


class AsyncThreadingQueue(ThreadingQueueBase):
    async def _put(self, data: Any):
        qfull_waited_time = 0
        while True:
            wait_time = self._wait_for_acquire_lock()
            while wait_time > 0:
                await asyncio.sleep(wait_time)
                wait_time = self._wait_for_acquire_lock(wait_time)

            wait_time = self._wait_for_not_full_queue(qfull_waited_time)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                qfull_waited_time += wait_time
            else:
                break

        self.work_queue.put(data)
        self.queue_lock.release()

    async def put(self, data: Any):
        await self._put(data)

        self._restart_failed_threads()
        requeue_data = self._check_requeue()
        if requeue_data:
            await self.put(data)


class ThreadingQueue:

    def __init__(self, num_of_threads: int, worker: Callable = None, log_dir: str = "", worker_params: dict = None,
                 worker_params_builder: Callable = None, on_close_thread: Callable = None, retry_count: int = 0,
                 console_log_level: int = 0):
        self.init_params = {
            "num_of_threads": num_of_threads,
            "worker": worker,
            "log_dir": log_dir,
            "worker_params_builder": worker_params_builder,
            "worker_params": worker_params,
            "on_close_thread": on_close_thread,
            "retry_count": retry_count,
            "console_log_level": console_log_level,
        }

    def __enter__(self):
        self.instance = SyncThreadingQueue(**self.init_params)
        return self.instance

    def __exit__(self, type, value, traceback):
        self.instance.stop()

    async def __aenter__(self):
        self.instance = AsyncThreadingQueue(**self.init_params)
        return self.instance

    async def __aexit__(self, type, value, traceback):
        self.instance.stop()
