## netdev-inspector ##

## 📂 项目结构

```text

 PythonProject2/
├── .venv/
├── config/
│   ├── devices.yaml
│   └── settings.yaml
├── logs/
│   └── inspector.log (implied)
├── utils/
│   ├── data_processor.py
│   └── excel_reporter.py
└── inspect_main.py

```

readme_content = """# Multi-Threaded Network Automation O&M Inspection System

这是一个基于 Python 开发的网络自动化巡检与运维监控系统。系统支持异构网络环境，能够同时并发登录多个网络节点（如 Linux 服务器、树莓派、主流数通设备等），自动执行巡检指令，解析系统核心指标（CPU、内存、业务服务状态、网络连通性等），并自动生成标准的企业级 Excel 巡检月度报告。

本项目非常适合用于自动化运维（NetDevOps）实战、毕设参考或个人简历项目加分。

---

## 🚀 核心特性

- **多线程并发巡检**：采用 `concurrent.futures.ThreadPoolExecutor` 线程池架构，支持多节点并发登录，大幅提升大规模网络环境下的巡检效率。
- **异构设备支持**：基于 `Netmiko` 库封装，具备极强的扩展性，可同时完美兼容 Linux 主机（如树莓派）与主流数通设备（如华为 VRP 系统）。
- **指标智能解析**：内置稳健的文本解析与正则提取模块，自动捕获设备 CPU 利用率、内存剩余空间、核心服务端口开放状态及网络丢包率等关键数据。
- **动态阈值告警**：支持在配置文件中自定义各项指标的告警阈值（如内存利用率 > 90% 触发告警），并在生成的报告中进行高亮标注。
- **可视化 Excel 报表**：基于 `openpyxl` 自动生成格式精美、排版专业的 Excel 巡检报告，支持单元格样式动态填充（正常显示为浅绿，告警自动标红）。
- **完善的日志追踪**：内置 `logging` 模块，全流程记录并发线程的连接状态、执行进度及异常错误，方便快速排错。

---

