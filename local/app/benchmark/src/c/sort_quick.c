#include <stdio.h>
#include <stdlib.h>
#include "bench_util.h"

static void swap(int *a, int *b) {
    int t = *a; *a = *b; *b = t;
}

static int partition(int arr[], int low, int high) {
    int pivot = arr[high];
    int i = low - 1;
    for (int j = low; j < high; j++) {
        if (arr[j] < pivot) { i++; swap(&arr[i], &arr[j]); }
    }
    swap(&arr[i + 1], &arr[high]);
    return i + 1;
}

void quick_sort(int arr[], int low, int high) {
    if (low < high) {
        int pi = partition(arr, low, high);
        quick_sort(arr, low, pi - 1);
        quick_sort(arr, pi + 1, high);
    }
}

int main(int argc, char *argv[]) {
    parse_args(argc, argv);
    int *data = read_int_array("data_bubble.bin", &array_size);
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    quick_sort(data, 0, array_size - 1);
    clock_gettime(CLOCK_MONOTONIC, &end);
    output_result("quick_sort", &start, &end);
    free(data);
    return 0;
}
