import math


def is_prime(number: int) -> bool:
    if number < 2:
        return False
    if number == 2:
        return True
    if number % 2 == 0:
        return False
    limit = int(math.isqrt(number))
    divisor = 3
    while divisor <= limit:
        if number % divisor == 0:
            return False
        divisor += 2
    return True


def primes_up_to(n: int) -> list[int]:
    if n < 2:
        return []
    if n == 2:
        return [2]

    # Odd-only sieve for improved speed and memory use.
    size = (n // 2) + 1
    sieve = bytearray(b"\x01") * size
    sieve[0] = 0

    limit = int(math.isqrt(n))
    p = 3
    while p <= limit:
        idx = p // 2
        if sieve[idx]:
            start = (p * p) // 2
            step = p
            sieve[start::step] = b"\x00" * (((size - 1 - start) // step) + 1)
        p += 2

    result = [2]
    result.extend(2 * i + 1 for i in range(1, size) if sieve[i] and (2 * i + 1) <= n)
    return result
