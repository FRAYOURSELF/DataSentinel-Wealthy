package observability

import "github.com/prometheus/client_golang/prometheus"

var (
	RequestsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{Name: "go_prime_http_requests_total", Help: "Total requests"},
		[]string{"path", "method", "status"},
	)
	RequestDuration = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{Name: "go_prime_http_request_duration_seconds", Help: "Request latency", Buckets: prometheus.DefBuckets},
		[]string{"path", "method"},
	)
	ErrorsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{Name: "go_prime_http_errors_total", Help: "Error responses"},
		[]string{"path"},
	)
)

func MustRegister() {
	prometheus.MustRegister(RequestsTotal, RequestDuration, ErrorsTotal)
}
