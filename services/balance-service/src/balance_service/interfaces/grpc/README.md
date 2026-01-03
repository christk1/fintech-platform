Generate stubs locally (also done in the Docker build):

- `python -m balance_service.interfaces.grpc.gen_stubs`

This writes `balance_pb2.py`, `balance_pb2.pyi`, and `balance_pb2_grpc.py` into this folder.

Notes:
- `balance.proto` lives alongside the generated Python files (route_guide-style) so generated imports use the full module path.
