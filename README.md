This library allow to do you tasks in multiple threads easily.

This is helpful when you have a lot of data to processing.

Asume that you have a large list of item to process. You need to write a consumer to put items to queue one by one.

Workers will get data from queue then process it. Putting data to queue should be quicker then processing it.

### Installation
TODO


### Usage
1. Import library
```python
from tqueue import ThreadingQueue
```
2. Set threading for a consumer
Apply the threading for a consumer:
- a. Set the number of threads and the worker
- b. Put data to queue

```python
async def consumer():
    # Start the queue
    tq = ThreadingQueue(40, worker)
    ...
    tq.put(data)
    ...
    tq.stop()
```
3. Create worker
- Create worker function that get the data as the first parameter
- Worker can be a normal function or a coroutine function
```python
def worker1(data):
    pass
async def worker2(data):
    pass
```
4. Run consumer
```python
await consumer()
```
or
```python
asyncio.run(consumer())
```


### Note
1. Apart from number of threads and the worker, you can set `log_dir` to store logs to file and `worker_params_builder` to generate parameters for each worker.
2. Apart from all above params, the rest of keyword params will be pass to the worker. 

### Example

```python
import json
import pymysql
import asyncio

from tqueue import ThreadingQueue


NUM_OF_THREADS = 40


def get_db_connection():
    return pymysql.connect(host='localhost',
                           user='root',
                           password='123456',
                           database='example',
                           cursorclass=pymysql.cursors.DictCursor)


# Build params for worker, the params will be persistent with thread
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
    

async def consumer(source_file: str):
    tq = ThreadingQueue(
        NUM_OF_THREADS, worker, log_dir=f"logs/update-images", worker_params_builder=worker_params_builder, params={"uid": 123}
    )
    with open(source_file, 'r') as f:
        for line in f:
            if not line:
                continue
            data = json.loads(line)

            await tq.put(data)
    tq.stop()


if __name__ == "__main__":
    asyncio.run(consumer("images.jsonl"))
```
