# tqueue package

This library allows you to do your tasks in multiple threads easily.

This is helpful when you have a lot of data to process.

Assume that you have a large list of items to process. You need to write a producer to put items in the queue one by one.

Workers will get data from the queue and then process it. Putting data into a queue should be quicker than processing it (worker).

### Installation

```bash
pip install tqueue
```


### Usage
1. Import library
```python
from tqueue import ThreadingQueue
```
2. Create a worker
- Create a worker function that gets the data as the first parameter
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
- b. Put data into the queue

- You can also use ThreadingQueue as a context manager

```python
def producer():
    # Start the queue
    with ThreadingQueue(40, worker) as tq:
        ...
        tq.put(data)
```

- You can also use it async

```python
async def producer():
    # Start the queue
    async with ThreadingQueue(40, worker) as tq:
        ...
        await tq.put(data)
```

4. Run producer

* Async producer:
```python
await producer()
```
or
```python
asyncio.run(producer())
```


### Note
1. You can add more keyword params for all workers running in threads via `worker_params`
2. Apart from the number of threads and the worker, you can set `log_dir` to store logs to file 
3. and `worker_params_builder` to generate parameters for each worker.
4. `on_thread_close` is an optional param as a function that is helpful when you need to close the database connection when a thread done
5. Apart from all the above params, the rest of the keyword params will be passed to the worker.

* If you change the lib from the 0.0.14 version to the newer, please update the code to fix the bug:
```python
# 0.0.14
with ThreadingQueue(num_of_threads, worker) as tq:
    ...
    await tq.put(data)
```

```python
# From 0.0.15

# Sync
with ThreadingQueue(num_of_threads, worker) as tq:
    ...
    tq.put(data)

# Async
async with ThreadingQueue(num_of_threads, worker) as tq:
    ...
    await tq.put(data)
```

* In both sync and async cases, you can provide a worker as an async function.
* The async version is a little bit better in performance because it uses `asyncio.sleep` to wait when the queue is full compared to `time.sleep` in the sync version. In most cases, the difference in performance is not much.

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


# Build params for the worker, the params will be persistent with the thread
# This function is called when init a new thread or retry
def worker_params_builder():
    # Threads use db connection separately
    conn = get_db_connection()
    conn.autocommit(1)
    cursor = conn.cursor()
    return {"cursor": cursor, "connection": conn}


# To clear resources: close database connection, ...
# This function is called when the thread ends
def on_close_thread(cursor, connection):
    cursor.close()
    connection.close()


def worker(image_info, cursor, uid: int, **kwargs):
    # Update image info into database
    
    sql = "UPDATE images SET width = %s, height = %s, uid = %s WHERE id = %s"
    cursor.execute(sql, (image_info["width"], image_info["height"], uid, image_info["id"]))
    

def producer(source_file: str):
    with ThreadingQueue(
        NUM_OF_THREADS, worker,
        log_dir=f"logs/update-images",
        worker_params_builder=worker_params_builder,
        on_close_thread=on_close_thread,
        params={"uid": 123},
        retry_count=1
    ) as tq:
        with open(source_file, 'r') as f:
            for line in f:
                if not line:
                    continue
                data = json.loads(line)
    
                tq.put(data)


if __name__ == "__main__":
    producer("images.jsonl")
```

### Development

#### Build project

1. Update the version number in file `src/tqueue/__version__.py`
2. Update the Change log
3. Build and publish the changes

```bash
python3 -m build
python3 -m twine upload dist/*
```
