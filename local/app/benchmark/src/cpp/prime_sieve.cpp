#include <vector>
#include <cmath>
#include <cstring>
#include "bench_util.hpp"

int sieve_of_eratosthenes(int limit) {
    std::vector<char> is_prime(limit + 1, 1);
    is_prime[0] = is_prime[1] = 0;

    int sqrt_limit = (int)std::sqrt(limit);
    for (int i = 2; i <= sqrt_limit; i++) {
        if (is_prime[i]) {
            for (int j = i * i; j <= limit; j += i) {
                is_prime[j] = 0;
            }
        }
    }

    int count = 0;
    for (int i = 2; i <= limit; i++) {
        if (is_prime[i]) count++;
    }
    return count;
}

int main(int argc, char *argv[]) {
    parse_args(argc, argv);
    auto start = std::chrono::high_resolution_clock::now();
    int count = sieve_of_eratosthenes(prime_limit);
    auto end = std::chrono::high_resolution_clock::now();
    output_result("prime_sieve", start, end);
    (void)count;
    return 0;
}
