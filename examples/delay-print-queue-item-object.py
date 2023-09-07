import time
import random
import asyncio

from tqueue import ThreadingQueue


class Item:
    foo: int = 0

    def __init__(self, foo: int):
        self.foo = foo

    def bar(self):
        print(f"Bar: {self.foo}")


def worker(data: Item):
    # Worker will receive Item objects from queue
    time.sleep(random.randint(1, 2))
    print(f"foo: {data.foo}")
    data.bar()


async def consumer():
    tq = ThreadingQueue(10, worker)
    for i in range(1, 30):
        item = Item(i)
        # Put an Item object to queue
        await tq.put(item)
    tq.stop()


if __name__ == "__main__":
    # export PYTHONPATH=[Path to src]
    asyncio.run(consumer())
