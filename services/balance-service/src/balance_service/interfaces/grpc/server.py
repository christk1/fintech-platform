from __future__ import annotations

import os
from concurrent import futures

import grpc

from balance_service.interfaces.grpc import balance_pb2, balance_pb2_grpc


class BalanceService(balance_pb2_grpc.BalanceServiceServicer):
    def Ping(
        self, request: balance_pb2.PingRequest, context: grpc.ServicerContext
    ) -> balance_pb2.PingResponse:
        # Stateless hot-path service: no business logic here.
        return balance_pb2.PingResponse(status="ok")


def serve() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "50051"))

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    balance_pb2_grpc.add_BalanceServiceServicer_to_server(BalanceService(), server)
    server.add_insecure_port(f"{host}:{port}")

    server.start()
    server.wait_for_termination()


def main() -> None:
    serve()


if __name__ == "__main__":
    main()
