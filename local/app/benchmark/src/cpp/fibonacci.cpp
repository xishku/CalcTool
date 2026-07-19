#include "bench_util.hpp"

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
    long long result;

    auto start = std::chrono::high_resolution_clock::now();
    result = fibonacci_iter(fib_n);
    auto end = std::chrono::high_resolution_clock::now();
    output_result("fibonacci_iter", start, end);

    start = std::chrono::high_resolution_clock::now();
    result = fibonacci_rec(fib_n);
    end = std::chrono::high_resolution_clock::now();
    output_result("fibonacci_rec", start, end);

    (void)result;
    return 0;
}
