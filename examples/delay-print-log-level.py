import logging
import time
import random

from tqueue import ThreadingQueue


def worker(data):
    time.sleep(random.randint(1, 2))
    # print(data["n"])
    if data["n"] % 10 == 9:
        raise Exception("Invalid n")


def consumer():
    with ThreadingQueue(
            10, worker, log_dir="logs", console_log_level=logging.CRITICAL, file_log_level=logging.INFO
    ) as tq:
        for i in range(1, 30):
            tq.put({"n": i})


if __name__ == "__main__":
    # export PYTHONPATH=[Path to src]
    consumer()
