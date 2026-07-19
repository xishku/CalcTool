package benchmark;

import org.yaml.snakeyaml.Yaml;
import java.io.*;
import java.util.*;
import java.util.stream.*;

public class Benchmark {
    private static int runsPerTest = 5;
    private static int warmupRuns = 2;
    private static int arraySize = 100000;
    private static int matrixDim = 500;
    private static int fibN = 40;
    private static int primeLimit = 10000000;
    private static int hashDataMB = 10;
    private static int stringLength = 1000000;
    private static int patternLength = 100;

    static class Result {
        String algorithm;
        String language = "java";
        List<Double> runs;
        double meanMs;
        double stddevMs;
        double peakMemoryMb;
        String unit = "ms";
    }

    static class Failed {
        String algorithm;
        String language = "java";
        String error;
    }

    @SuppressWarnings("unchecked")
    static void loadConfig() throws IOException {
        InputStream input = new FileInputStream("../../config.yaml");
        Yaml yaml = new Yaml();
        Map<String, Object> cfg = yaml.load(input);
        input.close();

        runsPerTest = (int) cfg.getOrDefault("runs_per_test", 5);
        warmupRuns = (int) cfg.getOrDefault("warmup_runs", 2);
        arraySize = (int) cfg.getOrDefault("array_size", 100000);
        matrixDim = (int) cfg.getOrDefault("matrix_dimension", 500);
        fibN = (int) cfg.getOrDefault("fibonacci_n", 40);
        primeLimit = (int) cfg.getOrDefault("prime_limit", 10000000);
        hashDataMB = (int) cfg.getOrDefault("hash_data_mb", 10);
        stringLength = (int) cfg.getOrDefault("string_length", 1000000);
        patternLength = (int) cfg.getOrDefault("pattern_length", 100);
    }

    static List<Integer> collectRuns(int n, Runnable fn) {
        List<Integer> times = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            long start = System.nanoTime();
            fn.run();
            long elapsed = (System.nanoTime() - start) / 1_000_000;
            times.add((int) elapsed);
        }
        return times;
    }

    @FunctionalInterface
    interface BenchFn { void run() throws Exception; }

    static Result runTest(String name, BenchFn fn) throws Exception {
        // cleanup before test
        System.gc();
        Thread.sleep(100);

        // warmup
        for (int i = 0; i < warmupRuns; i++) fn.run();

        // measure
        List<Double> ms = new ArrayList<>();
        for (int i = 0; i < runsPerTest; i++) {
            System.gc();
            Runtime rt = Runtime.getRuntime();
            long memBefore = rt.totalMemory() - rt.freeMemory();

            long start = System.nanoTime();
            fn.run();
            long elapsed = System.nanoTime() - start;

            long memAfter = rt.totalMemory() - rt.freeMemory();
            double memUsed = Math.max(0, (memAfter - memBefore) / (1024.0 * 1024.0));

            ms.add(elapsed / 1_000_000.0);
        }

        Result r = new Result();
        r.algorithm = name;
        r.runs = ms.stream().map(v -> Math.round(v * 10000.0) / 10000.0).collect(Collectors.toList());
        r.meanMs = Math.round(ms.stream().mapToDouble(Double::doubleValue).average().orElse(0) * 10000.0) / 10000.0;
        double avg = r.meanMs;
        double variance = ms.stream().mapToDouble(v -> Math.pow(v - avg, 2)).average().orElse(0);
        r.stddevMs = Math.round(Math.sqrt(variance) * 10000.0) / 10000.0;
        r.peakMemoryMb = 0;
        return r;
    }

    static void printJson(List<Result> results, List<Failed> failed) {
        StringBuilder sb = new StringBuilder();
        sb.append("{\"results\":[");
        for (int i = 0; i < results.size(); i++) {
            Result r = results.get(i);
            if (i > 0) sb.append(",");
            sb.append(String.format(
                "{\"algorithm\":\"%s\",\"language\":\"java\",\"runs\":%s,\"mean_ms\":%.4f,\"stddev_ms\":%.4f,\"peak_memory_mb\":%.2f,\"unit\":\"ms\"}",
                r.algorithm, r.runs.toString(), r.meanMs, r.stddevMs, r.peakMemoryMb));
        }
        sb.append("],\"failed\":[");
        for (int i = 0; i < failed.size(); i++) {
            Failed f = failed.get(i);
            if (i > 0) sb.append(",");
            sb.append(String.format("{\"algorithm\":\"%s\",\"language\":\"java\",\"error\":\"%s\"}",
                f.algorithm, f.error.replace("\"", "\\\"")));
        }
        sb.append("]}");
        System.out.println(sb.toString());
    }

    public static void main(String[] args) {
        List<Result> results = new ArrayList<>();
        List<Failed> failed = new ArrayList<>();

        try {
            loadConfig();
        } catch (Exception e) {
            failed.add(new Failed() {{ algorithm = "_config"; error = e.getMessage(); }});
            printJson(results, failed);
            return;
        }

        // Generate shared data
        DataGenerator.RNG.setSeed(42);
        int[] intArray = DataGenerator.genIntArray(arraySize);
        double[][] matA = DataGenerator.genMatrix(matrixDim);
        double[][] matB = DataGenerator.genMatrix(matrixDim);
        byte[] hashData = DataGenerator.genRandomBytes(hashDataMB);
        String text = DataGenerator.genRandomString(stringLength);
        String pattern = text.substring(stringLength / 3, stringLength / 3 + patternLength);

        // Write data for C/C++ programs
        try {
            DataGenerator.writeIntArray("data_bubble.bin", intArray);
            DataGenerator.writeDoubleArray("data_matrix_a.bin", matA);
            DataGenerator.writeDoubleArray("data_matrix_b.bin", matB);
            DataGenerator.writeBytes("data_hash.bin", hashData);
            DataGenerator.writeString("data_str_text.bin", text);
            DataGenerator.writeString("data_str_pattern.bin", pattern);
        } catch (Exception e) {
            // non-fatal, C/C++ may not run anyway
        }

        int[] finalArray = intArray;
        int finalFibN = fibN;
        int finalPrimeLimit = primeLimit;
        byte[] finalHashData = hashData;
        String finalText = text;
        String finalPattern = pattern;

        // Define tests
        Object[][] tests = {
            {"bubble_sort", (BenchFn) () -> { SortBubble.bubbleSort(finalArray.clone()); }},
            {"quick_sort", (BenchFn) () -> { SortQuick.quickSort(finalArray.clone(), 0, finalArray.length - 1); }},
            {"matrix_multiply", (BenchFn) () -> { MatrixMultiply.multiply(matA, matB); }},
            {"fibonacci_iter", (BenchFn) () -> { Fibonacci.iter(finalFibN); }},
            {"fibonacci_rec", (BenchFn) () -> { Fibonacci.rec(finalFibN); }},
            {"prime_sieve", (BenchFn) () -> { PrimeSieve.sieve(finalPrimeLimit); }},
            {"hash_fnv1a", (BenchFn) () -> { HashSHA256.hash(finalHashData); }},
            {"str_kmp", (BenchFn) () -> { StrKMP.search(finalText, finalPattern); }}
        };

        for (Object[] test : tests) {
            String name = (String) test[0];
            BenchFn fn = (BenchFn) test[1];
            try {
                Result r = runTest(name, fn);
                results.add(r);
            } catch (Exception e) {
                Failed f = new Failed();
                f.algorithm = name;
                f.error = e.getMessage();
                failed.add(f);
            }
        }

        printJson(results, failed);
    }
}
