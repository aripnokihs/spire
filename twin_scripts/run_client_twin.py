"""
Modifications are currently ignoring benchmark and controls spines.
"""
import sys, argparse, subprocess, time, os

base_dir = "/twins/spireA"
log_dir = f"{base_dir}/logs"

def get_args(argv):
    parser = argparse.ArgumentParser(description="Run a Spire client")
    parser.add_argument('-ip', required=False, type=str, help='Client IP (default: 192.168.101.{100+ID})')
    parser.add_argument(
        '--type', '-t',
        choices=['benchmark', 'plc', 'hmi'],
        default='benchmark',
        help='Client type: benchmark, plc, or hmi (default: benchmark)'
    )
    parser.add_argument(
        '--reconf', '-r',
        action='store_true',
        help='Enable reconfiguration support by running the Spines control network and Config Agent'
    )
    parser.add_argument( # This argument is currently only used when specifying proxy nodes
        '--id',
        type=int,
        help='Node ID in the network'
    )
    parser.add_argument(
        '--rtus',
        type=str,
        help='RTU list for proxy separated by commas'
    )
    parser.add_argument(
        '-num_twins',
        required=False,
        type=int,
        help='Number of twins for running proxies'
    )
    parser.add_argument(
        '-twin',
        required=False,
        type=str,
        help='Actual twin for which hmi will be run'
    )
    return parser.parse_args(argv)

def run_cmd(cmd: str, tag: str, log_file: str) -> subprocess.Popen:
    """Run shell command, prefixing each line with [tag] before streaming to stdout and log file."""
    os.makedirs(log_dir, exist_ok=True)
    tee_cmd = f"{cmd} 2>&1 | sed -u 's/^/[{tag}] /' | tee -a {log_file}"
    return subprocess.Popen(tee_cmd, shell=True)

def start_plc(rtu_id):
    if 0 <= rtu_id <= 9: #JHU
        jhu_cmd = f"cd {base_dir}/plcs/jhu{rtu_id} && ./openplc -m {503+rtu_id} -d {20001+rtu_id}"
        run_cmd(jhu_cmd, f"plc_jhu_{rtu_id}", f"{log_dir}/out_plc_jhu_{rtu_id}.txt")
    elif rtu_id == 10: # PNNL
        pnnl_cmd = f"cd {base_dir}/plcs/pnnl_plc && ./openplc -m 502 -d 20000"
        run_cmd(pnnl_cmd, f"plc_pnnl", f"{log_dir}/out_plc_pnnl.txt")
    elif 11 <= rtu_id <= 13: # EMS
        ems_id = rtu_id - 11
        ems_cmd = f"cd {base_dir}/plcs/ems{ems_id} && ./openplc -m {513+ems_id} -d {20011+ems_id}"
        run_cmd(ems_cmd, f"plc_ems_{ems_id}", f"{log_dir}/out_plc_ems_{ems_id}.txt")
    elif 14 <= rtu_id <= 16: # EMS
        names = ["ems_hydro", "ems_solar", "ems_wind"]
        ems_id = rtu_id - 14
        name = names[ems_id]
        ems_cmd = f"cd {base_dir}/plcs/{name} && ./openplc -m {516+ems_id} -d {20014+ems_id}"
        run_cmd(ems_cmd, f"plc_{name}", f"{log_dir}/out_plc_{name}.txt")
        
