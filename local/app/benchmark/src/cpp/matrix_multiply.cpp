#include <vector>
#include "bench_util.hpp"

void matrix_multiply(const std::vector<double> &a, const std::vector<double> &b,
                     std::vector<double> &c, int n) {
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
    auto a = read_double_vector("data_matrix_a.bin", n * n);
    auto b = read_double_vector("data_matrix_b.bin", n * n);
    std::vector<double> c(n * n, 0.0);

    auto start = std::chrono::high_resolution_clock::now();
    matrix_multiply(a, b, c, n);
    auto end = std::chrono::high_resolution_clock::now();
    output_result("matrix_multiply", start, end);
    return 0;
}
