# Multi-Proxy Configuration Generator Modification Plan

## Objective

Modify `gen_conf.py` and the configuration format so that Spire supports
**multiple RTU proxies**, with each proxy responsible for a specified
subset of RTUs.

The current configuration uses a single proxy:

``` json
"proxy": {
  "host": "host7",
  "ip": "192.168.101.107"
}
```

The new configuration will use a proxy list and explicitly assign RTUs
to each proxy:

``` json
"proxies": [
  {
    "host": "host7",
    "ip": "192.168.101.107",
    "rtus": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
  },
  {
    "host": "host8",
    "ip": "192.168.101.108",
    "rtus": [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
  }
]
```

The resulting topology will contain one Spines node for each proxy.

For four control centers, two proxies, and one HMI, the external
topology will contain seven nodes:

``` text
1  Control Center 1
2  Control Center 2
3  Control Center 3
4  Control Center 4
5  Proxy 1
6  Proxy 2
7  HMI
```

------------------------------------------------------------------------

## 1. Parse the Proxy List

After parsing `sites`, read the new `proxies` array:

``` python
proxies = cfg.get("proxies", [])
num_proxies = len(proxies)
proxy_ips = [proxy["ip"] for proxy in proxies]
```

This replaces assumptions throughout the generator that `cfg["proxy"]`
represents a single proxy.

It is also advisable to validate that at least one proxy exists:

``` python
if not proxies:
    print("Error: At least one proxy must be configured.")
    sys.exit(1)
```

------------------------------------------------------------------------

## 2. Validate RTU-to-Proxy Assignments

Because the selected architecture assigns different RTUs to different
proxies, validate the `rtus` lists before generating files.

At minimum, check:

-   Every proxy has an `ip`.
-   Every proxy has an `rtus` list.
-   An RTU ID is not assigned to more than one proxy.
-   Every expected RTU is assigned to a proxy.
-   RTU IDs are valid.

For the current 20-RTU template:

``` python
expected_rtus = set(range(20))
assigned_rtus = []

for proxy in proxies:
    assigned_rtus.extend(proxy.get("rtus", []))

assigned_set = set(assigned_rtus)

if len(assigned_rtus) != len(assigned_set):
    print("Error: An RTU is assigned to more than one proxy.")
    sys.exit(1)

if assigned_set != expected_rtus:
    missing = expected_rtus - assigned_set
    extra = assigned_set - expected_rtus
    print(f"Error: Invalid RTU assignment. Missing={missing}, Extra={extra}")
    sys.exit(1)
```

This prevents silently generating an inconsistent deployment.

------------------------------------------------------------------------

## 3. Modify `spines_ext.conf` Generation

The current generator assumes:

``` text
Control Centers + one Proxy + one HMI
```

Change it to:

``` text
Control Centers + all Proxies + one HMI
```

Generate the host list as follows:

``` python
hosts_ext = ["Hosts {\n"]

# Control Centers
for i, site in enumerate(cc_sites):
    hosts_ext.append(
        f"    {i + 1} {site['hosts'][0]['ip']}\n"
    )

# Proxies
for i, proxy in enumerate(proxies):
    hosts_ext.append(
        f"    {num_cc + i + 1} {proxy['ip']}\n"
    )

# HMI
hmi_ext_id = num_cc + num_proxies + 1
hosts_ext.append(
    f"    {hmi_ext_id} {cfg['hmi']['ip']}\n"
)

hosts_ext.append("}\n\nEdges {\n")
```

For the proposed configuration, this produces:

``` text
Hosts {
    1 192.168.101.101
    2 192.168.101.102
    3 192.168.101.103
    4 192.168.101.104
    5 192.168.101.107
    6 192.168.101.108
    7 <HMI-IP>
}
```

Update the external node count from:

``` python
total_ext_nodes = num_cc + 2
```

to:

``` python
total_ext_nodes = num_cc + num_proxies + 1
```

The final `+1` represents the HMI.

------------------------------------------------------------------------

