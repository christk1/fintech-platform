from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class TerraformOutputs:
    events_queue_url: str | None
    rds_endpoint: str | None
    redis_port: int | None


def _run_terraform_output(tf_dir: Path) -> dict:
    result = subprocess.run(
        ["terraform", "output", "-json"],
        cwd=str(tf_dir),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Failed to read terraform outputs. "
            f"cwd={tf_dir} exit={result.returncode}\n"
            f"stdout:\n{result.stdout}\n\n"
            f"stderr:\n{result.stderr}"
        )
    return json.loads(result.stdout or "{}")


def _parse_outputs(raw: dict) -> TerraformOutputs:
    def get_str(name: str) -> str | None:
        value = raw.get(name, {}).get("value")
        return value if isinstance(value, str) and value else None

    def get_int(name: str) -> int | None:
        value = raw.get(name, {}).get("value")
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return None

    return TerraformOutputs(
        events_queue_url=get_str("events_queue_url"),
        rds_endpoint=get_str("rds_endpoint"),
        redis_port=get_int("redis_port"),
    )


_ENV_KV_RE = re.compile(r"^(?P<key>[A-Z0-9_]+)=(?P<value>.*)$")


def _load_env_lines(env_file: Path) -> list[str]:
    if not env_file.exists():
        return []
    return env_file.read_text(encoding="utf-8").splitlines(keepends=False)


def _extract_host_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    return parsed.hostname


def _extract_port_from_url(url: str) -> int | None:
    parsed = urlparse(url)
    return parsed.port


def _sync_env(
    lines: list[str],
    outputs: TerraformOutputs,
    *,
    aws_endpoint_url: str | None,
    database_url: str | None,
    redis_url: str | None,
    sqs_queue_url: str | None,
) -> list[str]:
    # We keep the *host* from the existing env (usually host.docker.internal)
    # and only overwrite the ports/paths based on Terraform outputs.
    aws_host = _extract_host_from_url(aws_endpoint_url or "")
    aws_port = _extract_port_from_url(aws_endpoint_url or "")

    # SQS queue url
    new_sqs_url: str | None = None
    if outputs.events_queue_url and aws_host and aws_port:
        parsed = urlparse(outputs.events_queue_url)
        new_sqs_url = f"{parsed.scheme}://{aws_host}:{aws_port}{parsed.path}"

    # RDS
    new_database_url: str | None = None
    if outputs.rds_endpoint and database_url:
        rds_host_port = outputs.rds_endpoint
        rds_port = None
        try:
            rds_port = int(rds_host_port.split(":")[-1])
        except Exception:
            rds_port = None
        if aws_host and rds_port is not None:
            parsed_db = urlparse(database_url)
            # Keep creds + dbname; swap host/port.
            userinfo = ""
            if parsed_db.username:
                userinfo = parsed_db.username
                if parsed_db.password:
                    userinfo += f":{parsed_db.password}"
                userinfo += "@"
            db_path = parsed_db.path or "/"
            new_database_url = f"{parsed_db.scheme}://{userinfo}{aws_host}:{rds_port}{db_path}"

    # Redis
    new_redis_url: str | None = None
    if outputs.redis_port is not None and redis_url:
        if aws_host:
            parsed_redis = urlparse(redis_url)
            db_path = parsed_redis.path or ""
            new_redis_url = f"{parsed_redis.scheme}://{aws_host}:{outputs.redis_port}{db_path}"

    updates: dict[str, str] = {}
    if new_sqs_url:
        updates["SQS_PAYMENTS_QUEUE_URL"] = new_sqs_url
    if new_database_url:
        updates["DATABASE_URL"] = new_database_url
    if new_redis_url:
        updates["REDIS_URL"] = new_redis_url

    if not updates:
        return lines

    out: list[str] = []
    seen: set[str] = set()

    for line in lines:
        m = _ENV_KV_RE.match(line)
        if not m:
            out.append(line)
            continue
        key = m.group("key")
        if key in updates:
            out.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            out.append(line)

    # Append missing keys at end (keep file usable even if user deleted them)
    missing = [k for k in updates.keys() if k not in seen]
    if missing:
        if out and out[-1].strip() != "":
            out.append("")
        for k in missing:
            out.append(f"{k}={updates[k]}")

    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tf-dir", default="infra/envs/local")
    parser.add_argument("--env-file", default=".env")
    args = parser.parse_args()

    repo_root = Path(os.getcwd())
    tf_dir = (repo_root / args.tf_dir).resolve()
    env_file = (repo_root / args.env_file).resolve()

    raw = _run_terraform_output(tf_dir)
    outputs = _parse_outputs(raw)

    lines = _load_env_lines(env_file)

    # Read current values to preserve hostname conventions.
    current: dict[str, str] = {}
    for line in lines:
        m = _ENV_KV_RE.match(line)
        if m:
            current[m.group("key")] = m.group("value")

    new_lines = _sync_env(
        lines,
        outputs,
        aws_endpoint_url=current.get("AWS_ENDPOINT_URL"),
        database_url=current.get("DATABASE_URL"),
        redis_url=current.get("REDIS_URL"),
        sqs_queue_url=current.get("SQS_PAYMENTS_QUEUE_URL"),
    )

    if new_lines != lines:
        env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        print(f"Synced {env_file.name} from Terraform outputs.")
    else:
        print(f"{env_file.name} already matches Terraform outputs.")

    # Minimal sanity check: if redis_port exists, ensure REDIS_URL port matches.
    if outputs.redis_port is not None:
        redis_value = None
        for line in new_lines:
            if line.startswith("REDIS_URL="):
                redis_value = line.split("=", 1)[1]
                break
        if redis_value is not None:
            parsed = urlparse(redis_value)
            if parsed.port is not None and parsed.port != outputs.redis_port:
                print(
                    f"Warning: REDIS_URL port {parsed.port} != terraform redis_port {outputs.redis_port}",
                    file=sys.stderr,
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
