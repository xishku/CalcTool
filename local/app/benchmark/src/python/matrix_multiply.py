"""矩阵乘法算法"""
def matrix_multiply(a, b):
    n = len(a)
    result = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for k in range(n):
            aik = a[i][k]
            for j in range(n):
                result[i][j] += aik * b[k][j]
    return result

def run_matrix_multiply(dim, a, b):
    return matrix_multiply(a, b)
