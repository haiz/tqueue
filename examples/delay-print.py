import time
import random
import asyncio

from src import ThreadingQueue

# export PYTHONPATH=[Path to threading-queue]
tq = ThreadingQueue()


def worker(data):
    time.sleep(random.randint(1, 2))
    print(data["n"])


@tq.threading(10, worker)
async def consumer(my_queue: ThreadingQueue):
    for i in range(1, 30):
        await my_queue.put({"n": i})


if __name__ == "__main__":
    asyncio.run(consumer(tq))
