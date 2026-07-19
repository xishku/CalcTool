#ifndef BENCH_UTIL_HPP
#define BENCH_UTIL_HPP

#include <chrono>
#include <string>
#include <vector>
#include <fstream>
#include <iostream>
#include <cstdlib>
#include <cstring>

extern int array_size;
extern int matrix_dim;
extern int fib_n;
extern int prime_limit;
extern int hash_data_size;

void parse_args(int argc, char *argv[]);

std::vector<int> read_int_vector(const char *filename, int size);
std::vector<double> read_double_vector(const char *filename, int count);
std::vector<unsigned char> read_bytes(const char *filename, int &size);
std::string read_string(const char *filename, int &len);

template<typename T>
void output_result(const char *algo_name, T start, T end) {
    double ms = std::chrono::duration<double, std::milli>(end - start).count();
    printf("{\"algorithm\":\"%s\",\"language\":\"cpp\",\"mean_ms\":%.4f,\"unit\":\"ms\"}\n", algo_name, ms);
}

#endif
