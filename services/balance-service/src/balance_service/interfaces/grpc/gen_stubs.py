from __future__ import annotations

import pathlib

import re

from grpc_tools import protoc


def main() -> None:
    base = pathlib.Path(__file__).resolve().parent
    # Route-guide style: proto is on the Python package path so generated imports
    # use the full module name (e.g. balance_service.interfaces.grpc.balance_pb2).
    proto_file = base / "balance.proto"

    # base = .../services/balance-service/src/balance_service/interfaces/grpc
    # include root must be the `src/` directory so generated modules import as `balance_service...`
    src_root = base.parents[2]

    proto_rel = proto_file.relative_to(src_root)

    args = [
        "grpc_tools.protoc",
        f"-I{src_root}",
        f"--python_out={src_root}",
        f"--pyi_out={src_root}",
        f"--grpc_python_out={src_root}",
        str(proto_rel),
    ]

    code = protoc.main(args)

    if code != 0:
        raise SystemExit(code)

    _postprocess_pb2(base / "balance_pb2.py")
    _postprocess_pb2_pyi(base / "balance_pb2.pyi")
    _postprocess_pb2_grpc(base / "balance_pb2_grpc.py")


def _postprocess_pb2(path: pathlib.Path) -> None:
    if not path.exists():
        return

    text = path.read_text(encoding="utf-8")

    # Remove runtime version validation to match classic protoc output style.
    text = re.sub(r"\nfrom google\\.protobuf import runtime_version as _runtime_version\n", "\n", text)
    text = re.sub(
        r"\n_runtime_version\\.ValidateProtobufRuntimeVersion\([\s\S]*?\)\n",
        "\n",
        text,
    )

    path.write_text(text, encoding="utf-8")


def _postprocess_pb2_pyi(path: pathlib.Path) -> None:
    if not path.exists():
        return

    text = path.read_text(encoding="utf-8")
    # Pyright/Pylance can report an incompatibility because protobuf Message stubs
    # often declare `__slots__` as an empty tuple type. Removing the assignment
    # avoids the tuple-size mismatch without losing useful type info.
    text = re.sub(r"^\s*__slots__\s*=\s*\([^\)]*\)\s*$\n?", "", text, flags=re.MULTILINE)
    path.write_text(text, encoding="utf-8")


def _postprocess_pb2_grpc(path: pathlib.Path) -> None:
    if not path.exists():
        return

    text = path.read_text(encoding="utf-8")

    # Remove warnings import and version-guard blocks introduced by newer generators.
    text = re.sub(r"\nimport warnings\n", "\n", text)
    text = re.sub(r"\nGRPC_GENERATED_VERSION[\s\S]*?\n\n\n", "\n", text, count=1)

    # Remove newer `_registered_method` plumbing.
    text = text.replace(",\n                _registered_method=True", "")
    text = text.replace(",\n            _registered_method=True", "")
    text = "".join(
        line for line in text.splitlines(keepends=True) if "add_registered_method_handlers" not in line
    )

    # Remove the optional EXPERIMENTAL API class block (uses grpc.experimental which isn't typed).
    # The normal Stub/Servicer/add_* function are sufficient for typical usage.
    text = re.sub(
        r"\n\n\s*# This class is part of an EXPERIMENTAL API\.[\s\S]*\Z",
        "\n",
        text,
    )

    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
