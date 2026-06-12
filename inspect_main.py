import yaml
import logging
from concurrent.futures import ThreadPoolExecutor
from netmiko import ConnectHandler
from utils.data_processor import (
    parse_huawei_cpu, parse_huawei_memory, judge_metrics,
    parse_linux_cpu, parse_linux_memory, parse_huawei_interfaces, parse_huawei_ospf
)
from utils.excel_reporter import generate_excel_report

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler("logs/inspector.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# 💡 提示：如果你在电脑上连着 eNSP 调数通，把这里改成 False。
# 如果想先看表格扩展后的模拟效果，可以先保持 True 跑一次！
MOCK_MODE = False


def load_config():
    with open("config/settings.yaml", "r", encoding="utf-8") as f:
        settings = yaml.safe_load(f)
    with open("config/devices.yaml", "r", encoding="utf-8") as f:
        devices = yaml.safe_load(f)
    return settings, devices


def inspect_device(device, thresholds):
    ip = device['ip']
    logging.info(f"🚀 开始巡检设备: {ip}")

    # --- 1. MOCK 模拟数通故障环境（用于本地无设备测试） ---
    if MOCK_MODE:
        import random
        if device['device_type'] == 'huawei':
            # 随机模拟点故障：比如突然有个接口 down 了，或者 OSPF 挂了
            mock_down_ifs = random.choice([[], ["GE0/0/2(down/down)"]])
            mock_bad_ospf = random.choice([[], ["邻居10.1.1.2(状态:Init)"]])
            return judge_metrics(ip, random.randint(10, 40), random.randint(20, 50), mock_down_ifs, mock_bad_ospf, thresholds)
        else:
            return judge_metrics(ip, 12, 35, [], [], thresholds)

    # --- 2. 真实物理与虚拟网络连接 ---
    try:
        cpu_val, mem_val = 0, 0
        down_ifs, bad_ospf = [], []

        with ConnectHandler(**device) as ssh:
            if device['device_type'] == 'huawei':
                ssh.enable()
                # 抓取基础性能
                raw_cpu = ssh.send_command("display cpu-usage")
                raw_mem = ssh.send_command("display memory-usage")
                # 🚀 抓取数通协议与接口状态
                raw_if = ssh.send_command("display interface brief")
                raw_ospf = ssh.send_command("display ospf peer")

                cpu_val = parse_huawei_cpu(raw_cpu)
                mem_val = parse_huawei_memory(raw_mem)
                down_ifs = parse_huawei_interfaces(raw_if)
                bad_ospf = parse_huawei_ospf(raw_ospf)

            elif device['device_type'] == 'linux':
                raw_cpu = ssh.send_command("top -b -n 1 | grep '%Cpu'")
                raw_mem = ssh.send_command("free -m")
                cpu_val = parse_linux_cpu(raw_cpu)
                mem_val = parse_linux_memory(raw_mem)

            # 送入综合判定器
            report_data = judge_metrics(ip, cpu_val, mem_val, down_ifs, bad_ospf, thresholds)
            logging.info(f"✅ 设备 {ip} 巡检完成，状态: {report_data['status']}")
            return report_data

    except Exception as e:
        logging.error(f"❌ 设备 {ip} 连接或执行失败: {str(e)}")
        return {
            "ip": ip, "cpu": "ERR", "memory": "ERR",
            "status": "告警", "issue": f"SSH连接失败: {str(e)}"
        }


def main():
    settings, devices = load_config()
    thresholds = settings['thresholds']

    logging.info(f"📂 成功加载 {len(devices)} 台设备资产，并发线程池启动...")

    final_reports = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(inspect_device, dev, thresholds) for dev in devices]
        for future in futures:
            final_reports.append(future.result())

    generate_excel_report(final_reports, output_path="reports/网络巡检月度报告.xlsx")


if __name__ == "__main__":
    import os
    os.makedirs("reports", exist_ok=True)
    main()

