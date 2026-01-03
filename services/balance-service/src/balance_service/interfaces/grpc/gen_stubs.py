from __future__ import annotations

import pathlib

from grpc_tools import protoc


def main() -> None:
    base = pathlib.Path(__file__).resolve().parent
    proto_dir = base / "proto"
    proto_file = proto_dir / "balance.proto"

    out_dir = base

    args = [
        "grpc_tools.protoc",
        f"-I{proto_dir}",
        f"--python_out={out_dir}",
        f"--grpc_python_out={out_dir}",
        str(proto_file),
    ]

    code = protoc.main(args)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
