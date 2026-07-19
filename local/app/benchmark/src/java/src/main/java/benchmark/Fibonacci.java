package benchmark;

public class Fibonacci {
    public static long iter(int n) {
        if (n <= 1) return n;
        long a = 0, b = 1;
        for (int i = 2; i <= n; i++) {
            long t = a + b; a = b; b = t;
        }
        return b;
    }

    public static long rec(int n) {
        if (n <= 1) return n;
        return rec(n - 1) + rec(n - 2);
    }
}
