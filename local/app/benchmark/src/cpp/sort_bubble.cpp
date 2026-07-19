#include <iostream>
#include <vector>
#include <fstream>
#include "bench_util.hpp"
#include "bench_util.hpp"

void bubble_sort(std::vector<int> &arr) {
    size_t n = arr.size();
    for (size_t i = 0; i < n; i++) {
        for (size_t j = 0; j < n - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                std::swap(arr[j], arr[j + 1]);
            }
        }
    }
}

int main(int argc, char *argv[]) {
    parse_args(argc, argv);
    auto data = read_int_vector("data_bubble.bin", array_size);
    auto start = std::chrono::high_resolution_clock::now();
    bubble_sort(data);
    auto end = std::chrono::high_resolution_clock::now();
    output_result("bubble_sort", start, end);
    return 0;
}
