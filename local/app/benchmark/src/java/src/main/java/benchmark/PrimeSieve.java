package benchmark;

public class PrimeSieve {
    public static int sieve(int limit) {
        boolean[] isPrime = new boolean[limit + 1];
        for (int i = 2; i <= limit; i++) isPrime[i] = true;
        int sqrtLimit = (int) Math.sqrt(limit);
        for (int i = 2; i <= sqrtLimit; i++) {
            if (isPrime[i]) {
                for (int j = i * i; j <= limit; j += i) {
                    isPrime[j] = false;
                }
            }
        }
        int count = 0;
        for (int i = 2; i <= limit; i++) {
            if (isPrime[i]) count++;
        }
        return count;
    }
}