## 4. Preserve or Reconsider External Edge Policy

The current edge-generation logic is:

``` python
for i in range(1, total_ext_nodes + 1):
    for j in range(i + 1, total_ext_nodes + 1):
        if i <= num_cc:
            hosts_ext.append(f"    {i}  {j}    100\n")
```

This can remain unchanged if the desired policy is:

-   Control centers connect to other control centers.
-   Control centers connect to every proxy.
-   Control centers connect to the HMI.
-   Proxies do not directly connect to one another.
-   Proxies do not directly connect to the HMI.

With four control centers, two proxies, and one HMI, this generates
edges such as:

``` text
1 2
1 3
1 4
1 5
1 6
1 7
...
4 5
4 6
4 7
```

but not:

``` text
5 6
5 7
6 7
```

If proxy-to-proxy or proxy-to-HMI Spines links are required later, this
edge-generation policy must be changed separately.

------------------------------------------------------------------------

## 5. Modify `spines_ctrl.conf`

Replace the single-proxy construction:

``` python
ctrl_ips = (
    [s["hosts"][0]["ip"] for s in sites]
    + [cfg["proxy"]["ip"], cfg["hmi"]["ip"]]
)
```

with:

``` python
ctrl_ips = (
    [s["hosts"][0]["ip"] for s in sites]
    + proxy_ips
    + [cfg["hmi"]["ip"]]
)
```

The existing code can continue using:

``` python
total_ctrl_nodes = len(ctrl_ips)
```

and therefore automatically accommodates any number of proxies.

The current control-topology edge loop creates a complete graph, so no
further loop changes are required unless the desired topology changes.

------------------------------------------------------------------------

## 6. Modify `CC_CONNECTORS`

Replace:

``` python
connector_ips = [cfg["proxy"]["ip"], cfg["hmi"]["ip"]]
```

with:

``` python
connector_ips = proxy_ips + [cfg["hmi"]["ip"]]
```

Then:

``` python
replace_array_define(
    scada_def,
    "CC_CONNECTORS",
    connector_ips
)
```

will generate an array containing every proxy followed by the HMI.

For example:

``` c
#define CC_CONNECTORS {"192.168.101.107", \
                       "192.168.101.108", \
                       "192.168.101.109"}
```

### C-side follow-up

Search the Spire C source for every use of `CC_CONNECTORS`.

Check for assumptions such as:

``` c
for (i = 0; i < 2; i++)
```

or:

``` c
char *connectors[2];
```

If the number of connectors is hard-coded, introduce an appropriate
generated constant such as:

``` c
#define NUM_PROXIES 2
```

and/or:

``` c
#define NUM_CC_CONNECTORS 3
```

Then update the C code to use those constants.

If `NUM_PROXIES` is added to the base `scada_def.h`, the generator can
populate it:

``` python
replace_defines(scada_def, {
    "NUM_SM": total_rep,
    "NUM_F": cfg["num_f"],
    "NUM_K": cfg["num_k"],
    "NUM_CC": num_cc,
    "NUM_CC_REPLICA": cc_rep,
    "NUM_SITES": num_sites,
    "NUM_PROXIES": num_proxies
})
```

------------------------------------------------------------------------

## 7. Remove Remaining Single-Proxy References

The existing generator contains expressions such as:

``` python
cfg["proxy"]["ip"]
```

These must no longer be used after changing the JSON schema.

Search for them with:

``` bash
grep -n 'cfg\["proxy"\]' scripts/gen_conf.py
```

The target after migration is zero occurrences.

Also inspect:

``` bash
grep -n "proxy_ip" scripts/gen_conf.py
```

For every occurrence, determine whether the code needs:

-   one particular proxy IP,
-   all proxy IPs, or
-   a loop that generates one artifact/service per proxy.

------------------------------------------------------------------------

## 8. Fix Docker Network Fallback

The current fallback uses the single proxy:

