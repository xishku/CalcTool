#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "bench_util.h"

void compute_lps(const char *pattern, int m, int *lps) {
    int len = 0;
    lps[0] = 0;
    int i = 1;
    while (i < m) {
        if (pattern[i] == pattern[len]) {
            len++; lps[i] = len; i++;
        } else {
            if (len != 0) len = lps[len - 1];
            else { lps[i] = 0; i++; }
        }
    }
}

int kmp_search(const char *text, const char *pattern, int n, int m, int **matches) {
    int *lps = malloc(m * sizeof(int));
    compute_lps(pattern, m, lps);

    int capacity = 16, count = 0;
    *matches = malloc(capacity * sizeof(int));

    int i = 0, j = 0;
    while (i < n) {
        if (text[i] == pattern[j]) {
            i++; j++;
            if (j == m) {
                if (count >= capacity) {
                    capacity *= 2;
                    *matches = realloc(*matches, capacity * sizeof(int));
                }
                (*matches)[count++] = i - j;
                j = lps[j - 1];
            }
        } else {
            if (j != 0) j = lps[j - 1];
            else i++;
        }
    }

    free(lps);
    return count;
}

int main(int argc, char *argv[]) {
    parse_args(argc, argv);
    int text_len, pattern_len;
    char *text = read_string("data_str_text.bin", &text_len);
    char *pattern = read_string("data_str_pattern.bin", &pattern_len);

    struct timespec start, end;
    int *matches;
    clock_gettime(CLOCK_MONOTONIC, &start);
    int count = kmp_search(text, pattern, text_len, pattern_len, &matches);
    clock_gettime(CLOCK_MONOTONIC, &end);
    output_result("str_kmp", &start, &end);

    free(text); free(pattern); free(matches);
    return 0;
}
