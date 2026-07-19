#include <stdio.h>
#include <stdlib.h>
#include "bench_util.h"

void matrix_multiply(double *a, double *b, double *c, int n) {
    for (int i = 0; i < n; i++) {
        for (int k = 0; k < n; k++) {
            double aik = a[i * n + k];
            for (int j = 0; j < n; j++) {
                c[i * n + j] += aik * b[k * n + j];
            }
        }
    }
}

int main(int argc, char *argv[]) {
    parse_args(argc, argv);
    int n = matrix_dim;
    double *a = read_double_array("data_matrix_a.bin", n * n);
    double *b = read_double_array("data_matrix_b.bin", n * n);
    double *c = calloc(n * n, sizeof(double));

    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    matrix_multiply(a, b, c, n);
    clock_gettime(CLOCK_MONOTONIC, &end);
    output_result("matrix_multiply", &start, &end);

    free(a); free(b); free(c);
    return 0;
}