``` python
first_ip = (
    sites[0]["hosts"][0]["ip"]
    if sites and sites[0]["hosts"]
    else cfg["proxy"]["ip"]
)
```

Change it to:

``` python
first_ip = (
    sites[0]["hosts"][0]["ip"]
    if sites and sites[0]["hosts"]
    else proxies[0]["ip"]
)
```

The normal deployment has sites, so this is primarily required to
eliminate the obsolete `cfg["proxy"]` assumption.

------------------------------------------------------------------------

## 9. Generate One Proxy/PLC Service per Proxy

The current Docker Compose generator creates one `plc-client` at one
`proxy_ip`.

For the multi-proxy architecture, generate one service per proxy.

For example:

``` python
for i, proxy in enumerate(proxies, start=1):
    proxy_ip = proxy["ip"]

    dc_services.append(
        f"  plc-client{i}:\n"
        f"    image: spire-img\n"
        f"    pull_policy: never\n"
        f"    profiles:\n"
        f"      - full\n"
        f"    container_name: spire-plc{i}\n"
        f"    networks:\n"
        f"      spire-net:\n"
        f"        ipv4_address: {proxy_ip}\n"
        f"    cap_add:\n"
        f"      - NET_ADMIN\n"
        f"    command: python docker/run_client.py --type=plc --proxy-id={i}\n\n"
    )
```

This would produce services conceptually like:

``` yaml
plc-client1:
  container_name: spire-plc1
  networks:
    spire-net:
      ipv4_address: 192.168.101.107

plc-client2:
  container_name: spire-plc2
  networks:
    spire-net:
      ipv4_address: 192.168.101.108
```

### Required follow-up

The example adds `--proxy-id`, but `run_client.py` must be modified to
accept and use this argument before the generated command can be used.

The exact runtime interface should be finalized after inspecting
`docker/run_client.py`.

------------------------------------------------------------------------

## 10. Rework RTU Configuration Generation for Option B

This is the central change for the selected architecture.

Each RTU must use the IP of the proxy to which it is assigned.

Instead of:

``` python
def get_rtu_template(proxy_ip: str) -> dict:
```

refactor the function so that it can receive an RTU-to-proxy mapping.

### Build the mapping

From:

``` json
"proxies": [
  {
    "ip": "192.168.101.107",
    "rtus": [0, 1, 2]
  },
  {
    "ip": "192.168.101.108",
    "rtus": [3, 4, 5]
  }
]
```

construct:

``` python
rtu_proxy_map = {}

for proxy in proxies:
    for rtu_id in proxy["rtus"]:
        rtu_proxy_map[rtu_id] = proxy["ip"]
```

The result is conceptually:

``` python
{
    0: "192.168.101.107",
    1: "192.168.101.107",
    2: "192.168.101.107",
    3: "192.168.101.108",
    4: "192.168.101.108",
    5: "192.168.101.108"
}
```

### Change `get_rtu_template()`

Change:

``` python
def get_rtu_template(proxy_ip: str) -> dict:
```

to:

``` python
def get_rtu_template(rtu_proxy_map: dict[int, str]) -> dict:
```

Then replace each hard-coded:

``` python
"IP": proxy_ip
```

with the appropriate RTU lookup.

For RTU 0:

``` python
"IP": rtu_proxy_map[0]
```

For RTU 1:

``` python
"IP": rtu_proxy_map[1]
```

and so on.

A cleaner implementation is to first build the existing RTU template and
then assign IPs programmatically:

``` python
def get_rtu_template(rtu_proxy_map: dict[int, str]) -> dict:
    rtu_config = {
        # existing RTU configuration
    }

    for location in rtu_config["locations"]:
        for rtu in location["rtus"]:
            rtu_id = rtu["ID"]
            rtu["IP"] = rtu_proxy_map[rtu_id]

    return rtu_config
```

This is preferable to manually writing `rtu_proxy_map[0]`,
`rtu_proxy_map[1]`, etc. twenty times.

------------------------------------------------------------------------

## 11. Generate the Final RTU `config.json`

Replace:

