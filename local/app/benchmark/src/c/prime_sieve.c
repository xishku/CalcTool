#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "bench_util.h"

int sieve_of_eratosthenes(int limit, int **primes_out) {
    char *is_prime = malloc(limit + 1);
    memset(is_prime, 1, limit + 1);
    is_prime[0] = is_prime[1] = 0;

    int sqrt_limit = (int)sqrt(limit);
    for (int i = 2; i <= sqrt_limit; i++) {
        if (is_prime[i]) {
            for (int j = i * i; j <= limit; j += i) {
                is_prime[j] = 0;
            }
        }
    }

    int count = 0;
    for (int i = 2; i <= limit; i++) { if (is_prime[i]) count++; }

    int *primes = malloc(count * sizeof(int));
    int idx = 0;
    for (int i = 2; i <= limit; i++) { if (is_prime[i]) primes[idx++] = i; }

    free(is_prime);
    *primes_out = primes;
    return count;
}

int main(int argc, char *argv[]) {
    parse_args(argc, argv);
    struct timespec start, end;
    int *primes;

    clock_gettime(CLOCK_MONOTONIC, &start);
    int count = sieve_of_eratosthenes(prime_limit, &primes);
    clock_gettime(CLOCK_MONOTONIC, &end);
    output_result("prime_sieve", &start, &end);

    free(primes);
    return 0;
}
