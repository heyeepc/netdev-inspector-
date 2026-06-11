import yaml
import logging
from concurrent.futures import ThreadingPoolExecutor
from netmiko import ConnectHandler
from utils.data_processor import parse_huawei_cpu, parse_huawei_memory, judge_metrics
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

MOCK_MODE = True  # eNSP 调通前开启 Mock，方便调试 Excel 导出和阈值告警逻辑


def load_config():
    with open("config/settings.yaml", "r", encoding="utf-8") as f:
        settings = yaml.safe_load(f)
    with open("config/devices.yaml", "r", encoding="utf-8") as f:
        devices = yaml.safe_load(f)
    return settings, devices


def inspect_device(device, thresholds):
    ip = device['ip']
    logging.info(f"🚀 开始巡检设备: {ip}")

    if MOCK_MODE:
        # 模拟真实华为设备返回的 CLI 文本
        import random
        mock_cpu_pct = random.choice([15, 42, 88, 50])  # 随机制造一个超标的 88%
        mock_mem_pct = random.choice([30, 60, 70, 91])  # 随机制造一个超标的 91%

        raw_cpu = f"CPU Usage Stat. System CPU Usage : {mock_cpu_pct}%"
        raw_mem = f"Memory Usage Ratio : {mock_mem_pct}%"

        cpu_val = parse_huawei_cpu(raw_cpu)
        mem_val = parse_huawei_memory(raw_mem)
        return judge_metrics(ip, cpu_val, mem_val, thresholds)

    # ---------------- 真实环境执行连接 (eNSP / 物理设备) ----------------
    try:
        with ConnectHandler(**device) as ssh:
            # 华为交换机/路由器进入特权查看视图
            ssh.enable()

            # 执行华为特有巡检命令
            raw_cpu = ssh.send_command("display cpu-usage")
            raw_mem = ssh.send_command("display memory-usage")

            # 如果配置了 TextFSM，也可以直接获取结构化状态，比如 OSPF
            # ospf_data = ssh.send_command("display ospf peer", use_textfsm=True)

            cpu_val = parse_huawei_cpu(raw_cpu)
            mem_val = parse_huawei_memory(raw_mem)

            # 进行数据比对与告警判定
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

    # 生产级实践：多线程并发巡检（网络 IO 密集型最佳方案）
    final_reports = []
    with ThreadingPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(inspect_device, dev, thresholds) for dev in devices]
        for future in futures:
            final_reports.append(future.result())

    # 生成 Excel 报表
    generate_excel_report(final_reports, output_path="reports/网络巡检月度报告.xlsx")


if __name__ == "__main__":
    import os

    os.makedirs("reports", exist_ok=True)
    main()