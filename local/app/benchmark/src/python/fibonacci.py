"""斐波那契数列算法"""
def fibonacci_iterative(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

def fibonacci_recursive(n):
    if n <= 1:
        return n
    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)

def run_fibonacci_iterative(n):
    return fibonacci_iterative(n)

def run_fibonacci_recursive(n):
    return fibonacci_recursive(n)
