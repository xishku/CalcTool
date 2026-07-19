#include "bench_util.hpp"

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

std::vector<int> read_int_vector(const char *filename, int size) {
    std::ifstream f(filename, std::ios::binary);
    std::vector<int> data(size);
    f.read(reinterpret_cast<char*>(data.data()), size * sizeof(int));
    return data;
}

std::vector<double> read_double_vector(const char *filename, int count) {
    std::ifstream f(filename, std::ios::binary);
    std::vector<double> data(count);
    f.read(reinterpret_cast<char*>(data.data()), count * sizeof(double));
    return data;
}

std::vector<unsigned char> read_bytes(const char *filename, int &size) {
    std::ifstream f(filename, std::ios::binary | std::ios::ate);
    size = f.tellg();
    f.seekg(0, std::ios::beg);
    std::vector<unsigned char> data(size);
    f.read(reinterpret_cast<char*>(data.data()), size);
    return data;
}

std::string read_string(const char *filename, int &len) {
    std::ifstream f(filename, std::ios::binary | std::ios::ate);
    len = f.tellg();
    f.seekg(0, std::ios::beg);
    std::string data(len, '\0');
    f.read(&data[0], len);
    return data;
}
