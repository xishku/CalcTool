#include <vector>
#include <string>
#include "bench_util.hpp"

std::vector<int> compute_lps(const std::string &pattern) {
    int m = pattern.size();
    std::vector<int> lps(m, 0);
    int len = 0, i = 1;
    while (i < m) {
        if (pattern[i] == pattern[len]) {
            len++; lps[i] = len; i++;
        } else {
            if (len != 0) len = lps[len - 1];
            else { lps[i] = 0; i++; }
        }
    }
    return lps;
}

std::vector<int> kmp_search(const std::string &text, const std::string &pattern) {
    int n = text.size(), m = pattern.size();
    auto lps = compute_lps(pattern);
    std::vector<int> matches;
    int i = 0, j = 0;
    while (i < n) {
        if (text[i] == pattern[j]) {
            i++; j++;
            if (j == m) {
                matches.push_back(i - j);
                j = lps[j - 1];
            }
        } else {
            if (j != 0) j = lps[j - 1];
            else i++;
        }
    }
    return matches;
}

int main(int argc, char *argv[]) {
    parse_args(argc, argv);
    int text_len, pattern_len;
    auto text = read_string("data_str_text.bin", text_len);
    auto pattern = read_string("data_str_pattern.bin", pattern_len);

    auto start = std::chrono::high_resolution_clock::now();
    auto matches = kmp_search(text, pattern);
    auto end = std::chrono::high_resolution_clock::now();
    output_result("str_kmp", start, end);
    return 0;
}
