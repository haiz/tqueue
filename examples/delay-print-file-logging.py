import time
import random
import asyncio

from src import ThreadingQueue


def worker(data):
    time.sleep(random.randint(1, 2))
    print(data["n"])
    if data["n"] % 10 == 9:
        raise Exception("Invalid n")


async def consumer():
    tq = ThreadingQueue(10, worker, log_dir="logs")
    for i in range(1, 30):
        await tq.put({"n": i})
    tq.stop()


if __name__ == "__main__":
    # export PYTHONPATH=[Path to threading-queue]
    asyncio.run(consumer())
