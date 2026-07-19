#!/usr/bin/env python3
"""多语言算法性能基准测试 — 一键运行脚本"""
import os
import sys
import json
import time
import math
import platform
import subprocess
import shutil
import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, 'src')
RESULTS_DIR = os.path.join(BASE_DIR, 'results')


def load_config():
    with open(os.path.join(BASE_DIR, 'config.yaml'), 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    # Expand relative paths
    cfg['output_dir'] = os.path.join(BASE_DIR, cfg.get('output_dir', './results').lstrip('./\\'))
    return cfg


def get_machine_info():
    """获取机器环境信息"""
    info = {
        'os': platform.system() + ' ' + platform.release(),
        'cpu': platform.processor() or 'Unknown',
        'cores': os.cpu_count() or 0,
    }
    try:
        if platform.system() == 'Windows':
            import psutil
            info['ram_gb'] = round(psutil.virtual_memory().total / (1024**3), 1)
        else:
            with open('/proc/meminfo') as f:
                for line in f:
                    if 'MemTotal' in line:
                        info['ram_gb'] = round(int(line.split()[1]) / 1024**2, 1)
    except Exception:
        info['ram_gb'] = 0
    return info


def get_env_info(cfg):
    """获取各语言环境版本"""
    envs = {}
    # C
    try:
        out = subprocess.check_output([cfg['c_compiler'], '--version'], stderr=subprocess.STDOUT, text=True, timeout=5)
        envs['c'] = {'compiler': out.split('\n')[0], 'flags': cfg['c_flags']}
    except Exception:
        envs['c'] = {'compiler': 'not found', 'flags': ''}

    # C++
    try:
        out = subprocess.check_output([cfg['cpp_compiler'], '--version'], stderr=subprocess.STDOUT, text=True, timeout=5)
        envs['cpp'] = {'compiler': out.split('\n')[0], 'flags': cfg['cpp_flags']}
    except Exception:
        envs['cpp'] = {'compiler': 'not found', 'flags': ''}

    # Python
    envs['python'] = {'version': platform.python_version()}

    # Java
    try:
        out = subprocess.check_output(['java', '--version'], stderr=subprocess.STDOUT, text=True, timeout=5)
        envs['java'] = {'version': out.split('\n')[0] if out else 'unknown', 'vm_args': cfg['java_vm_args']}
    except Exception:
        envs['java'] = {'version': 'not found', 'vm_args': ''}

    return envs


def compile_c(cfg):
    """编译 C 程序（全部自实现算法，零第三方依赖）"""
    print("[C] Compiling...")
    c_src = os.path.join(SRC_DIR, 'c')
    c_bin = os.path.join(SRC_DIR, 'bin', 'c')
    os.makedirs(c_bin, exist_ok=True)

    compiler = cfg['c_compiler']
    flags = cfg['c_flags'].split()

    programs = ['sort_bubble', 'sort_quick', 'matrix_multiply', 'fibonacci', 'prime_sieve', 'hash_sha256', 'str_kmp']

    for prog in programs:
        src_file = os.path.join(c_src, f'{prog}.c')
        bin_file = os.path.join(c_bin, prog)
        cmd = [compiler] + flags + [src_file, os.path.join(c_src, 'bench_util.c'),
               '-o', bin_file, '-lm']
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=30)
            print(f"  [C] {prog} - OK")
        except subprocess.CalledProcessError as e:
            print(f"  [C] {prog} - FAIL: {e.stderr.strip()}")
        except Exception as e:
            print(f"  [C] {prog} - FAIL: {e}")

    return c_bin


def compile_cpp(cfg):
    """编译 C++ 程序（全部自实现算法，零第三方依赖）"""
    print("[C++] Compiling...")
    cpp_src = os.path.join(SRC_DIR, 'cpp')
    cpp_bin = os.path.join(SRC_DIR, 'bin', 'cpp')
    os.makedirs(cpp_bin, exist_ok=True)

    compiler = cfg['cpp_compiler']
    flags = cfg['cpp_flags'].split()

    programs = ['sort_bubble', 'sort_quick', 'matrix_multiply', 'fibonacci', 'prime_sieve', 'hash_sha256', 'str_kmp']

    for prog in programs:
        src_file = os.path.join(cpp_src, f'{prog}.cpp')
        bin_file = os.path.join(cpp_bin, prog)
        cmd = [compiler] + flags + [src_file, os.path.join(cpp_src, 'bench_util.cpp'),
               '-o', bin_file, '-lm']
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=30)
            print(f"  [C++] {prog} - OK")
        except subprocess.CalledProcessError as e:
            print(f"  [C++] {prog} - FAIL: {e.stderr.strip()}")
        except Exception as e:
            print(f"  [C++] {prog} - FAIL: {e}")

    return cpp_bin


