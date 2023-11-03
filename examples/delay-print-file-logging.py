import time
import random

from tqueue import ThreadingQueue


def worker(data):
    if data["n"] % 10 == 9:
        raise Exception("Invalid n")


def consumer():
    with ThreadingQueue(10, worker, log_dir="logs") as tq:
        for i in range(1, 30):
            tq.put({"n": i})


def consumer_retry():
    with ThreadingQueue(10, worker, log_dir="logs", retry_count=2) as tq:
        for i in range(1, 10):
            tq.put({"n": i})


if __name__ == "__main__":
    # export PYTHONPATH=[Path to src]
    # consumer()
    consumer_retry()
