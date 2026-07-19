#ifndef BENCH_UTIL_H
#define BENCH_UTIL_H

#include <time.h>

extern int array_size;
extern int matrix_dim;
extern int fib_n;
extern int prime_limit;
extern int hash_data_size;

void parse_args(int argc, char *argv[]);
int *read_int_array(const char *filename, int *size);
double *read_double_array(const char *filename, int count);
unsigned char *read_bytes(const char *filename, int *size);
char *read_string(const char *filename, int *len);
void output_result(const char *algo_name, struct timespec *start, struct timespec *end);

#endif
