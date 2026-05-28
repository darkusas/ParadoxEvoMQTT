# Paradox EVO MQTT
This is a Linux daemon for interacting with Paradox EVO48/92/192 security panel via MQTT using Paradox PRT3 module. The PRT3 module provides a serial interface for interacting with the panel, it's the "official" module for smart house integration according to Paradox themselves.

This daemon is made with the purpose for interaction with the Home Assistant and complies with it's defaul MQTT Alarm Panel interface.

# Version history
## v0.10
Fixed partial buffered reading (null characters were getting in a way).

## v0.9
Added a safety clauses after daemon crashed with unexpected and apparently malformed G000N000A000 event.

## v0.8
Fixed a bug which prevented timely report of Armed state after the Exit Delay.

## v0.7
The syscall reading abuse was fixed. Instead of banging `read` with one byte added an intermediate buffer to read as much bytes as are possible at any given time and parse it.

Also added "arming" state, i.e. when Exit Delay is triggered by Arm command. However, in "Stay Arm" mode the first event is actually "Arm" event, so it is not updated to "Arming", in "Stay Arm" the status goes right away to "arm_home".

## v0.6
Added MQTT username/password options and a flag if to retain all the messages sent by the daemon. Retain can be helpful when Home Assistant (or other "house mind") is restarted. If messages are not retained, Home Assistant would not know the immediate state of the panel and set it to "unknown".

Also enhanced the loader script a bit:
* Ability to override daemon binary's path
* Ability to provide a log file to redirect daemon's output

## v0.5
Area status management rewritten. Instead of calling area status on every important event, the more intelligent parsing of those events added. The area status is still requested, but only periodically on given timeout when there's no other activity.

Some thread related memory leaks (well, their sympthoms) fixed by detaching particular independent threads.

MQTT async client disconnection fixed and done properly with full destroy.

## v0.4
Adding Disarm functionality and a few fixes.
* Providing `-u` switch to give panel's user code for Disarm action
* Adding a forced delay between Area Status requests to prevent crashing (temporary solution)

## v0.3
This is the first public release and it includes the following functionality:
* Reporting each area (1-8 in EVO96/192 case) as separate security panels: generic state and full state from PRT3
* Reporting each zone's state on/off, zone's alarm on/off and full zone's state from PRT3.
* Arm and Stay Arm commands via MQTT (no Disarm yet!)
* Utility Key press command
* Only open MQTT server (no user/password)

# Building the daemon
There are handy Dockerfiles provided. One is prepared for the build environment. The script `docker-buildenv.sh` builds required image and then enters into shell with it.

**NOTE**: check the script, uncomment image building. See what's the PRT3's path on your system and change accordingly! Also check your Linux user's ID and Group ID and change in the Dockerfile!

You may build the daemon right on your Linux, just install the same dependencies listed in the Dockerfile and you're good to go.

The second Dockerfile is for _Production Environment_. After daemon is successfully built and compiled, run building of the Production image. It will install only running dependencies and copy entrypoint file together with daemon's binary.

Edit `Config` to build either debugging version or release. Prepare production image with either version, if you wish, however Release version will be faster (obviously, but probably unnoticable for human).

# Running the daemon
Daemon is controlled via command line switches. However, for running in Production Environment (either docker or right in the Linux) there's a more friendly way to start it up: a Python script `start_daemon.py` (which is an entry point for the Production Docker image) and a more friendly YAML configuration, which should be available at `/etc/paraevo.yaml`.

## Areas and zones
Paradox EVO panels can be configured in separate Areas or Partitions. Each of them can be considered a separate security system, simply running on one board. These are mostly used in multi-office environments, where each office has its own area/partition assigned. Less common is a use at home. For example, the living space can be assigned to one partition, and the attick to another (which is always in Armed state).

However, PRT3 _does not provide_ any means to discover, which zone (i.e. motion/door/window/smoke sensor) is assigned to which area. So this is up to the end user to map.

Example daemon command with one area:
`./paraevo -v -d /dev/ttyUSB0 -a 1 -z 1,2,3,4,5,6,7,10 --mqtt_server=192.168.0.100`

Example daemon command with two areas:
`./paraevo -v -d /dev/ttyUSB0 -a 1 -z 1,2,3,4,5,6,7,10 -a 2 -z 11,12,13,14,15 --mqtt_server=192.168.0.100`

It is important to keep the order of the switches. I.e. `-a` must be succeeded by `-z`, then the next `-a`. Other switches can be in either order, but areas/zones should be sequential.

## Serial Device Path
I suggest using not the `/dev/ttyUSB`, as in above examples, because these might change. Especially, if PC has more serial devices connected. The better way is to use the unique path:
`-d /dev/serial/by-id/usb-PARADOX_PARADOX_APR-PRT3_a4008936-if00-port0`

To find your PRT3's path list `/dev/serial/by-id`.

**NOTE**: not all Linux systems support this. Some embedded or custom flavours provide only `/dev/ttyUSB*`, which can be a headache to manage after system restart. But... _es la vida_.

