#include <cstdint>
#include <chrono>
#include "bench_util.hpp"

/* FNV-1a 64-bit hash — zero external dependencies */
static constexpr uint64_t FNV_OFFSET = 0xcbf29ce484222325ULL;
static constexpr uint64_t FNV_PRIME  = 0x100000001b3ULL;

static uint64_t fnv1a_64(const unsigned char *data, size_t len) {
    uint64_t hash = FNV_OFFSET;
    for (size_t i = 0; i < len; i++) {
        hash ^= static_cast<uint64_t>(data[i]);
        hash *= FNV_PRIME;
    }
    return hash;
}

int main(int argc, char *argv[]) {
    parse_args(argc, argv);
    auto data = read_bytes("data_hash.bin", hash_data_size);
    uint64_t result;

    auto start = std::chrono::high_resolution_clock::now();
    result = fnv1a_64(data.data(), hash_data_size);
    auto end = std::chrono::high_resolution_clock::now();

    volatile uint64_t guard = result;
    (void)guard;

    output_result("hash_fnv1a", start, end);
    return 0;
}