``` python
rtu_data = get_rtu_template(proxy_ip)
```

with:

``` python
rtu_proxy_map = {}

for proxy in proxies:
    for rtu_id in proxy["rtus"]:
        rtu_proxy_map[rtu_id] = proxy["ip"]

rtu_data = get_rtu_template(rtu_proxy_map)
```

Then retain:

``` python
with open(rtu_json_path, "w") as f:
    json.dump(rtu_data, f, indent=4)
```

The generated `config.json` will therefore contain different proxy IPs
for different RTUs.

For example:

``` json
{
  "ID": 0,
  "rtus": [
    {
      "ID": 0,
      "IP": "192.168.101.107"
    }
  ]
}
```

while RTU 10 can contain:

``` json
{
  "ID": 10,
  "rtus": [
    {
      "ID": 10,
      "IP": "192.168.101.108"
    }
  ]
}
```

------------------------------------------------------------------------

## 12. Determine Whether One Shared RTU Config or Per-Proxy Configs Are Needed

With Option B, there are two possible runtime representations:

### Shared configuration

Generate one `config.json` containing all 20 RTUs, where each RTU has
its assigned proxy IP.

This is the smallest change to the existing generator.

### Per-proxy configuration

Generate:

``` text
config_proxy1.json
config_proxy2.json
```

where each file contains only the RTUs assigned to that proxy.

This may be necessary if each proxy process loads `config.json` and
expects every listed RTU to be local to itself.

The correct choice depends on how the PLC/proxy runtime consumes
`config.json`.

**Before finalizing runtime behavior, inspect `docker/run_client.py` and
the code that reads the generated RTU `config.json`.**

If each proxy independently reads the same complete configuration and
connects only according to the IP fields, a shared configuration may
work.

If each proxy interprets every RTU in the file as one it must manage,
generate a separate RTU configuration for each proxy instead.

------------------------------------------------------------------------

## 13. Review Benchmark Client Behavior

The current generator assigns the benchmark client the single proxy IP.

With multiple proxies, determine whether the benchmark client:

1.  represents a proxy,
2.  should run once per proxy, or
3.  is a separate logical endpoint that needs its own IP.

Do not simply reuse `proxies[0]["ip"]` unless the benchmark architecture
explicitly requires that.

If benchmark mode should test each proxy independently, generate one
benchmark service per proxy.

------------------------------------------------------------------------

## 14. Expected External Topology

For:

``` text
CC1    192.168.101.101
CC2    192.168.101.102
CC3    192.168.101.103
CC4    192.168.101.104
Proxy1 192.168.101.107
Proxy2 192.168.101.108
HMI    <HMI-IP>
```

the generated external Spines host list should be:

``` text
Hosts {
    1 192.168.101.101
    2 192.168.101.102
    3 192.168.101.103
    4 192.168.101.104
    5 192.168.101.107
    6 192.168.101.108
    7 <HMI-IP>
}
```

With the existing CC-centered edge policy, expected edges include:

``` text
1 2 100
1 3 100
1 4 100
1 5 100
1 6 100
1 7 100
2 3 100
2 4 100
2 5 100
2 6 100
2 7 100
3 4 100
3 5 100
3 6 100
3 7 100
4 5 100
4 6 100
4 7 100
```

------------------------------------------------------------------------

## 15. Recommended Implementation Order

Implement and test the changes in this order:

1.  Change the input JSON from `proxy` to `proxies`.
2.  Add an `rtus` list to every proxy.
3.  Parse `proxies`, `proxy_ips`, and `num_proxies`.
4.  Validate RTU assignments.
5.  Update `spines_ext.conf` host generation.
6.  Update `total_ext_nodes`.
7.  Verify the external Spines edge policy.
8.  Update `spines_ctrl.conf`.
9.  Update `CC_CONNECTORS`.
10. Add `NUM_PROXIES` / `NUM_CC_CONNECTORS` if required by the C
    implementation.
