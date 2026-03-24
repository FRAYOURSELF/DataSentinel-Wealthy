FROM golang:1.22-alpine AS builder
WORKDIR /src
COPY go.mod ./
RUN go mod download
COPY . .
RUN go build -o /bin/go-prime-service ./main.go

FROM alpine:3.20
RUN adduser -D -u 10001 appuser
USER appuser
COPY --from=builder /bin/go-prime-service /bin/go-prime-service
EXPOSE 8080
CMD ["/bin/go-prime-service"]
