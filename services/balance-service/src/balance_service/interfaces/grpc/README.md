Generate stubs locally (also done in the Docker build):

- `python -m balance_service.interfaces.grpc.gen_stubs`

This writes `balance_pb2.py` and `balance_pb2_grpc.py` into this folder.