11. Remove every remaining `cfg["proxy"]` reference.
12. Build `rtu_proxy_map`.
13. Refactor `get_rtu_template()` to assign each RTU to its configured
    proxy.
14. Determine whether runtime requires one shared RTU config or one
    config per proxy.
15. Generate one Docker proxy/PLC service per proxy.
16. Modify `run_client.py` to distinguish proxy instances if necessary.
17. Resolve benchmark-client behavior.
18. Regenerate the configuration.
19. Inspect all generated files before building the image.
20. Build and test the multi-proxy deployment.

------------------------------------------------------------------------

## 16. Validation Checklist

After running `gen_conf.py`, verify the following.

### `spines_ext.conf`

-   Contains four CC nodes.
-   Contains both proxy nodes.
-   Contains the HMI node.
-   Node IDs are unique.
-   Total external nodes = 7.
-   Both proxy IPs have the expected edges.

### `spines_ctrl.conf`

-   Contains all sites.
-   Contains both proxies.
-   Contains HMI.
-   All generated node IDs are unique.

### `scada_def.h`

-   `CC_CONNECTORS` contains both proxy IPs and the HMI IP.
-   Any connector-count constants match the generated array.
-   No C code assumes exactly two connector entries.

### RTU `config.json`

-   Every RTU appears exactly once.
-   RTUs assigned to Proxy 1 contain `192.168.101.107`.
-   RTUs assigned to Proxy 2 contain `192.168.101.108`.
-   No RTU references an obsolete proxy IP.

### `docker-compose.yml`

-   Both proxy services exist.
-   Proxy container names are unique.
-   Proxy IP addresses are unique.
-   HMI IP does not conflict with a proxy.
-   Replica IPs do not conflict with proxy IPs.
-   Commands identify the correct proxy instance/configuration.

### Source tree

Run:

``` bash
grep -R 'cfg\["proxy"\]' scripts/
```

and verify that the old single-proxy JSON access has been eliminated
from the generator.

Also search the C/runtime code for singleton assumptions:

``` bash
grep -R "CC_CONNECTORS" .
grep -R "NUM_CC_CONNECTORS" .
grep -R "NUM_PROXIES" .
```

------------------------------------------------------------------------

## Final Target Architecture

The configuration generator should treat proxies as a first-class list
rather than a singleton:

``` text
                         Configuration JSON
                                |
              +-----------------+------------------+
              |                                    |
              v                                    v
           sites[]                             proxies[]
              |                                    |
              |                         +----------+----------+
              |                         |                     |
              |                      Proxy 1               Proxy 2
              |                     RTUs 0-9              RTUs 10-19
              |                         |                     |
              +-------------------------+---------------------+
                                        |
                                        v
                                gen_conf.py
                                        |
          +-----------------------------+-----------------------------+
          |                             |                             |
          v                             v                             v
    Spines topology               C definitions                Docker/runtime
  spines_ext.conf                 scada_def.h                 docker-compose.yml
  spines_ctrl.conf               CC_CONNECTORS               proxy instances
          |                             |                             |
          +-----------------------------+-----------------------------+
                                        |
                                        v
                                RTU configuration
                              RTU -> Proxy mapping
```

The key design invariant is:

> **Every RTU is assigned to exactly one proxy, and the same proxy
> assignment must be reflected consistently in the generated Spines
> topology, C configuration, RTU configuration, and Docker runtime.**

The generator should validate this invariant before producing deployment
files.


# `run_client.py` Multi-Proxy Modification Plan

## Objective

Modify `run_client.py` so Spire can run multiple PLC/RTU proxy nodes,
with each proxy owning only the RTUs assigned to it by the master JSON
configuration.

Example:

``` json
"proxies": [
  {
    "host": "host7",
    "ip": "192.168.101.107",
    "rtus": [0,1,2,3,4,5,6,7,8,9]
  },
  {
    "host": "host8",
    "ip": "192.168.101.108",
    "rtus": [10,11,12,13,14,15,16,17,18,19]
  }
]
```

