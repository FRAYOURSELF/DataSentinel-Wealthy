import math


def primes_in_segment(start: int, end: int) -> list[int]:
    if end < 2 or end < start:
        return []
    start = max(start, 2)
    size = end - start + 1
    is_prime = [True] * size

    limit = int(math.sqrt(end))
    base = [True] * (limit + 1)
    base[0:2] = [False, False]
    for p in range(2, int(math.sqrt(limit)) + 1):
        if base[p]:
            for multiple in range(p * p, limit + 1, p):
                base[multiple] = False
    base_primes = [i for i, ok in enumerate(base) if ok]

    for p in base_primes:
        first = max(p * p, ((start + p - 1) // p) * p)
        for multiple in range(first, end + 1, p):
            is_prime[multiple - start] = False

    return [start + i for i, ok in enumerate(is_prime) if ok]
