"""埃拉托色尼筛法质数筛选"""
def sieve_of_eratosthenes(limit):
    is_prime = [True] * (limit + 1)
    is_prime[0] = is_prime[1] = False
    for i in range(2, int(limit ** 0.5) + 1):
        if is_prime[i]:
            step = i
            start = i * i
            for j in range(start, limit + 1, step):
                is_prime[j] = False
    return [i for i, prime in enumerate(is_prime) if prime]

def run_prime_sieve(limit):
    return sieve_of_eratosthenes(limit)
