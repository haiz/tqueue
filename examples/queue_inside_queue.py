import time
import random
from datetime import datetime

from tqueue import ThreadingQueue


def process_child(child_id: int):
    print(f"start child {child_id} {datetime.utcnow()}")
    time.sleep(random.randint(0, 2))
    print(f"end child {child_id} {datetime.utcnow()}")


def process_parent(parent_id: int):
    print(f"start parent {parent_id} {datetime.utcnow()}")
    with ThreadingQueue(2, process_child, name=f"Child#{parent_id}") as tq:
        for i in range(3):
            tq.put(parent_id * 10 + i)
    print(f"start parent {parent_id} {datetime.utcnow()}")


def run():
    with ThreadingQueue(2, process_parent, name="Parent") as tq:
        for i in range(3):
            tq.put(i)


if __name__ == '__main__':
    # export PYTHONPATH=[Path to src]
    run()
