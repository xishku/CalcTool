#include <vector>
#include "bench_util.hpp"

int partition(std::vector<int> &arr, int low, int high) {
    int pivot = arr[high];
    int i = low - 1;
    for (int j = low; j < high; j++) {
        if (arr[j] < pivot) { i++; std::swap(arr[i], arr[j]); }
    }
    std::swap(arr[i + 1], arr[high]);
    return i + 1;
}

void quick_sort(std::vector<int> &arr, int low, int high) {
    if (low < high) {
        int pi = partition(arr, low, high);
        quick_sort(arr, low, pi - 1);
        quick_sort(arr, pi + 1, high);
    }
}

int main(int argc, char *argv[]) {
    parse_args(argc, argv);
    auto data = read_int_vector("data_bubble.bin", array_size);
    auto start = std::chrono::high_resolution_clock::now();
    quick_sort(data, 0, data.size() - 1);
    auto end = std::chrono::high_resolution_clock::now();
    output_result("quick_sort", start, end);
    return 0;
}
