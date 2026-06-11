import re


def parse_huawei_cpu(raw_text):
    """
    解析华为 display cpu-usage 的返回文本，提取出纯数字利用率
    """
    match = re.search(r"System CPU Usage\s*:\s*(\d+)%", raw_text)
    if match:
        return int(match.group(1))
    match_alt = re.search(r"CPU Usage\s*:\s*(\d+)%", raw_text)
    if match_alt:
        return int(match_alt.group(1))
    return 0


def parse_huawei_memory(raw_text):
    """
    解析 display memory-usage 的返回文本
    """
    match = re.search(r"Memory Usage Ratio\s*:\s*(\d+)%", raw_text)
    if match:
        return int(match.group(1))
    return 0


def judge_metrics(ip, cpu_val, mem_val, thresholds):
    """
    根据给定的阈值配置，判定设备当前是正常还是告警
    """
    status = "正常"
    logs = []

    if cpu_val > thresholds['cpu_usage_max']:
        status = "告警"
        logs.append(f"CPU利用率({cpu_val}%)超过阈值")

    if mem_val > thresholds['memory_usage_max']:
        status = "告警"
        logs.append(f"内存利用率({mem_val}%)超过阈值")

    return {
        "ip": ip,
        "cpu": f"{cpu_val}%",
        "memory": f"{mem_val}%",
        "status": status,
        "issue": ", ".join(logs) if logs else "无异常"
    }
def parse_linux_cpu(raw_text):
    """
    解析 top -b -n 1 返回的 CPU 空闲率，并换算为利用率
    """
    # 示例行：%-Cpu(s):  5.0 us,  2.0 sy,  0.0 ni, 93.0 id ...
    match = re.search(r"(\d+\.\d+)\s*id", raw_text)
    if match:
        idle_cpu = float(match.group(1))
        return int(100 - idle_cpu)  # 利用率 = 100% - 空闲率
    return 0

def parse_linux_memory(raw_text):
    """
    解析 free -m 返回的内存数据
    """
    # 示例：Mem:           3800        1000         500         100         300        2300
    # 对应：total        used        free      shared  buff/cache   available
    lines = raw_text.splitlines()
    for line in lines:
        if line.startswith("Mem:"):
            parts = line.split()
            total = int(parts[1])
            available = int(parts[6])  # 💡 取第 7 列的 available，而不是 used
            mem_usage = int((total - available) / total * 100)
            return mem_usage
    return 0