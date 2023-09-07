import time
import random
import asyncio

from tqueue import ThreadingQueue


def worker(data):
    time.sleep(random.randint(1, 2))
    print(data["n"])


async def consumer():
    tq = ThreadingQueue(10, worker)
    for i in range(1, 30):
        await tq.put({"n": i})
    tq.stop()


if __name__ == "__main__":
    # export PYTHONPATH=[Path to src]
    asyncio.run(consumer())
