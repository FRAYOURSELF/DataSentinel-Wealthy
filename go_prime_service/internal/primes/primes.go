package primes

import "math"

func IsPrime(number int64) bool {
	if number < 2 {
		return false
	}
	if number == 2 {
		return true
	}
	if number%2 == 0 {
		return false
	}
	limit := int64(math.Sqrt(float64(number)))
	for i := int64(3); i <= limit; i += 2 {
		if number%i == 0 {
			return false
		}
	}
	return true
}

func simpleSieve(limit int) []int {
	if limit < 2 {
		return []int{}
	}
	isPrime := make([]bool, limit+1)
	for i := 2; i <= limit; i++ {
		isPrime[i] = true
	}
	for p := 2; p*p <= limit; p++ {
		if isPrime[p] {
			for j := p * p; j <= limit; j += p {
				isPrime[j] = false
			}
		}
	}
	primes := make([]int, 0)
	for i := 2; i <= limit; i++ {
		if isPrime[i] {
			primes = append(primes, i)
		}
	}
	return primes
}

func SegmentedPrimes(n int) []int {
	if n < 2 {
		return []int{}
	}
	if n == 2 {
		return []int{2}
	}

	limit := int(math.Sqrt(float64(n))) + 1
	basePrimes := simpleSieve(limit)
	result := make([]int, 0)

	segmentSize := max(limit, 32768)
	low := 2
	high := min(low+segmentSize-1, n)

	for low <= n {
		segment := make([]bool, high-low+1)
		for i := range segment {
			segment[i] = true
		}

		for _, p := range basePrimes {
			if p*p > high {
				break
			}
			start := ((low + p - 1) / p) * p
			if start < p*p {
				start = p * p
			}
			for j := start; j <= high; j += p {
				segment[j-low] = false
			}
		}

		for i := low; i <= high; i++ {
			if i >= 2 && segment[i-low] {
				result = append(result, i)
			}
		}

		low = high + 1
		high = min(low+segmentSize-1, n)
	}

	return result
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
