import re


def parse_huawei_cpu(raw_text):
    match = re.search(r"System CPU Usage\s*:\s*(\d+)%", raw_text)
    if match: return int(match.group(1))
    match_alt = re.search(r"CPU Usage\s*:\s*(\d+)%", raw_text)
    if match_alt: return int(match_alt.group(1))
    return 0


def parse_huawei_memory(raw_text):
    match = re.search(r"Memory Usage Ratio\s*:\s*(\d+)%", raw_text)
    if match: return int(match.group(1))
    return 0


def parse_linux_cpu(raw_text):
    match = re.search(r"(\d+\.\d+)\s*id", raw_text)
    if match: return int(100 - float(match.group(1)))
    return 0


def parse_linux_memory(raw_text):
    lines = raw_text.splitlines()
    for line in lines:
        if line.startswith("Mem:"):
            parts = line.split()
            total, available = int(parts[1]), int(parts[6])
            return int((total - available) / total * 100)
    return 0


# ==================== 🚀 新增数通核心解析函数 ====================

def parse_huawei_interfaces(raw_text):
    """
    解析 display interface brief
    提取出所有 DOWN 的物理接口
    """
    down_interfaces = []
    lines = raw_text.splitlines()
    for line in lines:
        # 匹配华为接口状态行的典型特征，过滤掉表头
        # 示例: GigabitEthernet0/0/1        up    up       0%    0%          0          0
        if any(x in line for x in ["Ethernet", "GE", "XGE", "Vlanif"]):
            parts = line.split()
            if len(parts) >= 3:
                if_name = parts[0]
                phy_status = parts[1].lower()  # 物理状态
                protocol_status = parts[2].lower()  # 协议状态

                # 如果接口是 down，记录下来
                if phy_status == "down" or protocol_status == "down":
                    down_interfaces.append(f"{if_name}({phy_status}/{protocol_status})")
    return down_interfaces


def parse_huawei_ospf(raw_text):
    """
    解析 display ospf peer
    提取出状态不是 FULL (或 2-Way) 的邻居
    """
    abnormal_ospf = []
    # 华为的 OSPF 回显通常包含 Router ID, Peer IP 和 State
    # 我们用正则捕获 Peer 的 IP 和它的 State
    # 示例:  Router ID: 1.1.1.1          Address: 10.1.1.1
    #        State: Full        Mode:NbrSelect  Priority: 1

    peer_ips = re.findall(r"Address:\s*([\d\.]+)", raw_text)
    states = re.findall(r"State:\s*([a-zA-Z\d\-]+)", raw_text)

    for ip, state in zip(peer_ips, states):
        if state.upper() not in ["FULL", "2-WAY"]:
            abnormal_ospf.append(f"邻居{ip}(状态:{state})")

    return abnormal_ospf


def judge_metrics(ip, cpu_val, mem_val, down_ifs, bad_ospf, thresholds):
    """
    生产级多维指标综合判定
    """
    status = "正常"
    logs = []

    if isinstance(cpu_val, int) and cpu_val > thresholds['cpu_usage_max']:
        status = "告警"
        logs.append(f"CPU({cpu_val}%)超标")

    if isinstance(mem_val, int) and mem_val > thresholds['memory_usage_max']:
        status = "告警"
        logs.append(f"内存({mem_val}%)超标")

    # 数通状态判定
    if down_ifs:
        status = "告警"
        logs.append(f"接口异常:{'|'.join(down_ifs)}")

    if bad_ospf:
        status = "告警"
        logs.append(f"OSPF异常:{'|'.join(bad_ospf)}")

    return {
        "ip": ip,
        "cpu": f"{cpu_val}%" if isinstance(cpu_val, int) else cpu_val,
        "memory": f"{mem_val}%" if isinstance(mem_val, int) else mem_val,
        "status": status,
        "issue": ", ".join(logs) if logs else "无异常"
    }