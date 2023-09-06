import time
import random
import asyncio

from src import ThreadingQueue


def worker(data, uid: int = 0, pb: int = 0):
    time.sleep(random.randint(1, 2))
    print({"data": data, "uid": uid, "pb": pb})


def worker_params_builder():
    return {"pb": random.randint(10, 99)}


async def consumer():
    # Start threading queue
    tq = ThreadingQueue(
        10, worker, worker_params_builder=worker_params_builder, worker_params={"uid": random.randint(1, 10)}
    )
    for i in range(1, 30):
        await tq.put({"r": i})
    tq.stop()


if __name__ == "__main__":
    # export PYTHONPATH=[Path to threading-queue]
    asyncio.run(consumer())
