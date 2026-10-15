"""
Modifications are currently ignoring benchmark and controls spines.
"""
#!/usr/bin/env python3
import ipaddress
import json
import re
import shutil
import sys
from pathlib import Path

def replace_defines(file_path: Path, replacements: dict):
    """Replaces single-line C-style #define statements in target header files."""
    content = file_path.read_text()
    for key, val in replacements.items():
        pattern = rf"(#define\s+{key}\s+)[^\r\n]+"
        content = re.sub(pattern, rf"\g<1>{val}", content)
    file_path.write_text(content)

def replace_array_define(file_path: Path, macro_name: str, ips: list[str]):
    """Replaces multi-line C macro arrays like #define MACRO {"ip1", \ ... }."""
    content = file_path.read_text()
    formatted_array = f"#define {macro_name} {{" + (", \\\n" + " " * 31).join(f'"{ip}"' for ip in ips) + "}"
    pattern = rf"#define\s+{macro_name}\s*\{{[^}}]*\}}"
    content = re.sub(pattern, formatted_array, content)
    file_path.write_text(content)

def get_rtu_template(rtu_proxy_map: dict[int, str]) -> dict:
    """Returns the base RTU/Location configuration dictionary with updated proxy IPs."""
    rtu_config = {
        "num_rtus": 20,
        "num_locations": 20,
        "locations": [
            {"ID": 0, "protocols": ["dnp3"], "rtus": [{"ID": 0, "scenario": "JHU", "protocol": "dnp3", "PORT": 20001, "IP": rtu_proxy_map[0]}]},
            {"ID": 1, "protocols": ["dnp3"], "rtus": [{"ID": 1, "scenario": "JHU", "protocol": "dnp3", "PORT": 20002, "IP": rtu_proxy_map[1]}]},
            {"ID": 2, "protocols": ["dnp3"], "rtus": [{"ID": 2, "scenario": "JHU", "protocol": "dnp3", "PORT": 20003, "IP": rtu_proxy_map[2]}]},
            {"ID": 3, "protocols": ["modbus"], "rtus": [{"ID": 3, "scenario": "JHU", "protocol": "modbus", "PORT": 506, "IP": rtu_proxy_map[3], "NUM_CYCLES": 6, "DEBUG": 1, "CYCLES": ["1,coilStatus(3,0)", "1,holdingRegisters(3,0)", "1,holdingRegisters(3,1)", "1,holdingRegisters(3,2)", "1,holdingRegisters(3,3)", "1,holdingRegisters(3,4)"]}]},
            {"ID": 4, "protocols": ["modbus"], "rtus": [{"ID": 4, "scenario": "JHU", "protocol": "modbus", "PORT": 507, "IP": rtu_proxy_map[4], "NUM_CYCLES": 5, "DEBUG": 1, "CYCLES": ["1,coilStatus(4,0)", "1,holdingRegisters(4,0)", "1,holdingRegisters(4,1)", "1,holdingRegisters(4,2)", "1,holdingRegisters(4,3)"]}]},
            {"ID": 5, "protocols": ["dnp3"], "rtus": [{"ID": 5, "scenario": "JHU", "protocol": "dnp3", "PORT": 20006, "IP": rtu_proxy_map[5]}]},
            {"ID": 6, "protocols": ["dnp3"], "rtus": [{"ID": 6, "scenario": "JHU", "protocol": "dnp3", "PORT": 20007, "IP": rtu_proxy_map[6]}]},
            {"ID": 7, "protocols": ["dnp3"], "rtus": [{"ID": 7, "scenario": "JHU", "protocol": "dnp3", "PORT": 20008, "IP": rtu_proxy_map[7]}]},
            {"ID": 8, "protocols": ["modbus"], "rtus": [{"ID": 8, "scenario": "JHU", "protocol": "modbus", "PORT": 511, "IP": rtu_proxy_map[8], "NUM_CYCLES": 3, "DEBUG": 1, "CYCLES": ["1,coilStatus(8,0)", "1,holdingRegisters(8,0)", "1,holdingRegisters(8,1)"]}]},
            {"ID": 9, "protocols": ["modbus"], "rtus": [{"ID": 9, "scenario": "JHU", "protocol": "modbus", "PORT": 512, "IP": rtu_proxy_map[9], "NUM_CYCLES": 3, "DEBUG": 1, "CYCLES": ["1,coilStatus(9,0)", "1,holdingRegisters(9,0)", "1,holdingRegisters(9,1)"]}]},
            {"ID": 10, "protocols": ["modbus"], "rtus": [{"ID": 10, "protocol": "modbus", "scenario": "PNNL", "PORT": 502, "IP": rtu_proxy_map[10], "NUM_CYCLES": 3, "DEBUG": 1, "CYCLES": ["14,inputStatus(0,0)", "14,coilStatus(0,0)", "16,holdingRegisters(0,0)"]}]},
            {"ID": 11, "protocols": ["modbus"], "rtus": [{"ID": 11, "protocol": "modbus", "scenario": "EMS", "PORT": 513, "IP": rtu_proxy_map[11], "NUM_CYCLES": 3, "DEBUG": 1, "CYCLES": ["1,coilStatus(0,0)", "1,holdingRegisters(0,0)", "3,inputRegisters(0,0)"]}]},
            {"ID": 12, "protocols": ["modbus"], "rtus": [{"ID": 12, "protocol": "modbus", "scenario": "EMS", "PORT": 514, "IP": rtu_proxy_map[12], "NUM_CYCLES": 3, "DEBUG": 1, "CYCLES": ["1,coilStatus(0,0)", "1,holdingRegisters(0,0)", "3,inputRegisters(0,0)"]}]},
            {"ID": 13, "protocols": ["modbus"], "rtus": [{"ID": 13, "protocol": "modbus", "scenario": "EMS", "PORT": 515, "IP": rtu_proxy_map[13], "NUM_CYCLES": 3, "DEBUG": 1, "CYCLES": ["1,coilStatus(0,0)", "1,holdingRegisters(0,0)", "3,inputRegisters(0,0)"]}]},
            {"ID": 14, "protocols": ["modbus"], "rtus": [{"ID": 14, "protocol": "modbus", "scenario": "EMS", "PORT": 516, "IP": rtu_proxy_map[14], "NUM_CYCLES": 3, "DEBUG": 1, "CYCLES": ["1,coilStatus(0,0)", "1,holdingRegisters(0,0)", "3,inputRegisters(0,0)"]}]},
            {"ID": 15, "protocols": ["modbus"], "rtus": [{"ID": 15, "protocol": "modbus", "scenario": "EMS", "PORT": 517, "IP": rtu_proxy_map[15], "NUM_CYCLES": 3, "DEBUG": 1, "CYCLES": ["1,coilStatus(0,0)", "1,holdingRegisters(0,0)", "3,inputRegisters(0,0)"]}]},
            {"ID": 16, "protocols": ["modbus"], "rtus": [{"ID": 16, "protocol": "modbus", "scenario": "EMS", "PORT": 518, "IP": rtu_proxy_map[16], "NUM_CYCLES": 3, "DEBUG": 1, "CYCLES": ["1,coilStatus(0,0)", "1,holdingRegisters(0,0)", "3,inputRegisters(0,0)"]}]},
            {"ID": 17, "protocols": ["iec61850"], "rtus": [{"ID": 17, "scenario": "SUBSTATION", "protocol": "iec61850", "PORT": 20001, "IP": rtu_proxy_map[17]}]},
            {"ID": 18, "protocols": ["iec61850"], "rtus": [{"ID": 18, "scenario": "SUBSTATION", "protocol": "iec61850", "PORT": 20002, "IP": rtu_proxy_map[18]}]},
            {"ID": 19, "protocols": ["iec61850"], "rtus": [{"ID": 19, "scenario": "SUBSTATION", "protocol": "iec61850", "PORT": 20002, "IP": rtu_proxy_map[19]}]}
        ],
        "GLOBALS": {
            "modbus": {
                "PROTOCOL": "RTU",
                "N_POLL_SLAVE": 0,
                "CYCLETIME": 1000,
                "DEBUG": 1
            }
        }
    }
    return rtu_config