`gen_conf.py` remains the source of truth. It passes each generated
proxy container its node ID, IP address, and RTU list.

## 1. Remove hard-coded node IDs

The current code assumes PLC/benchmark ID 7 and HMI ID 8. Adding proxy
nodes invalidates these assumptions.

Add:

``` python
parser.add_argument(
    '--id',
    type=int,
    help='Spines/control-network node ID'
)
```

Use:

``` python
i = args.id
```

where the node ID is required.

For four CCs, two proxies, and one HMI, the generated topology is
expected to be:

``` text
1 CC1
2 CC2
3 CC3
4 CC4
5 Proxy1
6 Proxy2
7 HMI
```

`gen_conf.py`, rather than `run_client.py`, should calculate these IDs.

## 2. Add an RTU assignment argument

Add:

``` python
parser.add_argument(
    '--rtus',
    type=str,
    help='Comma-separated RTU IDs assigned to this proxy'
)
```

Parse it:

``` python
if args.rtus:
    rtu_ids = [int(x) for x in args.rtus.split(",")]
else:
    rtu_ids = []
```

For PLC mode, reject an empty assignment:

``` python
if args.type == "plc" and not rtu_ids:
    print("Error: PLC client requires at least one RTU assignment.")
    sys.exit(1)
```

Also validate that RTU IDs are in the supported range.

## 3. Pass proxy IPs explicitly

Continue supporting `--ip`, but generated Docker services should always
supply it explicitly rather than relying on:

``` python
ip = f"192.168.101.{100 + i}"
```

Example:

``` text
--ip=192.168.101.107
```

This avoids coupling node IDs to IP-address numbering.

## 4. Refactor PLC startup

Create:

``` python
def start_plc(rtu_id):
    ...
```

Based on the current script, the apparent mapping is:

``` text
RTU 0-9   -> JHU PLCs
RTU 10    -> PNNL PLC
RTU 11-13 -> EMS PLCs 0-2
RTU 14-16 -> ems_hydro / ems_solar / ems_wind
RTU 17-19 -> IEC 61850; runtime handling still needs verification
```

Suggested implementation for RTUs 0-16:

``` python
def start_plc(rtu_id):
    if 0 <= rtu_id <= 9:
        cmd = (
            f"cd {base_dir}/plcs/jhu{rtu_id} && "
            f"./openplc -m {503 + rtu_id} -d {20001 + rtu_id}"
        )
        run_cmd(cmd, f"plc_jhu_{rtu_id}",
                f"{log_dir}/out_plc_jhu_{rtu_id}.txt")

    elif rtu_id == 10:
        cmd = f"cd {base_dir}/plcs/pnnl_plc && ./openplc -m 502 -d 20000"
        run_cmd(cmd, "plc_pnnl", f"{log_dir}/out_plc_pnnl.txt")

    elif 11 <= rtu_id <= 13:
        ems_id = rtu_id - 11
        cmd = (
            f"cd {base_dir}/plcs/ems{ems_id} && "
            f"./openplc -m {513 + ems_id} -d {20011 + ems_id}"
        )
        run_cmd(cmd, f"plc_ems_{ems_id}",
                f"{log_dir}/out_plc_ems_{ems_id}.txt")

    elif 14 <= rtu_id <= 16:
        names = ["ems_hydro", "ems_solar", "ems_wind"]
        ems_id = rtu_id - 14
        name = names[ems_id]
        cmd = (
            f"cd {base_dir}/plcs/{name} && "
            f"./openplc -m {516 + ems_id} -d {20014 + ems_id}"
        )
        run_cmd(cmd, f"plc_{name}",
                f"{log_dir}/out_plc_{name}.txt")
```

Do not invent startup behavior for RTUs 17-19 until their IEC 61850
runtime path is confirmed.

## 5. Start only assigned PLCs

Replace the current unconditional PLC loops with:

``` python
for rtu_id in rtu_ids:
    start_plc(rtu_id)
```

