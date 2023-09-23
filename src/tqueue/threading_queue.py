import asyncio
import copy
import json
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
    requeue_data = []
    restarting_thread_ids = []

    # Restart thread when the exception occurs and it includes one of these messages
    restart_on_errors = [
        "got Future <Future pending> attached to a different loop",  # SqlAlchemy Async
        "Command Out of Sync",  # SqlAlchemy
    ]

    def __init__(self, num_of_threads: int, worker, log_dir: str = "", worker_params_builder=None,
                 worker_params: dict = None, on_close_thread=None, retry_count: int = 0, std_out_log_level: int = 0):

        queue_size = 3 * num_of_threads

        self.logger = SimpleLogger()
        self.work_queue = queue.Queue(queue_size)
        self.queue_lock = threading.Lock()
        self.start_time = time.time()

        thread_log_dir = ""
        log_file_path = f"failed-data.{int(time.time())}-{num_of_threads}.txt"
        if log_dir:
            thread_log_dir = f"{log_dir}/threads/{int(time.time())}-{num_of_threads}"
            log_file_path = f"{thread_log_dir}/failed-data.txt"

        self.logger = SimpleLogger(file_path=log_file_path, std_out_log_level=std_out_log_level)

        self.settings = {
            "worker": worker,
            "thread_log_dir": thread_log_dir,
            "worker_params_builder": worker_params_builder,
            "on_close_thread": on_close_thread,
            "retry_count": retry_count,
            "worker_params": worker_params if worker_params else {},
            "std_out_log_level": std_out_log_level,
        }

        self.threads = self.create_threads(num_of_threads)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.stop()

    def is_expired(self) -> bool:
        return self.expired

    def should_restart(self, ex):
        if len(self.restart_on_errors) > 0:
            error = str(ex)
            for e_msg in self.restart_on_errors:
                if e_msg in error:
                    return True
        return False

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

    def create_threads(self, num_of_threads) -> List:
        for tid in range(num_of_threads):
            thread = self.create_thread(str(tid + 1))
            self.threads.append(thread)
        return self.threads

    def create_thread(self, thread_id: str):
        handler = self.settings["worker"]
        thread_log_dir = self.settings["thread_log_dir"]
        worker_params_builder = self.settings["worker_params_builder"]
        on_close_thread = self.settings["on_close_thread"]
        retry_count = self.settings["retry_count"]
        worker_params = self.settings["worker_params"]
        std_out_log_level = self.settings["std_out_log_level"]

        params = copy.deepcopy(worker_params)

        log_file_path = f"{thread_log_dir}/Thread-{thread_id}" if thread_log_dir else ""
        logger = SimpleLogger(file_path=log_file_path, std_out_log_level=std_out_log_level)
        thread = WorkerThread(thread_id, self.is_expired, self.work_queue, self.queue_lock, handler, logger,
                              params=params, worker_params_builder=worker_params_builder, on_close=on_close_thread,
                              retry_count=retry_count, on_restart=self.on_restart_thread, on_fail=self.on_thread_failed,
                              should_restart=self.should_restart
                              )
        thread.start()
        return thread

    async def put(self, data: Any):
        queue_full_waiting_time = 0.01
        while True:
            acquire_waiting_time = 0.0002
            while not self.queue_lock.acquire():
                await asyncio.sleep(acquire_waiting_time)
                acquire_waiting_time += 0.0002
            if self.work_queue.full():
                self.queue_lock.release()
                await asyncio.sleep(queue_full_waiting_time)
                queue_full_waiting_time += 0.01
            else:
                break

        self.work_queue.put(data)
        self.queue_lock.release()

        await self.restart_threads()

    # Handle restarting threads
    async def restart_threads(self):
        while len(self.restarting_thread_ids) > 0:
            thread_id = self.restarting_thread_ids.pop(0)
            thread = self.create_thread(self.new_thread_id(thread_id))
            self.threads.append(thread)

        if len(self.requeue_data) > 0:
            self.threads = [t for t in self.threads if t.is_alive()]
            if len(self.threads) > 0:
                data = self.requeue_data.pop(0)
                await self.put(data)

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

    def new_thread_id(self, thread_id: str) -> str:
        parts = thread_id.split(".")
        if len(parts) >= 2:
            parts[-1] = str(int(parts[-1]) + 1)
        else:
            parts.append("1")
        return ".".join(parts)
