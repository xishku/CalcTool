"""Python 基准测试主入口"""
import sys
import os
import json
import time
import random
import math
import statistics
import tracemalloc
import yaml

sys.path.insert(0, os.path.dirname(__file__))

from sort_bubble import run_bubble_sort
from sort_quick import run_quick_sort
from matrix_multiply import run_matrix_multiply
from fibonacci import run_fibonacci_iterative, run_fibonacci_recursive
from prime_sieve import run_prime_sieve
from hash_sha256 import run_hash_fnv1a
from str_kmp import run_kmp


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def gen_random_array(size):
    return [random.randint(0, 1000000) for _ in range(size)]


def gen_matrix(dim):
    return [[random.random() for _ in range(dim)] for _ in range(dim)]


def gen_random_bytes(size_mb):
    return os.urandom(size_mb * 1024 * 1024)


def gen_random_string(length):
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 '
    return ''.join(random.choice(chars) for _ in range(length))


def benchmark(func, name, warmup, runs, *args, **kwargs):
    """运行基准测试，返回结果字典"""
    # 预热
    for _ in range(warmup):
        func(*args, **kwargs)

    # 正式测量
    times = []
    mem_peaks = []
    for _ in range(runs):
        tracemalloc.start()
        start = time.perf_counter_ns()
        func(*args, **kwargs)
        elapsed_ns = time.perf_counter_ns() - start
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        times.append(elapsed_ns / 1_000_000)  # ns -> ms
        mem_peaks.append(peak / (1024 * 1024))  # bytes -> MB

    return {
        'runs': [round(t, 4) for t in times],
        'mean_ms': round(statistics.mean(times), 4),
        'stddev_ms': round(statistics.stdev(times) if len(times) > 1 else 0, 4),
        'peak_memory_mb': round(max(mem_peaks), 2),
        'unit': 'ms'
    }


def prepare_data(cfg):
    random.seed(42)
    array = gen_random_array(cfg['array_size'])
    dim = cfg['matrix_dimension']
    a = gen_matrix(dim)
    b = gen_matrix(dim)
    fib_n = cfg['fibonacci_n']
    prime_limit = cfg['prime_limit']
    hash_data = gen_random_bytes(cfg['hash_data_mb'])
    text = gen_random_string(cfg['string_length'])
    pattern = text[cfg['string_length'] // 3: cfg['string_length'] // 3 + cfg['pattern_length']]
    return array, dim, a, b, fib_n, prime_limit, hash_data, text, pattern


def run_all(cfg):
    runs = cfg['runs_per_test']
    warmup = cfg['warmup_runs']
    results = []
    failed = []

    array, dim, a, b, fib_n, prime_limit, hash_data, text, pattern = prepare_data(cfg)

    tests = [
        ('bubble_sort', run_bubble_sort, (array,)),
        ('quick_sort', run_quick_sort, (array,)),
        ('matrix_multiply', run_matrix_multiply, (dim, a, b)),
        ('fibonacci_iter', run_fibonacci_iterative, (fib_n,)),
        ('fibonacci_rec', run_fibonacci_recursive, (fib_n,)),
        ('prime_sieve', run_prime_sieve, (prime_limit,)),
        ('hash_fnv1a', run_hash_fnv1a, (hash_data,)),
        ('str_kmp', run_kmp, (text, pattern)),
    ]

    for name, func, args in tests:
        try:
            r = benchmark(func, name, warmup, runs, *args)
            r['algorithm'] = name
            r['language'] = 'python'
            results.append(r)
        except Exception as e:
            failed.append({'algorithm': name, 'language': 'python', 'error': str(e)})

    return results, failed


if __name__ == '__main__':
    cfg = load_config()
    results, failed = run_all(cfg)
    # 输出为 JSON，供 run 脚本汇总
    print(json.dumps({'results': results, 'failed': failed}))
