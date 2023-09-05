This library allow to do you tasks in multiple threads easily.
This is helpful when you have a lot of data to processing.
Asume that you have a large list of item to process. You need to write a consumer to put items to queue one by one.
Workers will get data from queue then process it. Putting data to queue should be quicker then processing it.

### Installation
TODO


### Usage
1. Create a queue
```python
from tqueue import ThreadingQueue

tqueue = ThreadingQueue()
```
2. Set threading for a consumer
Apply the threading for a consumer:
- a. Set the number of threads and the worker
- b. Put data to queue

```python
@tqueue.threading(40, worker)
async def consumer(my_queue: ThreadingQueue):
    ...
    my_queue.put(data)
```
3. Run consumer
consumer(tqueue, "images.jsonl")


### Note
1. Apart from number of threads and the worker, you can set `log_dir` to store logs to file and `worker_params_builder` to generate parameters for each worker.
2. Apart from all above params, the rest of keyword params will be pass to the worker. 

### Example

```python
import json
import pymysql

from threading_queue import ThreadingQueue


NUM_OF_THREADS = 40


tqueue = ThreadingQueue()


def get_db_connection():
    return pymysql.connect(host='localhost',
                           user='root',
                           password='123456',
                           database='example',
                           cursorclass=pymysql.cursors.DictCursor)


# Build params for worker
def worker_params_builder():
    # Threads use db connection separately
    conn = get_db_connection()
    conn.autocommit(1)
    cursor = conn.cursor()
    return {"cursor": cursor}


def worker(image_info, cursor, uid: int = 0):
    # Update image info into database
    
    sql = "UPDATE images SET width = %s, height = %s, uid = %s WHERE id = %s"
    cursor.execute(sql, (image_info["width"], image_info["height"], uid, image_info["id"]))
    


@tqueue.threading(
    NUM_OF_THREADS, worker, log_dir=f"logs/update-images", worker_params_builder=worker_params_builder, params={"uid": 123}
)
async def consumer(my_queue: ThreadingQueue, source_file: str):
    with open(source_file, 'r') as f:
        for line in f:
            if not line:
                continue
            data = json.loads(line)

            await my_queue.put(data)


if __name__ == "__main__":
    consumer(tqueue, "images.jsonl")

```
