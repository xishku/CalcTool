import time
import functools

from .logger import Logger

class Dec:
    @staticmethod
    def timeit_decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()  # 记录开始时间
            result = func(*args, **kwargs)  # 执行函数
            end_time = time.time()  # 记录结束时间
            execution_time = end_time - start_time  # 计算执行时间
            Logger.log().info(f"函数 '{func.__name__}' 耗时: {execution_time:.4f}s")
            return result  # 返回函数结果
        return wrapper