def run_binary(bin_dir, prog_name, cfg):
    """运行单个二进制文件多次并收集结果"""
    bin_path = os.path.join(bin_dir, prog_name)
    if prog_name == 'sort_bubble' and os.path.exists(bin_path):
        ext = ''
    else:
        ext = '.exe' if platform.system() == 'Windows' else ''
    full_path = bin_path + ext

    # Generate args for C/C++ programs
    args = [
        '--array-size', str(cfg['array_size']),
        '--matrix-dim', str(cfg['matrix_dimension']),
        '--fib-n', str(cfg['fibonacci_n']),
        '--prime-limit', str(cfg['prime_limit']),
        '--hash-size', str(cfg['hash_data_mb']),
    ]

    lang = 'c' if 'c' in bin_dir and 'cpp' not in bin_dir else 'cpp'

    results = []
    for run_idx in range(cfg['runs_per_test']):
        try:
            out = subprocess.check_output([full_path] + args, text=True, timeout=120)
            # Parse JSON output line
            for line in out.strip().split('\n'):
                line = line.strip()
                if line.startswith('{'):
                    r = json.loads(line)
                    r['runs'] = [r['mean_ms']]
                    r['stddev_ms'] = 0
                    r['peak_memory_mb'] = 0
                    results.append(r)
                    break
        except FileNotFoundError:
            return None, f"binary not found: {full_path}"
        except subprocess.TimeoutExpired:
            return None, "timeout"
        except Exception as e:
            return None, str(e)

    if not results:
        return None, "no output"

    # Aggregate runs
    times = [r['mean_ms'] for r in results]
    aggregated = results[0].copy()
    aggregated['runs'] = [round(t, 4) for t in times]
    aggregated['mean_ms'] = round(sum(times) / len(times), 4)
    if len(times) > 1:
        avg = aggregated['mean_ms']
        var = sum((t - avg) ** 2 for t in times) / (len(times) - 1)
        aggregated['stddev_ms'] = round(math.sqrt(var), 4)
    else:
        aggregated['stddev_ms'] = 0
    return aggregated, None


def run_python(cfg):
    """运行 Python benchmark"""
    print("[Python] Running...")
    py_path = os.path.join(SRC_DIR, 'python', 'benchmark.py')
    try:
        out = subprocess.check_output(['python', py_path], text=True, timeout=600, cwd=SRC_DIR)
        data = json.loads(out)
        return data.get('results', []), data.get('failed', [])
    except FileNotFoundError:
        return [], [{'algorithm': '_python', 'language': 'python', 'error': 'python not found'}]
    except subprocess.TimeoutExpired:
        return [], [{'algorithm': '_python', 'language': 'python', 'error': 'timeout'}]
    except Exception as e:
        return [], [{'algorithm': '_python', 'language': 'python', 'error': str(e)}]


def run_java(cfg):
    """编译并运行 Java benchmark"""
    print("[Java] Compiling...")
    java_src = os.path.join(SRC_DIR, 'java')
    # Copy config for Java to read
    shutil.copy(os.path.join(BASE_DIR, 'config.yaml'), os.path.join(java_src, 'config.yaml'))

    gradlew = os.path.join(java_src, 'gradlew.bat' if platform.system() == 'Windows' else 'gradlew')

    # Check if gradlew exists
    if not os.path.exists(gradlew):
        print("  [Java] gradlew not found, generating wrapper...")
        # Create a simple manual compile
        return compile_java_manual(cfg, java_src)

    try:
        # Build jar
        subprocess.run([gradlew, 'clean', 'jar'], check=True, capture_output=True, text=True,
                       timeout=120, cwd=java_src)
        print("  [Java] Build OK")

        # Run
        print("[Java] Running...")
        java_home = cfg.get('java_home', '')
        java_bin = 'java'
        if java_home:
            java_bin = os.path.join(java_home, 'bin', 'java')

        vm_args = cfg['java_vm_args'].split()
        jar_file = os.path.join(java_src, 'build', 'libs', 'benchmark-1.0.0.jar')
        cmd = [java_bin] + vm_args + ['-jar', jar_file]
        out = subprocess.check_output(cmd, text=True, timeout=600, cwd=java_src)

        data = json.loads(out)
        return data.get('results', []), data.get('failed', [])
    except subprocess.CalledProcessError as e:
        return [], [{'algorithm': '_java', 'language': 'java', 'error': e.stderr.strip()}]
    except Exception as e:
        return [], [{'algorithm': '_java', 'language': 'java', 'error': str(e)}]


