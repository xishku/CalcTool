package benchmark;

public class MatrixMultiply {
    public static double[][] multiply(double[][] a, double[][] b) {
        int n = a.length;
        double[][] result = new double[n][n];
        for (int i = 0; i < n; i++) {
            for (int k = 0; k < n; k++) {
                double aik = a[i][k];
                for (int j = 0; j < n; j++) {
                    result[i][j] += aik * b[k][j];
                }
            }
        }
        return result;
    }
}
