import time
import random
import asyncio

from src import ThreadingQueue

# export PYTHONPATH=[Path to threading-queue]
tq = ThreadingQueue()


def worker(data, uid: int = 0, pb: int = 0):
    time.sleep(random.randint(1, 2))
    print({"data": data, "uid": uid, "pb": pb})


def worker_params_builder():
    return {"pb": random.randint(10, 99)}


@tq.threading(10, worker, worker_params_builder=worker_params_builder, worker_params={"uid": random.randint(1, 10)})
async def consumer(my_queue: ThreadingQueue):
    for i in range(1, 30):
        await my_queue.put({"r": i})


if __name__ == "__main__":
    asyncio.run(consumer(tq))
