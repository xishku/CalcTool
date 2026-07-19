package benchmark;

/**
 * FNV-1a 64-bit hash — zero external dependencies.
 * 故意使用 long（有符号溢出），与 C 的 uint64_t 溢出行为一致。
 */
public class HashSHA256 {
    private static final long FNV_OFFSET = 0xcbf29ce484222325L;
    private static final long FNV_PRIME  = 0x100000001b3L;

    public static long hash(byte[] data) {
        long h = FNV_OFFSET;
        for (byte b : data) {
            h ^= (b & 0xff);
            h *= FNV_PRIME;
        }
        return h;
    }
}