def compile_java_manual(cfg, java_src):
    """手动编译 Java（无需 gradlew）"""
    src_files = []
    for root, dirs, files in os.walk(os.path.join(java_src, 'src', 'main', 'java')):
        for f in files:
            if f.endswith('.java'):
                src_files.append(os.path.join(root, f))

    out_dir = os.path.join(java_src, 'build', 'classes')
    os.makedirs(out_dir, exist_ok=True)

    # Download snakeyaml if needed
    snake_yaml = os.path.join(java_src, 'lib', 'snakeyaml-2.2.jar')
    if not os.path.exists(snake_yaml):
        os.makedirs(os.path.join(java_src, 'lib'), exist_ok=True)
        # Try to copy from system
        print("  [Java] snakeyaml not found, attempting to download...")
        try:
            import urllib.request
            urllib.request.urlretrieve(
                'https://repo1.maven.org/maven2/org/yaml/snakeyaml/2.2/snakeyaml-2.2.jar',
                snake_yaml
            )
            print("  [Java] snakeyaml downloaded")
        except Exception:
            # Create stub if unavailable
            print("  [Java] WARNING: snakeyaml unavailable, Java tests may fail.")

    cp = out_dir
    if os.path.exists(snake_yaml):
        cp = out_dir + os.pathsep + snake_yaml

    try:
        print(f"  [Java] Compiling {len(src_files)} files...")
        subprocess.run(['javac', '-d', out_dir, '-cp', cp] + src_files,
                       check=True, capture_output=True, text=True, timeout=60)
        print("  [Java] Compile OK")

        print("[Java] Running...")
        try:
            import subprocess
            vm_args = cfg['java_vm_args'].split()
            result = subprocess.run(['java'] + vm_args + ['-cp', cp, 'benchmark.Benchmark'],
                                    capture_output=True, text=True, timeout=600, cwd=java_src)
            if result.returncode != 0:
                return [], [{'algorithm': '_java', 'language': 'java', 'error': result.stderr.strip()}]
            data = json.loads(result.stdout.strip().split('\n')[-1])
            return data.get('results', []), data.get('failed', [])
        except Exception as e:
            return [], [{'algorithm': '_java', 'language': 'java', 'error': str(e)}]
    except subprocess.CalledProcessError as e:
        return [], [{'algorithm': '_java', 'language': 'java', 'error': e.stderr.strip()}]
    except Exception as e:
        return [], [{'algorithm': '_java', 'language': 'java', 'error': str(e)}]


def run_c_binaries(cfg, bin_dir, language):
    """运行 C/C++ 编译好的程序"""
    if not bin_dir or not os.path.exists(bin_dir):
        print(f"[{language.upper()}] No binaries found, skipping.")
        return [], []

    programs = ['sort_bubble', 'sort_quick', 'matrix_multiply', 'fibonacci', 'hash_sha256', 'prime_sieve', 'str_kmp']

    results = []
    failed = []
    print(f"[{language.upper()}] Running...")
    for prog in programs:
        r, err = run_binary(bin_dir, prog, cfg)
        if err:
            print(f"  [{language.upper()}] {prog} - FAIL: {err}")
            failed.append({'algorithm': prog, 'language': language, 'error': err})
        elif r:
            print(f"  [{language.upper()}] {prog}: {r['mean_ms']:.2f} ms")
            results.append(r)

    # C binary fibonacci outputs both iter and rec
    return results, failed


