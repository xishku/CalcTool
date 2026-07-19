#include <stdio.h>
#include "bench_util.h"

long long fibonacci_iter(int n) {
    if (n <= 1) return n;
    long long a = 0, b = 1;
    for (int i = 2; i <= n; i++) {
        long long t = a + b; a = b; b = t;
    }
    return b;
}

long long fibonacci_rec(int n) {
    if (n <= 1) return n;
    return fibonacci_rec(n - 1) + fibonacci_rec(n - 2);
}

int main(int argc, char *argv[]) {
    parse_args(argc, argv);
    struct timespec start, end;
    long long result;

    // 迭代版本
    clock_gettime(CLOCK_MONOTONIC, &start);
    result = fibonacci_iter(fib_n);
    clock_gettime(CLOCK_MONOTONIC, &end);
    output_result("fibonacci_iter", &start, &end);

    // 递归版本
    clock_gettime(CLOCK_MONOTONIC, &start);
    result = fibonacci_rec(fib_n);
    clock_gettime(CLOCK_MONOTONIC, &end);
    output_result("fibonacci_rec", &start, &end);

    (void)result;
    return 0;
}
