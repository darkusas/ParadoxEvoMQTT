#!/usr/bin/env python3

import os
import subprocess
import sys
from pathlib import Path

import yaml


def _as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return default


def _load_config(path: str) -> dict:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError("Config root must be a YAML mapping")

    return data


def _zone_num(zone) -> int:
    if isinstance(zone, int):
        return zone
    if isinstance(zone, dict) and "num" in zone:
        return int(zone["num"])
    raise ValueError(f"Invalid zone entry: {zone!r}")


def _zone_name(zone) -> str | None:
    if isinstance(zone, dict):
        name = zone.get("name")
        if name is None:
            return None
        name = str(name)
        return name
    return None


def _zone_attrs(zone) -> dict[str, str]:
    if not isinstance(zone, dict):
        return {}

    attrs: dict[str, str] = {}
    for key in ("device_class", "entity_category", "icon"):
        value = zone.get(key)
        if value is None:
            continue
        value = str(value).strip()
        if value == "":
            continue
        attrs[key] = value
    return attrs


def _maybe_trim_log_file(log_path: Path, max_size_mb: int | str | None) -> None:
    try:
        max_size_mb = int(max_size_mb) if max_size_mb is not None else 10
    except (TypeError, ValueError):
        raise ValueError("log_max_size_mb must be an integer")

    if max_size_mb < 1:
        raise ValueError("log_max_size_mb must be >= 1")

    max_size_bytes = max_size_mb * 1024 * 1024

    if log_path.exists():
        file_size = log_path.stat().st_size
    else:
        file_size = 0

    if file_size > max_size_bytes:
        keep_bytes = min(file_size, max_size_bytes)
        with log_path.open("rb") as f:
            f.seek(-keep_bytes, os.SEEK_END)
            tail = f.read()

        first_newline = tail.find(b"\n")
        if first_newline >= 0 and first_newline + 1 < len(tail):
            tail = tail[first_newline + 1:]

        with log_path.open("wb") as f:
            f.write(tail)


def build_args(cfg: dict) -> list[str]:
    device = cfg.get("device")
    if not device:
        raise ValueError("Missing required key: device")

    binary_path = str(cfg.get("binary_path") or "/opt/paraevo/paraevo")

    args: list[str] = [binary_path]

    if _as_bool(cfg.get("verbose"), default=False) or _as_bool(cfg.get("log"), default=False):
        args.append("-v")

    if _as_bool(cfg.get("daemon"), default=False):
        args.append("-D")

    args.extend(["-d", str(device)])

    mqtt = cfg.get("mqtt") or {}
    if not isinstance(mqtt, dict):
        raise ValueError("mqtt must be a mapping")

    mqtt_server = mqtt.get("server")
    if not mqtt_server:
        raise ValueError("Missing required key: mqtt.server")

    args.append(f"--mqtt_server={mqtt_server}")

    mqtt_port = mqtt.get("port")
    if mqtt_port is not None:
        args.append(f"--mqtt_port={int(mqtt_port)}")

    mqtt_login = mqtt.get("login")
    if mqtt_login:
        args.append(f"--mqtt_login={mqtt_login}")

    mqtt_password = mqtt.get("password")
    if mqtt_password:
        args.append(f"--mqtt_password={mqtt_password}")

    if _as_bool(mqtt.get("retain"), default=False):
        args.append("-r")

    user_code = cfg.get("user_code")
    if user_code is not None and str(user_code) != "":
        args.extend(["-u", str(user_code)])

    areas = cfg.get("areas")
    if not isinstance(areas, list) or not areas:
        raise ValueError("areas must be a non-empty list")

    for area in areas:
        if not isinstance(area, dict) or "num" not in area:
            raise ValueError(f"Invalid area entry: {area!r}")

        area_num = int(area["num"])
        zones = area.get("zones")
        if not isinstance(zones, list) or not zones:
            raise ValueError(f"Area {area_num} has no zones list")

        zone_numbers = [str(_zone_num(z)) for z in zones]

        args.extend(["-a", str(area_num), "-z", ",".join(zone_numbers)])

        for z in zones:
            zn = _zone_num(z)
            name = _zone_name(z)
            if name is not None and name != "":
                args.append(f"--zone_name={zn}:{name}")

            attrs = _zone_attrs(z)
            if "device_class" in attrs:
                args.append(f"--zone_device_class={zn}:{attrs['device_class']}")
            if "entity_category" in attrs:
                args.append(f"--zone_entity_category={zn}:{attrs['entity_category']}")
            if "icon" in attrs:
                args.append(f"--zone_icon={zn}:{attrs['icon']}")

    status_period = cfg.get("status_period")
    if status_period is not None:
        args.extend(["-S", str(int(status_period))])

    return args


def main() -> int:
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "/etc/paraevo.yaml"
    cfg = _load_config(cfg_path)

    args = build_args(cfg)

    # Logging redirection (append). If not set, inherit container stdout/stderr.
    log_file = cfg.get("log_file")
    if log_file:
        log_path = Path(str(log_file))
        log_path.parent.mkdir(parents=True, exist_ok=True)
        _maybe_trim_log_file(log_path, cfg.get("log_max_size_mb"))
        with log_path.open("a", encoding="utf-8") as f:
            print("The final command:")
            print(" ".join(args))
            f.write("The final command:\n")
            f.write(" ".join(args) + "\n")
            f.flush()
            proc = subprocess.run(args, stdout=f, stderr=subprocess.STDOUT)
            return int(proc.returncode)

    print("The final command:")
    print(" ".join(args))
    proc = subprocess.run(args)
    return int(proc.returncode)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"start_daemon.py error: {e}", file=sys.stderr)
        raise