def print_summary(all_results, all_failed):
    """打印汇总对比表"""
    print()
    print("=" * 70)
    print("                    Benchmark Summary")
    print("=" * 70)

    algos = ['bubble_sort', 'quick_sort', 'matrix_multiply', 'fibonacci_iter',
             'fibonacci_rec', 'prime_sieve', 'hash_fnv1a', 'str_kmp']
    langs = ['c', 'cpp', 'java', 'python']

    # Build lookup: {algo: {lang: mean_ms}}
    lookup = {}
    for r in all_results:
        algo = r['algorithm']
        lang = r['language']
        mean = r.get('mean_ms', 0)
        if algo not in lookup:
            lookup[algo] = {}
        lookup[algo][lang] = mean

    # Header
    header = f"{'Algorithm':<20} | {'C (ms)':>10} | {'C++ (ms)':>10} | {'Java (ms)':>10} | {'Python (ms)':>10}"
    print(header)
    print("-" * len(header))

    for algo in algos:
        row = f"{algo:<20} |"
        for lang in langs:
            val = lookup.get(algo, {}).get(lang)
            if val is not None:
                row += f" {val:>9.2f} |"
            else:
                row += f" {'N/A':>9} |"
        print(row)

    print("=" * 70)
    print("* C as baseline (relative = 1.0)")

    if all_failed:
        print()
        print("Failed tests:")
        for f in all_failed:
            print(f"  - [{f['language']}] {f['algorithm']}: {f['error']}")


def main():
    cfg = load_config()
    os.makedirs(RESULTS_DIR, exist_ok=True)

    machine = get_machine_info()
    envs = get_env_info(cfg)

    all_results = []
    all_failed = []

    # 1. Compile & Run C
    c_bin = None
    try:
        c_bin = compile_c(cfg)
    except Exception as e:
        all_failed.append({'algorithm': '_c_compile', 'language': 'c', 'error': str(e)})

    # 2. Compile & Run C++
    cpp_bin = None
    try:
        cpp_bin = compile_cpp(cfg)
    except Exception as e:
        all_failed.append({'algorithm': '_cpp_compile', 'language': 'cpp', 'error': str(e)})

    # 3. Run Python
    py_results, py_failed = run_python(cfg)
    all_results.extend(py_results)
    all_failed.extend(py_failed)

    # 4. Run Java
    java_results, java_failed = run_java(cfg)
    all_results.extend(java_results)
    all_failed.extend(java_failed)

    # 5. Run C binaries
    c_results, c_failed = run_c_binaries(cfg, c_bin, 'c')
    all_results.extend(c_results)
    all_failed.extend(c_failed)

    # 6. Run C++ binaries
    cpp_results, cpp_failed = run_c_binaries(cfg, cpp_bin, 'cpp')
    all_results.extend(cpp_results)
    all_failed.extend(cpp_failed)

    # Build summary
    summary = {}
    for r in all_results:
        algo = r['algorithm']
        lang = r['language']
        mean = r.get('mean_ms', 0)
        if algo not in summary:
            summary[algo] = {}
        summary[algo][lang] = {'mean_ms': mean, 'relative': 0}

    # Calculate relative (baseline = C)
    for algo, langs_data in summary.items():
        baseline = langs_data.get('c', {}).get('mean_ms', 1)
        if baseline == 0:
            baseline = 1
        for lang, d in langs_data.items():
            d['relative'] = round(d['mean_ms'] / baseline, 2)

    # Generate report
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    report = {
        'meta': {
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
            'machine': machine,
            'environments': envs,
            'config': {
                'runs_per_test': cfg['runs_per_test'],
                'warmup_runs': cfg['warmup_runs'],
                'array_size': cfg['array_size'],
                'matrix_dimension': cfg['matrix_dimension'],
                'fibonacci_n': cfg['fibonacci_n'],
                'prime_limit': cfg['prime_limit'],
                'hash_data_mb': cfg['hash_data_mb'],
                'string_length': cfg['string_length'],
                'pattern_length': cfg['pattern_length'],
            }
        },
        'results': all_results,
        'failed': all_failed,
        'summary': summary
    }

    report_path = os.path.join(RESULTS_DIR, f'report_{timestamp}.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved to: {report_path}")

    # Print summary
    print_summary(all_results, all_failed)


if __name__ == '__main__':
    main()
