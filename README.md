# tqueue package

This library allow to do you tasks in multiple threads easily.

This is helpful when you have a lot of data to processing.

Asume that you have a large list of item to process. You need to write a producer to put items to queue one by one.

Workers will get data from queue then process it. Putting data to queue should be quicker then processing it.

### Installation

```bash
pip install tqueue
```


### Usage
1. Import library
```python
from tqueue import ThreadingQueue
```
2. Create worker
- Create worker function that get the data as the first parameter
- Worker can be a normal function or a coroutine function
- Worker will be called in child threads

```python
def worker(data):
    pass
async def worker2(data):
    pass
```

3. Set threading for a producer
Apply the threading for a producer:
- a. Set the number of threads and the worker
- b. Put data to queue

```python
async def producer():
    # Start the queue
    tq = ThreadingQueue(40, worker)
    ...
    tq.put(data)
    ...
    tq.stop()
```

- You can also use ThreadingQueue like a context manager

```python
async def producer():
    # Start the queue
    with ThreadingQueue(40, worker) as tq:
        ...
        tq.put(data)
```

4. Run producer
```python
await producer()
```
or
```python
asyncio.run(producer())
```


### Note
1. You can add more keyword params for all workers running in threads via `worker_params`
2. Apart from number of threads and the worker, you can set `log_dir` to store logs to file 
3. and `worker_params_builder` to generate parameters for each worker.
4. `on_thread_close` is an optional param as a function that is helpful when you need to close the database connection when a thread done
5. Apart from all above params, the rest of keyword params will be pass to the worker. 

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
    

async def producer(source_file: str):
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
    asyncio.run(producer("images.jsonl"))
```

### Development

#### Build project

1. Update the version number in file `src/tqueue/__version__.py`
2. Update Change log
3. Build and publish the changes

```bash
python3 -m build
python3 -m twine upload dist/*
```
