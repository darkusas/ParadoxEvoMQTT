#!/usr/bin/python3
import os
import subprocess
import sys
import tempfile

import yaml

DEFAULT_BINARY_PATH = "/opt/paraevo/paraevo"
DEFAULT_CONFIG_FILE = "/etc/paraevo.yaml"
DEFAULT_LOG_MAX_SIZE_MB = 10


def append_with_limit(path, data, max_size_bytes):
    if max_size_bytes <= 0:
        max_size_bytes = DEFAULT_LOG_MAX_SIZE_MB * 1024 * 1024

    log_dir = os.path.dirname(path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    target_dir = log_dir if log_dir else "."

    def write_atomic(content):
        fd, temp_path = tempfile.mkstemp(dir=target_dir, prefix=".paraevo-log-", suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(content)
            os.replace(temp_path, path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    existing_size = os.path.getsize(path) if os.path.exists(path) else 0
    if len(data) >= max_size_bytes:
        write_atomic(data[-max_size_bytes:])
        return

    if existing_size + len(data) <= max_size_bytes:
        try:
            with open(path, "ab") as f:
                f.write(data)
        except OSError:
            write_atomic(data)
        return

    keep = max_size_bytes - len(data)
    with open(path, "rb") as f:
        if keep > 0:
            f.seek(max(existing_size - keep, 0))
            tail = f.read(keep)
        else:
            tail = b""

    write_atomic(tail + data)


def parse_zone_entry(zone):
    if isinstance(zone, (int, float)):
        return int(zone), {}

    if isinstance(zone, dict) and "num" in zone:
        meta = {}
        for key in ("name", "device_class", "entity_category", "icon"):
            value = zone.get(key)
            if value is not None and value != "":
                meta[key] = str(value)
        return int(zone["num"]), meta

    raise ValueError("Invalid zone config entry!")


config_file = DEFAULT_CONFIG_FILE
if len(sys.argv) > 1:
    config_file = sys.argv[1]

with open(config_file, "r") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

binary_path = config.get("binary_path", DEFAULT_BINARY_PATH)
args = [binary_path]

enable_full_logging = bool(config.get("log", False) or config.get("verbose", False))
if enable_full_logging:
    args.append("-v")

if config.get("daemon") is True:
    args.append("-D")

if "device" in config:
    args.extend(["-d", str(config["device"])])
else:
    print("Device not present in config!")
    exit(-1)

if "mqtt" in config:
    if "server" in config["mqtt"]:
        args.append("--mqtt_server=" + str(config["mqtt"]["server"]))
    else:
        print("No MQTT server in config!")

    if "port" in config["mqtt"]:
        args.append("--mqtt_port=" + str(config["mqtt"]["port"]))

    if "login" in config["mqtt"]:
        args.append("--mqtt_login=" + str(config["mqtt"]["login"]))

    if "password" in config["mqtt"]:
        args.append("--mqtt_password=" + str(config["mqtt"]["password"]))

    if config["mqtt"].get("retain") is True:
        args.append("-r")

else:
    print("No MQTT settings in config!")
    exit(-1)

if "areas" in config:
    for area in config["areas"]:
        if "num" in area:
            args.extend(["-a", str(area["num"])])
        else:
            print("Area config does not have \"num\"!")
            exit(-1)

        if "zones" in area:
            zone_nums = []
            for zone in area["zones"]:
                try:
                    zone_num, meta = parse_zone_entry(zone)
                except ValueError as exc:
                    print(str(exc))
                    exit(-1)

                zone_nums.append(str(zone_num))
                if "name" in meta:
                    args.append(f"--zone_name={zone_num}:{meta['name']}")
                if "device_class" in meta:
                    args.append(f"--zone_device_class={zone_num}:{meta['device_class']}")
                if "entity_category" in meta:
                    args.append(f"--zone_entity_category={zone_num}:{meta['entity_category']}")
                if "icon" in meta:
                    args.append(f"--zone_icon={zone_num}:{meta['icon']}")
            args.extend(["-z", ",".join(zone_nums)])
        else:
            print("Area config does not have zones!")
            exit(-1)
else:
    print("No area config!")
    exit(-1)

if "user_code" in config and config["user_code"] != "":
    args.extend(["-u", str(config["user_code"])])

if "status_period" in config:
    args.extend(["-S", str(config["status_period"])])

print("The final command:")
print("(hidden for security)")

log_file = config.get("log_file")
log_max_size_mb = config.get("log_max_size_mb", DEFAULT_LOG_MAX_SIZE_MB)
try:
    log_max_size_bytes = int(log_max_size_mb) * 1024 * 1024
except (TypeError, ValueError):
    print("Invalid log_max_size_mb value in config, using default 10 MB")
    log_max_size_bytes = DEFAULT_LOG_MAX_SIZE_MB * 1024 * 1024

if log_file:
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while True:
        chunk = proc.stdout.read(4096)
        if not chunk:
            break
        append_with_limit(str(log_file), chunk, log_max_size_bytes)
    sys.exit(proc.wait())
else:
    sys.exit(subprocess.call(args))
