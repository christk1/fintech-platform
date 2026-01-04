FROM golang:1.25-alpine AS build

WORKDIR /src

ENV PATH=/usr/local/go/bin:/go/bin:$PATH

RUN apk add --no-cache protobuf git

COPY go.mod ./
RUN go mod download

COPY . .

RUN go install google.golang.org/protobuf/cmd/protoc-gen-go@latest \
  && go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

RUN protoc \
  --go_out=. --go_opt=paths=source_relative \
  --go-grpc_out=. --go-grpc_opt=paths=source_relative \
  proto/balance.proto

RUN CGO_ENABLED=0 go build -o /out/balance-service ./cmd/server


FROM alpine:3.23

WORKDIR /app

COPY --from=build /out/balance-service /app/balance-service

ENV HOST=0.0.0.0
ENV PORT=50051

EXPOSE 50051

CMD ["/app/balance-service"]
