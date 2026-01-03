FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir -U pip \
  && pip install --no-cache-dir .

COPY src/ /app/src/

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src

# Generate gRPC stubs during image build
RUN python -m grpc_tools.protoc \
  -I /app/src/balance_service/interfaces/grpc/proto \
  --python_out=/app/src/balance_service/interfaces/grpc \
  --grpc_python_out=/app/src/balance_service/interfaces/grpc \
  /app/src/balance_service/interfaces/grpc/proto/balance.proto

EXPOSE 50051

CMD ["python", "-m", "balance_service.interfaces.grpc.server"]