def main():
    config_file = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("config.json")
    if not config_file.exists():
        print(f"Error: Configuration file '{config_file}' not found.")
        sys.exit(1)

    with open(config_file, "r") as f:
        cfg = json.load(f)

    out_dir = Path(f"conf/conf_{cfg['conf_suffix']}")
    if out_dir.exists():
        print(f"Output directory {out_dir} already exists!")
        sys.exit(0)

    out_dir.mkdir(parents=True, exist_ok=True)

    # Partition sites into Control Centers and Data Centers
    raw_sites = cfg.get("sites", [])
    cc_sites = [s for s in raw_sites if s.get("type") == "control_center"]
    dc_sites = [s for s in raw_sites if s.get("type") == "data_center"]
    
    # Collect list of proxies (not checking validity, ensure the JSON is valid)
    proxies = cfg.get("proxies", [])
    num_proxies = len(proxies)
    proxy_ips = [proxy["ip"] for proxy in proxies]
    
    # Ordering Control Centers first maintains index alignment
    sites = cc_sites + dc_sites

    num_sites = len(sites)
    num_cc = len(cc_sites)

    # Dynamically compute replica counts across host machines
    total_rep = sum(len(s["hosts"]) for s in sites)
    cc_rep = sum(len(s["hosts"]) for s in cc_sites)

    # Build striped host map (round-robin replica ID assignment across sites)
    striped_hosts = []
    max_hosts_per_site = max((len(s["hosts"]) for s in sites), default=0)
    replica_id = 1
    for host_idx in range(max_hosts_per_site):
        for site in sites:
            if host_idx < len(site["hosts"]):
                # append replica id, ip, and spines ip (first ip addr for site)
                striped_hosts.append((replica_id, site["hosts"][host_idx]["ip"], site["hosts"][0]["ip"]))
                replica_id += 1

    # 1. Generate address.config & spines_address.config (using striped IDs)
    addr_lines = [f"{rep_id} {spines_ip}\n" for rep_id, ip, spines_ip in striped_hosts]
    addr_file = out_dir / "address.config"
    addr_file.write_text("".join(addr_lines))
    shutil.copy(addr_file, out_dir / "spines_address.config")

    # 2. Generate spines_int.conf
    spines_int = out_dir / "spines_int.conf"
    shutil.copy(Path(cfg["base_files"]["spines"]), spines_int)

    hosts_int = ["Hosts {\n"] + [f"    {i + 1} {s['hosts'][0]['ip']}\n" for i, s in enumerate(sites)] + ["}\n\nEdges {\n"]
    for i in range(1, num_sites + 1):
        for j in range(i + 1, num_sites + 1):
            hosts_int.append(f"    {i}  {j}    100\n")
    hosts_int.append("}\n\n")

    with open(spines_int, "a") as f:
        f.writelines(hosts_int)

    # 3. Generate spines_ext.conf
    spines_ext = out_dir / "spines_ext.conf"
    shutil.copy(Path(cfg["base_files"]["spines"]), spines_ext)

    hosts_ext = ["Hosts {\n"]
    for i, s in enumerate(cc_sites):
        hosts_ext.append(f"    {i + 1} {s['hosts'][0]['ip']}\n")
    for i, p in enumerate(proxies):
        hosts_ext.append(f"    {num_cc + i + 1} {p['ip']}\n")
    hmi_ext_id = num_cc + num_proxies + 1
    hosts_ext.append(f"    {hmi_ext_id} {cfg['hmi']['ip']}\n")
    hosts_ext.append("}\n\nEdges {\n")

    total_ext_nodes = num_cc + num_proxies + 1
    for i in range(1, total_ext_nodes + 1):
        for j in range(i + 1, total_ext_nodes + 1):
            if i <= num_cc:
                hosts_ext.append(f"    {i}  {j}    100\n")
    hosts_ext.append("}\n\n")

    with open(spines_ext, "a") as f:
        f.writelines(hosts_ext)

    # 4. Generate spines_ctrl.conf
    spines_ctrl = out_dir / "spines_ctrl.conf"
    shutil.copy(Path(cfg["base_files"]["spines"]), spines_ctrl)

    ctrl_ips = [s["hosts"][0]["ip"] for s in sites] + proxy_ips + [cfg["hmi"]["ip"]]
    total_ctrl_nodes = len(ctrl_ips)

    hosts_ctrl = ["Hosts {\n"]
    for i, ip in enumerate(ctrl_ips):
        hosts_ctrl.append(f"    {i + 1} {ip}\n")
    hosts_ctrl.append("}\n\nEdges {\n")

    for i in range(1, total_ctrl_nodes + 1):
        for j in range(i + 1, total_ctrl_nodes + 1):
            hosts_ctrl.append(f"    {i}  {j}    100\n")
    hosts_ctrl.append("}\n\n")

    with open(spines_ctrl, "a") as f:
        f.writelines(hosts_ctrl)

    # 5. Generate prime_def.h
    prime_def = out_dir / "prime_def.h"
    shutil.copy(Path(cfg["base_files"]["prime_def"]), prime_def)
    replace_defines(prime_def, {
        "NUM_F": cfg["num_f"],
        "NUM_K": cfg["num_k"]
    })

    # 6. Generate scada_def.h
    scada_def = out_dir / "scada_def.h"
    shutil.copy(Path(cfg["base_files"]["scada_def"]), scada_def)
    
    replace_defines(scada_def, {
        "NUM_SM": total_rep,
        "NUM_F": cfg["num_f"],
        "NUM_K": cfg["num_k"],
        "NUM_CC": num_cc,
        "NUM_CC_REPLICA": cc_rep,
        "NUM_SITES": num_sites,
        "NUM_CC_CONNECTORS": len(proxy_ips)+1,
        "SPINES_HMI_ADDR": f'"{cfg["hmi"]["ip"]}"' # added to specify hmi addr
    })

    int_site_ips = [s["hosts"][0]["ip"] for s in sites]
    ext_site_ips = [s["hosts"][0]["ip"] for s in cc_sites]
    connector_ips = proxy_ips + [cfg["hmi"]["ip"]]


    replace_array_define(scada_def, "SPINES_INT_SITE_ADDRS", int_site_ips)
    replace_array_define(scada_def, "SPINES_EXT_SITE_ADDRS", ext_site_ips)
    replace_array_define(scada_def, "CC_CONNECTORS", connector_ips)

    # 7. Generate docker-compose.yml (using striped IDs)
    first_ip = sites[0]["hosts"][0]["ip"] if sites and sites[0]["hosts"] else proxies[0]["ip"]
    net = ipaddress.IPv4Interface(f"{first_ip}/24").network
    subnet_str = str(net)
    gateway_str = str(net[1])

    # proxy_ip = cfg["proxy"]["ip"]
    hmi_ip = cfg["hmi"]["ip"]

    dc_services = []
    # Sort by replica ID so services appear in order spire1, spire2, etc.
    for rep_id, ip, spines_ip in sorted(striped_hosts, key=lambda x: x[0]):
        dc_services.append(
            f"  spire{rep_id}:\n"
            f"    image: spire-img\n"
            f"    pull_policy: never\n"
            f"    container_name: spire{rep_id}\n"
            f"    networks:\n"
            f"      spire-net:\n"
            f"        ipv4_address: {ip}\n"
            f"    cap_add:\n"
            f"      - NET_ADMIN\n"
            f"    command: python docker/run_replica.py -id {rep_id} -ip {ip}\n"
        )

    # Benchmark client
    # Keep this only if benchmark mode is still needed.
    # It needs an explicit --id because run_client.py uses args.id
    # when no -ip is provided.
    dc_services.append(
        f"  benchmark-client:\n"
        f"    image: spire-img\n"
        f"    pull_policy: never\n"
        f"    profiles:\n"
        f"      - benchmark\n"
        f"    container_name: spire-benchmark\n"
        f"    cap_add:\n"
        f"      - NET_ADMIN\n"
        f"    command: python docker/run_client_mod.py --type=benchmark --id=0\n"
    )

    # One PLC/proxy container per configured proxy
    for proxy_id, proxy in enumerate(proxies):
        proxy_ip = proxy["ip"]
        rtu_ids = ",".join(str(rtu_id) for rtu_id in proxy["rtus"])

        dc_services.append(
            f"  plc-client-{proxy_id}:\n"
            f"    image: spire-img\n"
            f"    pull_policy: never\n"
            f"    profiles:\n"
            f"      - full\n"
            f"    container_name: spire-plc-{proxy_id}\n"
            f"    networks:\n"
            f"      spire-net:\n"
            f"        ipv4_address: {proxy_ip}\n"
            f"    cap_add:\n"
            f"      - NET_ADMIN\n"
            f"    command: python docker/run_client_mod.py "
            f"--type=plc --id={proxy_id} "
            f"--rtus={rtu_ids} -ip={proxy_ip}\n"
        )

    # HMI client
    dc_services.append(
        f"  hmi-client:\n"
        f"    image: spire-img\n"
        f"    pull_policy: never\n"
        f"    profiles:\n"
        f"      - full\n"
        f"    container_name: spire-hmi\n"
        f"    networks:\n"
        f"      spire-net:\n"
        f"        ipv4_address: {hmi_ip}\n"
        f"    ports:\n"
        f"      - \"5051:5051\"\n"
        f"      - \"5052:5052\"\n"
        f"      - \"5053:5053\"\n"
        f"    cap_add:\n"
        f"      - NET_ADMIN\n"
        f"    command: python docker/run_client_mod.py "
        f"--type=hmi --id={len(proxies)} -ip={hmi_ip}\n"
    )
    docker_compose_content = (
        f"networks:\n"
        f"  spire-net:\n"
        f"    driver: bridge\n"
        f"    ipam:\n"
        f"      config:\n"
        f"        - subnet: {subnet_str}\n"
        f"          gateway: {gateway_str}\n"
        f"    name: spire-net\n\n"
        f"services:\n" + "\n".join(dc_services)
    )

    (out_dir / "docker-compose.yml").write_text(docker_compose_content)

    # 8. Generate target output config.json with updated RTU Proxy IPs
    
    # Generate proxy_id -> IP address map
    rtu_proxy_map = {}
    for proxy in proxies:
        for rtu_id in proxy["rtus"]:
            rtu_proxy_map[rtu_id] = proxy["ip"]
    
    rtu_json_path = out_dir / "config.json"
    rtu_data = get_rtu_template(rtu_proxy_map)
    with open(rtu_json_path, "w") as f:
        json.dump(rtu_data, f, indent=4)

if __name__ == "__main__":
    main()