## Use the paraevo.yaml
Instead of passing command-line switches every time, the recommended way to configure the daemon is via a YAML file (default location `/etc/paraevo.yaml`). The Python script `start_daemon.py` reads this file, builds the equivalent command, and executes it.

**NOTE**: `start_daemon.py` has hardcoded default paths (`/opt/paraevo/paraevo` for the binary, `/etc/paraevo.yaml` for the config). You can override the config path by passing it as an argument: `python3 start_daemon.py /path/to/my.yaml`. Change the binary path with the `binary_path` key inside the YAML file.

### Configuration keys

| Key | Required | Description |
|-----|----------|-------------|
| `device` | **Yes** | Path to the serial device where PRT3 is connected |
| `binary_path` | No | Override path to the `paraevo` binary (default: `/opt/paraevo/paraevo`) |
| `log_file` | No | Write daemon stdout/stderr to this file (with size cap) |
| `log_max_size_mb` | No | Maximum log file size in MB (default: `10`) |
| `daemon` | No | Run in background as a daemon (`true`/`false`, default `false`) |
| `log` | No | Enable full logging (`true`/`false`). Default `false` = only `ERROR` logs |
| `verbose` | No | Legacy alias of `log` for backward compatibility |
| `status_period` | No | Seconds between periodic area-status requests when idle (default: 60) |
| `user_code` | No | Panel user code — **required for Disarm** |
| `mqtt.server` | **Yes** | IP address or hostname of the MQTT broker |
| `mqtt.port` | No | MQTT broker port (default: `1883`) |
| `mqtt.login` | No | MQTT username |
| `mqtt.password` | No | MQTT password |
| `mqtt.retain` | No | Retain all published messages (`true`/`false`). Recommended `true` so Home Assistant knows the last state after a restart |
| `areas` | **Yes** | List of areas/partitions to monitor (at least one required) |
| `areas[].num` | **Yes** | Area number (1–8) |
| `areas[].zones` | **Yes** | List of zones assigned to this area. Each zone is either a bare number or an object with `num` and optional metadata fields |
| `zones[].num` | **Yes** | Zone number |
| `zones[].name` | No | Human-readable zone name, used for Home Assistant MQTT auto-discovery labels |
| `zones[].device_class` | No | Home Assistant `device_class` for the zone (default: `motion`) |
| `zones[].entity_category` | No | Optional Home Assistant `entity_category` |
| `zones[].icon` | No | Optional Home Assistant `icon` |

### Full annotated example

```yaml
# Path to the USB serial device where PRT3 is attached.
# Using the stable by-id path is recommended over /dev/ttyUSB* which can change on reboot.
device: /dev/serial/by-id/usb-PARADOX_PARADOX_APR-PRT3_a4008936-if00-port0

# Optional: override path to the paraevo binary.
# binary_path: /opt/paraevo/paraevo

# Optional: write all daemon output to a log file.
log_file: /var/log/paraevo.log

# Optional: run the daemon in the background.
daemon: false

# Optional: cap log file size in MB (default 10).
log_max_size_mb: 10

# Optional: full logging (INFO/VERB/DBG). Default false = only ERROR logs.
log: false

# Optional: legacy alias for "log".
verbose: false

# Optional: how often (in seconds) to poll area status when there is no panel activity.
status_period: 60

# MQTT broker connection settings.
mqtt:
  server: 192.168.1.100   # IP or hostname of your MQTT broker
  port: 1883               # default MQTT port
  login: mqtt_user         # MQTT username (omit if broker has no auth)
  password: mqtt_password  # MQTT password (omit if broker has no auth)
  retain: true             # retain last known state so HA survives restarts

# Panel user code. Only strictly required for the Disarm command.
user_code: "1234"

# Areas (partitions) and their zones.
# Each area becomes a separate alarm_control_panel entity in Home Assistant.
# Zone names appear as labels in HA MQTT auto-discovery.
areas:
  - num: 1                  # Area / partition 1
    zones:
      - num: 1
        name: "HallwayPIR"
        device_class: "motion"
      - num: 2
        name: "LivingRoomPIR"
      - num: 3
        name: "BedroomPIR"
      - num: 4
        name: "KitchenDoor"
      - num: 5
        name: "GarageDoor"
      - num: 6
        name: "BasementWindow"

  - num: 2                  # Area / partition 2 (e.g. garage / outbuilding)
    zones:
      - num: 10
        name: "PerimeterFence"
        entity_category: "diagnostic"
        icon: "mdi:shield-home"
      - num: 11
        name: "OutdoorMotion"
```

The generated command for the above example would be equivalent to:
```
/opt/paraevo/paraevo -d /dev/serial/by-id/... \
  --mqtt_server=192.168.1.100 --mqtt_port=1883 \
  --mqtt_login=mqtt_user --mqtt_password=mqtt_password -r \
  -u 1234 \
  -a 1 --zone_name=1:HallwayPIR --zone_device_class=1:motion -z 1,2,3,4,5,6 ... \
  -a 2 --zone_name=10:PerimeterFence --zone_entity_category=10:diagnostic --zone_icon=10:mdi:shield-home -z 10,11 ... \
  -S 60
```

