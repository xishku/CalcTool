#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include "bench_util.h"

/* FNV-1a 64-bit hash — zero external dependencies */
#define FNV_OFFSET 0xcbf29ce484222325ULL
#define FNV_PRIME  0x100000001b3ULL

static uint64_t fnv1a_64(const unsigned char *data, size_t len) {
    uint64_t hash = FNV_OFFSET;
    for (size_t i = 0; i < len; i++) {
        hash ^= (uint64_t)data[i];
        hash *= FNV_PRIME;
    }
    return hash;
}

int main(int argc, char *argv[]) {
    parse_args(argc, argv);
    unsigned char *data = read_bytes("data_hash.bin", &hash_data_size);
    uint64_t result;

    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    result = fnv1a_64(data, hash_data_size);
    clock_gettime(CLOCK_MONOTONIC, &end);

    /* prevent compiler from optimizing away the computation */
    volatile uint64_t guard = result;
    (void)guard;

    output_result("hash_fnv1a", &start, &end);
    free(data);
    return 0;
}