Thus proxy node 1 starts only the PLCs for RTUs 0-9, while proxy node 2
starts only those assigned to it.

## 6. Start only assigned `./proxy` processes

Replace:

``` python
for proxy_id in range(17):
    proxy_cmd = f"cd {base_dir}/proxy && ./proxy {proxy_id} {ip}:8120 1"
```

with:

``` python
for rtu_id in rtu_ids:
    if 0 <= rtu_id <= 16:
        proxy_cmd = (
            f"cd {base_dir}/proxy && "
            f"./proxy {rtu_id} {ip}:8120 1"
        )
        run_cmd(
            proxy_cmd,
            f"proxy_{rtu_id}",
            f"{log_dir}/out_proxy_{rtu_id}.txt"
        )
```

Expected behavior:

``` text
Proxy node 1 (.107):
    ./proxy 0 .107:8120 1
    ...
    ./proxy 9 .107:8120 1

Proxy node 2 (.108):
    ./proxy 10 .108:8120 1
    ...
    ./proxy 16 .108:8120 1
```

RTUs 17-19 remain excluded from `./proxy` until IEC 61850 handling is
confirmed.

## 7. Keep one external Spines daemon per proxy node

The existing command can remain:

``` python
spines_ext_cmd = (
    f"cd {base_dir}/spines/daemon && "
    f"./spines -p 8120 -c spines_ext.conf -I {ip}"
)
```

Each proxy container has a different IP, so both can use port 8120.

## 8. Revisit `num_apps`

The current PLC branch hard-codes:

``` python
num_apps = 10
```

Do not rely on this for arbitrary assignments.

A possible replacement is:

``` python
num_apps = len(rtu_ids)
```

but use it only after confirming that Config Agent defines `num_apps` as
the number of RTU/proxy applications managed by the node.

The proposed 10/10 split happens to preserve the value 10 for both
proxies, but future configurations may not.

## 9. Review IPC paths

The current PLC path is:

``` python
ipc_path = "/tmp/rtu_ipc_main"
```

If each proxy runs in a separate Docker container and this IPC path is
container-local, the same path can be used in both containers.

If the IPC endpoint is shared or mounted across containers, make it
unique:

``` python
ipc_path = f"/tmp/rtu_ipc_main_{i}"
```

Verify this before changing it.

## 10. Preserve HMI startup but remove its hard-coded ID

The existing HMI process loop can remain.

However, remove:

``` python
i = 8
```

and pass the generated HMI node ID from `gen_conf.py`:

``` text
python docker/run_client.py --type=hmi --id=7 --ip=<HMI-IP>
```

for the four-CC/two-proxy example.

## 11. Review benchmark mode separately

Benchmark mode currently shares the old singleton assumptions:

``` python
i = 7
num_apps = 10
ipc_path = "/tmp/bm_ipc_main"
```

Determine whether benchmark mode should run against one selected proxy,
run once per proxy, or use its own address. Do not silently bind it to
`proxies[0]`.

## 12. Target argument parser

The modified parser should conceptually include:

``` python
def get_args(argv):
    parser = argparse.ArgumentParser(description="Run a Spire client")

    parser.add_argument('--id', type=int,
                        help='Spines/control-network node ID')

    parser.add_argument('-ip', type=str,
                        help='Client IP')

    parser.add_argument('--rtus', type=str,
                        help='Comma-separated RTU IDs assigned to this proxy')

    parser.add_argument(
        '--type', '-t',
        choices=['benchmark', 'plc', 'hmi'],
        default='benchmark'
    )

    parser.add_argument(
        '--reconf', '-r',
        action='store_true'
    )

    return parser.parse_args(argv)
```

## 13. Commands `gen_conf.py` should generate

Proxy 1:

``` text
python docker/run_client.py \
    --type=plc \
    --id=5 \
    --ip=192.168.101.107 \
    --rtus=0,1,2,3,4,5,6,7,8,9
```

Proxy 2:

