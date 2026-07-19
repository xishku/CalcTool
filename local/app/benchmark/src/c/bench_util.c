#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "bench_util.h"

int array_size = 100000;
int matrix_dim = 500;
int fib_n = 40;
int prime_limit = 10000000;
int hash_data_size = 10 * 1024 * 1024;

void parse_args(int argc, char *argv[]) {
    for (int i = 1; i + 1 < argc; i += 2) {
        if (strcmp(argv[i], "--array-size") == 0) array_size = atoi(argv[i+1]);
        else if (strcmp(argv[i], "--matrix-dim") == 0) matrix_dim = atoi(argv[i+1]);
        else if (strcmp(argv[i], "--fib-n") == 0) fib_n = atoi(argv[i+1]);
        else if (strcmp(argv[i], "--prime-limit") == 0) prime_limit = atoi(argv[i+1]);
        else if (strcmp(argv[i], "--hash-size") == 0) hash_data_size = atoi(argv[i+1]) * 1024 * 1024;
    }
}

int *read_int_array(const char *filename, int *size) {
    FILE *f = fopen(filename, "rb");
    int *data = malloc(*size * sizeof(int));
    fread(data, sizeof(int), *size, f);
    fclose(f);
    return data;
}

double *read_double_array(const char *filename, int count) {
    FILE *f = fopen(filename, "rb");
    double *data = malloc(count * sizeof(double));
    fread(data, sizeof(double), count, f);
    fclose(f);
    return data;
}

unsigned char *read_bytes(const char *filename, int *size) {
    FILE *f = fopen(filename, "rb");
    fseek(f, 0, SEEK_END);
    *size = ftell(f);
    rewind(f);
    unsigned char *data = malloc(*size);
    fread(data, 1, *size, f);
    fclose(f);
    return data;
}

char *read_string(const char *filename, int *len) {
    FILE *f = fopen(filename, "rb");
    fseek(f, 0, SEEK_END);
    *len = ftell(f);
    rewind(f);
    char *data = malloc(*len);
    fread(data, 1, *len, f);
    fclose(f);
    return data;
}

void output_result(const char *algo_name, struct timespec *start, struct timespec *end) {
    double ms = (end->tv_sec - start->tv_sec) * 1000.0 +
                (end->tv_nsec - start->tv_nsec) / 1000000.0;
    printf("{\"algorithm\":\"%s\",\"language\":\"c\",\"mean_ms\":%.4f,\"unit\":\"ms\"}\n", algo_name, ms);
}
