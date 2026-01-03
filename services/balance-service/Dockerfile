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
RUN python -m balance_service.interfaces.grpc.gen_stubs

EXPOSE 50051

CMD ["python", "-m", "balance_service.interfaces.grpc.server"]
