import yaml
import logging
from concurrent.futures import ThreadPoolExecutor
from netmiko import ConnectHandler
from utils.data_processor import parse_huawei_cpu, parse_huawei_memory, judge_metrics, parse_linux_cpu, parse_linux_memory
from utils.excel_reporter import generate_excel_report

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler("logs/inspector.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# 🚀 关键：关闭 Mock 模式，开启真实物理/虚拟设备巡检
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

    # 1. 模拟环境逻辑
    if MOCK_MODE:
        import random
        mock_cpu_pct = random.choice([15, 42, 88, 50])
        mock_mem_pct = random.choice([30, 60, 70, 91])

        raw_cpu = f"CPU Usage Stat. System CPU Usage : {mock_cpu_pct}%"
        raw_mem = f"Memory Usage Ratio : {mock_mem_pct}%"

        cpu_val = parse_huawei_cpu(raw_cpu)
        mem_val = parse_huawei_memory(raw_mem)
        return judge_metrics(ip, cpu_val, mem_val, thresholds)

    # 2. 真实环境执行连接 (树莓派 / eNSP 物理与虚拟设备)
    try:
        # 初始化变量防报错
        cpu_val = 0
        mem_val = 0

        with ConnectHandler(**device) as ssh:
            if device['device_type'] == 'huawei':
                ssh.enable()
                raw_cpu = ssh.send_command("display cpu-usage")
                raw_mem = ssh.send_command("display memory-usage")
                cpu_val = parse_huawei_cpu(raw_cpu)
                mem_val = parse_huawei_memory(raw_mem)

            elif device['device_type'] == 'linux':
                # 💡 实机向你的树莓派发送 Linux 标准网管命令
                # 使用 top -b -n 1 抓取单次 CPU 快照
                raw_cpu = ssh.send_command("top -b -n 1 | grep '%Cpu'")
                raw_mem = ssh.send_command("free -m")

                # 调用你写好的 Linux 解析函数
                cpu_val = parse_linux_cpu(raw_cpu)
                mem_val = parse_linux_memory(raw_mem)

            # 统一送入阈值判定模块
            report_data = judge_metrics(ip, cpu_val, mem_val, thresholds)
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

    # 生成 Excel 报表
    generate_excel_report(final_reports, output_path="reports/网络巡检月度报告.xlsx")


if __name__ == "__main__":
    import os
    os.makedirs("reports", exist_ok=True)
    main()