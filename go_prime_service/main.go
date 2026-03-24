package main

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"

	"go-prime-service/internal/observability"
	"go-prime-service/internal/primes"

	"github.com/prometheus/client_golang/prometheus/promhttp"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
)

type errorResponse struct {
	Error string `json:"error"`
}

type checkPrimeResponse struct {
	Number  int64 `json:"number"`
	IsPrime bool  `json:"is_prime"`
}

type primesResponse struct {
	N      int   `json:"n"`
	Count  int   `json:"count"`
	Primes []int `json:"primes"`
}

func main() {
	shutdown := initTracer()
	defer shutdown()
	observability.MustRegister()
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	addr := ":" + port

	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.Handler())
	mux.Handle("/health", otelhttp.NewHandler(http.HandlerFunc(healthHandler), "health"))
	mux.Handle("/check-prime", otelhttp.NewHandler(withMetrics("/check-prime", http.HandlerFunc(checkPrimeHandler)), "check-prime"))
	mux.Handle("/primes", otelhttp.NewHandler(withMetrics("/primes", http.HandlerFunc(primesHandler)), "primes"))

	server := &http.Server{
		Addr:              addr,
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
	}

	log.Printf("go-prime-service listening on %s", addr)
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("server failed: %v", err)
	}
}

func withMetrics(path string, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		wrapped := &statusRecorder{ResponseWriter: w, status: 200}
		next.ServeHTTP(wrapped, r)

		statusClass := strconv.Itoa(wrapped.status/100) + "xx"
		observability.RequestsTotal.WithLabelValues(path, r.Method, statusClass).Inc()
		observability.RequestDuration.WithLabelValues(path, r.Method).Observe(time.Since(start).Seconds())
		if wrapped.status >= 400 {
			observability.ErrorsTotal.WithLabelValues(path).Inc()
		}
	})
}

type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (r *statusRecorder) WriteHeader(statusCode int) {
	r.status = statusCode
	r.ResponseWriter.WriteHeader(statusCode)
}

func healthHandler(w http.ResponseWriter, _ *http.Request) {
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte("ok"))
}

func checkPrimeHandler(w http.ResponseWriter, r *http.Request) {
	numberRaw := r.URL.Query().Get("number")
	number, err := strconv.ParseInt(numberRaw, 10, 64)
	if err != nil || number < 0 {
		writeJSON(w, http.StatusBadRequest, errorResponse{Error: "invalid number"})
		return
	}
	writeJSON(w, http.StatusOK, checkPrimeResponse{Number: number, IsPrime: primes.IsPrime(number)})
}

func primesHandler(w http.ResponseWriter, r *http.Request) {
	nRaw := r.URL.Query().Get("n")
	n, err := strconv.Atoi(nRaw)
	if err != nil || n < 2 || n > 5_000_000 {
		writeJSON(w, http.StatusBadRequest, errorResponse{Error: "n must be between 2 and 5000000"})
		return
	}
	values := primes.SegmentedPrimes(n)
	writeJSON(w, http.StatusOK, primesResponse{N: n, Count: len(values), Primes: values})
}

func writeJSON(w http.ResponseWriter, statusCode int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	_ = json.NewEncoder(w).Encode(payload)
}

func initTracer() func() {
	endpoint := os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
	if endpoint == "" {
		endpoint = "otel-collector:4317"
	}

	exporter, err := otlptracegrpc.New(context.Background(), otlptracegrpc.WithEndpoint(endpoint), otlptracegrpc.WithInsecure())
	if err != nil {
		log.Printf("otel exporter init failed: %v", err)
		return func() {}
	}

	res, _ := resource.Merge(
		resource.Default(),
		resource.NewWithAttributes(
			semconv.SchemaURL,
			semconv.ServiceName("go-prime-service"),
		),
	)
	provider := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
	)
	otel.SetTracerProvider(provider)

	return func() {
		ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		defer cancel()
		_ = provider.Shutdown(ctx)
	}
}
