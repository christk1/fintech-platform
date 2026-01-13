from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _rewrite_grpc_imports(out_dir: Path) -> None:
    """Ensure generated gRPC modules work when placed inside a Python package.

    grpc_tools.protoc generates `import balance_pb2 as balance__pb2`, which assumes
    `balance_pb2` is importable from sys.path root. In this repo we place stubs
    under `.../infrastructure/grpc/`, so we need a relative import.
    """

    grpc_file = out_dir / "balance_pb2_grpc.py"
    if not grpc_file.exists():
        return

    content = grpc_file.read_text(encoding="utf-8")
    content2 = content.replace(
        "\nimport balance_pb2 as balance__pb2\n",
        "\nfrom . import balance_pb2 as balance__pb2\n",
    )
    if content2 != content:
        grpc_file.write_text(content2, encoding="utf-8")


def _run(cmd: list[str], *, cwd: Path) -> None:
    result = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)
    if result.returncode != 0:
        raise SystemExit(
            f"Command failed (exit={result.returncode})\n"
            f"cwd={cwd}\n"
            f"cmd={' '.join(cmd)}\n\n"
            f"stdout:\n{result.stdout}\n\n"
            f"stderr:\n{result.stderr}\n"
        )


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    proto_dir = repo_root / "services" / "balance-service" / "proto"
    proto_file = proto_dir / "balance.proto"

    if not proto_file.exists():
        raise SystemExit(f"Missing proto file: {proto_file}")

    targets = [
        repo_root / "services" / "api-gateway" / "src" / "api_gateway" / "infrastructure" / "grpc",
        repo_root / "services" / "worker" / "src" / "worker" / "infrastructure" / "grpc",
    ]

    python = sys.executable

    for out_dir in targets:
        out_dir.mkdir(parents=True, exist_ok=True)
        init_py = out_dir / "__init__.py"
        init_py.touch(exist_ok=True)

        cmd = [
            python,
            "-m",
            "grpc_tools.protoc",
            f"-I{proto_dir}",
            f"--python_out={out_dir}",
            f"--pyi_out={out_dir}",
            f"--grpc_python_out={out_dir}",
            str(proto_file),
        ]
        _run(cmd, cwd=repo_root)
        _rewrite_grpc_imports(out_dir)

    print("Generated Python gRPC stubs for balance.proto")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