def main(argv):
    global log_dir, base_dir
    args = get_args(argv)

    i = args.id # retrieve '--id' argument from command
    
    # Check number of digital twins, default is 1
    if args.num_twins:
        twin_num = args.num_twins
    else:
        twin_num = 1
    
    # Specify which digital twin it is, default is twin A
    if args.twin:
        dir_letter = args.twin
        base_dir = f"/twins/spire{dir_letter}"
        log_dir = f"{base_dir}/logs"
    else:
        dir_letter = 'A'
        base_dir = "/twins/spireA"
        log_dir = f"{base_dir}/logs"

    if args.rtus:
        rtu_ids = [int(x) for x in args.rtus.split(",")]
    else:
        rtu_ids = []
    
    # Determine IPC path and application count based on client type
    if args.type == 'plc':
        # num_apps = 10
        num_apps = len(rtu_ids)
        ipc_path = "/tmp/rtu_ipc_main"
    elif args.type == 'hmi':
        num_apps = 3
        ipc_path = "/tmp/hmi_ipc_main"
    else: #benchmark
        num_apps = 10
        ipc_path = "/tmp/bm_ipc_main"
        args.type = "benchmark"

    if args.ip:
        ip = args.ip
    else:
        ip = f"192.168.101.{100 + i}"
    
    # Store ext spines processes
    sp_procs = []

    # Conditionally launch proxy/plc processes
    if args.type == 'plc':
        padded_port = 0
        for twin in range(twin_num):
            log_dir_letter = chr(ord('A') + twin)
            padded_port = 10000*twin
            spines_base_dir = f"/twins/spire{log_dir_letter}"
            spines_ext_cmd = f"cd {spines_base_dir}/spines/daemon && ./spines -p {8120+padded_port} -c spines_ext.conf -I {ip}"
            proc = run_cmd(spines_ext_cmd, f"spines_ext_{args.type}", f"{log_dir}/out_spines_ext_{args.type}{log_dir_letter}.txt")
            sp_procs.append(proc)
        
        time.sleep(2)
        
        for rtu_id in rtu_ids: # only start plc/rtus listed in arguments
            start_plc(rtu_id)
        
        for proxy_id in rtu_ids: # only start proxies for selected plc/rtus
            proxy_cmd = (
                f"cd {base_dir}/proxy && "
                f"./proxy -c rtus_plcs "
                f"-id {proxy_id} "
                f"-sd {ip}:8120 "
                f"-dt twins-{args.id}.txt "
                f"-n 1"
            )
            run_cmd(proxy_cmd, f"proxy_{proxy_id}", f"{log_dir}/out_proxy_{proxy_id}.txt")

    # Conditionally launch HMI processes
    if args.type == 'hmi':
        port_padding = 10000 * (ord(dir_letter) - 65)
        spines_base_dir = f"/twins/spire{dir_letter}"
        spines_ext_cmd = f"cd {spines_base_dir}/spines/daemon && ./spines -p {8120+port_padding} -c spines_ext.conf -I {ip}"
        proc = run_cmd(spines_ext_cmd, f"spines_ext_{args.type}", f"{log_dir}/out_spines_ext_{args.type}.txt")
        sp_procs.append(proc)
        
        time.sleep(2)
        
        hmi_base_dir = f"/twins/spire{dir_letter}"
        for hmi_id, name in enumerate(["jhu_hmi", "pnnl_hmi", "ems_hmi"]):
            hmi_cmd = f"cd {hmi_base_dir}/hmis/{name} && ./{name} {ip}:{8120+port_padding} -port={5051+hmi_id}"
            run_cmd(hmi_cmd, f"{name}", f"{log_dir}/out_{name}.txt")

    # Conditionally launch reconfiguration processes
    if args.reconf:
        port_padding = 10000 * (ord(dir_letter) - 65)
        spines_ctrl_cmd = f"cd {base_dir}/spines/daemon && ./spines -p {8900+port_padding} -c spines_ctrl.conf"
        conf_agent_cmd  = f"cd {base_dir}/prime/bin && ./config_agent {i} {ip} {ipc_path} p {num_apps}"

        run_cmd(spines_ctrl_cmd, f"spines_ctrl_{args.type}", f"{log_dir}/out_spines_ctrl_{args.type}.txt")
        time.sleep(5)
        run_cmd(conf_agent_cmd, f"conf_agent_{args.type}", f"{log_dir}/out_conf_agent_{args.type}.txt")

    # Wait for external spines process to exit
    for proc in sp_procs:
        proc.wait()

if __name__ == "__main__":
    main(sys.argv[1:])