``` text
python docker/run_client.py \
    --type=plc \
    --id=6 \
    --ip=192.168.101.108 \
    --rtus=10,11,12,13,14,15,16,17,18,19
```

HMI should likewise receive its generated ID and IP.

## 14. Recommended code structure

Refactor toward:

``` python
def get_args(argv):
    ...

def run_cmd(cmd, tag, log_file):
    ...

def start_plc(rtu_id):
    ...

def start_proxy(rtu_id, spines_ip):
    ...

def start_hmis(ip):
    ...

def main(argv):
    ...
```

Then PLC startup becomes approximately:

``` python
if args.type == "plc":
    for rtu_id in rtu_ids:
        start_plc(rtu_id)

    for rtu_id in rtu_ids:
        if 0 <= rtu_id <= 16:
            start_proxy(rtu_id, ip)
```

## 15. Target runtime flow

``` text
Parse arguments
      |
      v
Receive node ID, proxy IP, assigned RTUs
      |
      v
Start this node's spines_ext daemon
      |
      v
For each assigned RTU:
      +--> start corresponding PLC
      +--> if RTU 0-16, start ./proxy
      +--> if RTU 17-19, use verified IEC 61850 path
      |
      v
If --reconf:
      +--> start spines_ctrl
      +--> start config_agent using generated node ID
      |
      v
Wait for external Spines process
```

## 16. Validation checklist

### Proxy node 1

With:

``` text
--id=5
--ip=192.168.101.107
--rtus=0,1,2,3,4,5,6,7,8,9
```

verify:

-   external Spines binds to `.107`;
-   only JHU PLCs 0-9 start;
-   only `./proxy` 0-9 start;
-   no PNNL/EMS PLC starts;
-   no proxy process 10-16 starts.

### Proxy node 2

With:

``` text
--id=6
--ip=192.168.101.108
--rtus=10,11,12,13,14,15,16,17,18,19
```

verify:

-   external Spines binds to `.108`;
-   PNNL starts;
-   EMS PLCs associated with 11-16 start;
-   `./proxy` 10-16 start;
-   JHU PLCs do not start;
-   RTUs 17-19 are not accidentally passed to `./proxy`.

### Reconfiguration

Verify:

-   each proxy uses its generated node ID;
-   each Config Agent receives the correct IP;
-   `num_apps` semantics are confirmed;
-   IPC paths do not conflict.

### HMI

Verify:

-   no hard-coded `i = 8` remains;
-   HMI receives its generated topology ID;
-   all existing HMI processes still start.

## 17. Implementation order

1.  Add `--id`.
2.  Add `--rtus`.
3.  Parse and validate the RTU list.
4.  Remove hard-coded PLC node ID `i = 7`.
5.  Remove hard-coded HMI node ID `i = 8`.
6.  Extract PLC startup into `start_plc(rtu_id)`.
7.  Start only PLCs belonging to assigned RTUs.
8.  Replace `range(17)` with RTU-assignment-driven proxy startup.
9.  Continue limiting `./proxy` to RTUs 0-16 until IEC 61850 behavior is
    verified.
10. Verify `num_apps` semantics.
11. Verify IPC behavior.
12. Update `gen_conf.py` to generate one PLC service per proxy.
13. Pass `--id`, `--ip`, and `--rtus` from Docker Compose.
14. Review benchmark behavior separately.
15. Test each proxy container independently.
16. Test the complete multi-proxy deployment.

## Final design principle

`run_client.py` should not decide RTU ownership. Ownership belongs in
the deployment JSON:

``` text
configuration JSON
       |
       v
   gen_conf.py
       |
       v
docker-compose.yml
       |
       +--> Proxy 1: --id=5 --ip=.107 --rtus=0,...,9
       |
       +--> Proxy 2: --id=6 --ip=.108 --rtus=10,...,19
                          |
                          v
                    run_client.py
```

`run_client.py` should execute the assignment it receives. This keeps
RTU ownership in one source of truth and allows the runtime to scale to
additional proxy nodes without adding hard-coded partitions.
