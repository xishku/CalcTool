#include <stdio.h>
#include <stdlib.h>
#include "bench_util.h"

void bubble_sort(int arr[], int n) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                int temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
            }
        }
    }
}

int main(int argc, char *argv[]) {
    parse_args(argc, argv);
    int *data = read_int_array("data_bubble.bin", &array_size);
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    bubble_sort(data, array_size);
    clock_gettime(CLOCK_MONOTONIC, &end);
    output_result("bubble_sort", &start, &end);
    free(data);
    return 0;
}