# Configuration of PRT3
Module should be configured to 57600 baud and ASCII mode.

**NOTE**: one must configure the device using the keypad. _It simply does not work_ by configuring via BabyWare or WinLoad (a known issue).

# MQTT Interface

MQTT interface I have currently covered include area support, zone state report and utility key "presses".

The topic string begins with `darauble/paraevo` by default, however _this is changeable_ via `-t`, you can set it like that:
`./paraevo -t my/cool/house/alarm/panel <...>`

## Area Topics
Running area 1 will report its status to the topic `darauble/paraevo/area/1`. Reported statuses correspond to https://www.home-assistant.io/integrations/alarm_control_panel.mqtt/ and are:
* armed_away
* armed_home
* disarmed
* triggered

There is also a topic `darauble/paraevo/area/1/state`, which reports full JSON output from PRT3 module with its corresponding values:
`darauble/paraevo/area/1/state {"num": 1,"name": "My House","status": "D","memory": "O","trouble": "O","ready": "O","programming": "O","alarm": "O","strobe": "O"}`

For the meaning of these value please consult the **PRT3 ASCII Programming Guide** (just google it).

The listening topic is set to `darauble/paraevo/area/1/set`. The default values from Home Assistant are accepted:
* ARM_AWAY - using Area Quick Arm
* ARM_HOME - using Area Quick ARM
* DISARM - user code must be provided via `-u` switch or YAML entry

The entry in `configuration.yaml` of Home Assistant is simple as following:
```
alarm_control_panel:
  - platform: mqtt
    state_topic: "darauble/paraevo/area/1"
    command_topic: "darauble/paraevo/area/1/set"

```

## Home Assistant MQTT Auto-discovery
Zone auto-discovery messages are published to:
`homeassistant/binary_sensor/paraevo_Z<zone_number>/config`

Discovered zone entities use `device_class: motion` by default.  
You can override `device_class` per zone, and optionally set `entity_category` and `icon` in YAML.

To add auto-discovered sensors in Home Assistant:
1. In Home Assistant, add/configure the MQTT integration (`Settings -> Devices & Services -> Add Integration -> MQTT`).
2. In `paraevo.yaml`, set `mqtt.retain: true` (recommended for stable discovery/state after restarts).
3. Start/restart ParadoxEvoMQTT.
4. Home Assistant will automatically create `binary_sensor` entities for all configured zones from your `areas[].zones` configuration.

No manual `binary_sensor` YAML is required for discovered zones.

## Zone Topics
Each zone has a topic `darauble/paraevo/area/1/zone/1`. If sensor is off, the reported payload is `OFF`. It is set to `ON` if zone:
* is open
* is tampered
* is on fire loop trouble

It is oversimplified, I know, but I wanted to keep this topic as a *binary sensor* for Home Assistant.

Also each zone has a topic for alarm reporting: `darauble/paraevo/area/1/zone/1/alarm`. Again, it is binary: `ON`/`OFF`.

And if that is not enough, there's a JSON topic `darauble/paraevo/area/1/zone/1/state`. It again contains the states from PRT3 directly:
`{"num": 1,"area": 1,"name": "Living room","status": "C","alarm": "O","fire": "O","supervision": "O","battery": "O","bypassed": "O"}`

A binary sensor showing the zone status can be configured as follows:
```
binary_sensor:
  - platform: mqtt
    name: "Living Room"
    state_topic: "darauble/paraevo/area/1/zone/1/state"
    payload_on: "ON"
    payload_off: "OFF"
```

**NOTE**: _bypassed_ flag is not yet supported in v0.3! TBD.

## Utility Keys
Currently there's no way in PRT3 to turn on or off physical EVO's PGMs. That's a bit unfair. However, if remote controls are used with the panel, it is very likely that PGM actions are (or may be) tied to Utility Key presses (additional keys on the remote, that can be assigned any Utility Key number).

The easiest way to make physical PGMs react is to program them to react to Utility Key press and issue this command to the PRT3.

The topic is as follows: `darauble/paraevo/utilitykey`. As a payload, send the number of desired key (1 to 251 on EVO).

So, let's say, that Utility Key 1 issues a command to PGM, which in turn opens or closes the garage gate. The zone 30 reports if the gate (a magnetic sensor on it) is open or closed. This could be translated to MQTT switch configuration in Home Assistant as follows:

```
switch
  - platform: mqtt
    name: "Garage gate open/close"
    state_topic: "darauble/paraevo/area/1/zone/30"
    state_on: "on"
    state_off: "off"
    command_topic: "darauble/paraevo/utilitykey"
    payload_on: "1"
    payload_off: "1"
```

## LWT Topic
To track if Paradox EVO daemon is running, the following topic is published with either "offline" or "online" payloads: `darauble/paraevo/daemon`.

To add a binary sensor to the Home Assistant configuration for alert automation:
```
binary_sensor:
  - platform: mqtt
    name: "ParaEVO"
    state_topic: "darauble/paraevo/daemon"
    payload_on: "online"
    payload_off: "offline"
```
