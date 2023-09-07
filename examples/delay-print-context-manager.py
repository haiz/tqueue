import time
import random
import asyncio

from tqueue import ThreadingQueue


def worker(data):
    time.sleep(random.randint(1, 2))
    print(data["n"])


async def consumer():
    with ThreadingQueue(10, worker) as tq:
        for i in range(1, 30):
            await tq.put({"n": i})


if __name__ == "__main__":
    # export PYTHONPATH=[Path to src]
    asyncio.run(consumer())
