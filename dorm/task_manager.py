import threading
import uuid
from collections import OrderedDict

# 简单的内存缓存，自动清理（保留最近100条）
task_cache = OrderedDict()
cache_lock = threading.Lock()
MAX_CACHE_SIZE = 100

def create_task():
    task_id = str(uuid.uuid4())
    with cache_lock:
        task_cache[task_id] = {"status": "processing", "html": None, "error": None}
        # 保持最大缓存
        while len(task_cache) > MAX_CACHE_SIZE:
            task_cache.popitem(last=False)
    return task_id

def update_task(task_id, status, html=None, error=None):
    with cache_lock:
        if task_id in task_cache:
            task_cache[task_id]["status"] = status
            if html is not None:
                task_cache[task_id]["html"] = html
            if error is not None:
                task_cache[task_id]["error"] = error

def get_task(task_id):
    with cache_lock:
        return task_cache.get(task_id)