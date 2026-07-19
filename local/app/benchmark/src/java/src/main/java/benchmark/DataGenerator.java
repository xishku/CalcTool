package benchmark;

import java.io.*;
import java.util.Random;
import java.nio.file.*;

public class DataGenerator {
    private static final Random RNG = new Random(42);
    private static final String DATA_DIR = "data";

    public static int[] genIntArray(int size) {
        int[] arr = new int[size];
        for (int i = 0; i < size; i++) arr[i] = RNG.nextInt(1000000);
        return arr;
    }

    public static double[][] genMatrix(int dim) {
        double[][] m = new double[dim][dim];
        for (int i = 0; i < dim; i++)
            for (int j = 0; j < dim; j++)
                m[i][j] = RNG.nextDouble();
        return m;
    }

    public static byte[] genRandomBytes(int sizeMB) {
        byte[] data = new byte[sizeMB * 1024 * 1024];
        RNG.nextBytes(data);
        return data;
    }

    public static String genRandomString(int length) {
        String chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ";
        StringBuilder sb = new StringBuilder(length);
        for (int i = 0; i < length; i++)
            sb.append(chars.charAt(RNG.nextInt(chars.length())));
        return sb.toString();
    }

    // Write binary data for C/C++ programs
    public static void writeIntArray(String filename, int[] arr) throws IOException {
        Paths.get(DATA_DIR).toFile().mkdirs();
        try (DataOutputStream dos = new DataOutputStream(
                new BufferedOutputStream(new FileOutputStream(DATA_DIR + "/" + filename)))) {
            for (int v : arr) dos.writeInt(v);
        }
    }

    public static void writeDoubleArray(String filename, double[][] mat) throws IOException {
        Paths.get(DATA_DIR).toFile().mkdirs();
        try (DataOutputStream dos = new DataOutputStream(
                new BufferedOutputStream(new FileOutputStream(DATA_DIR + "/" + filename)))) {
            for (double[] row : mat)
                for (double v : row)
                    dos.writeDouble(v);
        }
    }

    public static void writeBytes(String filename, byte[] data) throws IOException {
        Paths.get(DATA_DIR).toFile().mkdirs();
        Files.write(Paths.get(DATA_DIR, filename), data);
    }

    public static void writeString(String filename, String s) throws IOException {
        Paths.get(DATA_DIR).toFile().mkdirs();
        Files.write(Paths.get(DATA_DIR, filename), s.getBytes());
    }
}
