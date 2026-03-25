# LocalMoneyAI v0.4.0

[中文](#中文) | [English](#english)

---

<a name="english"></a>
## English

### 📖 Overview

A privacy-first local AI-powered personal finance tracker. All data stays on your device - no cloud, no account, no tracking.

### ✨ Features

- **🤖 AI-Powered Entry** - Just type naturally: "Lunch 35, taxi 20" and AI extracts the data
- **📸 Receipt Scanning** - Upload receipts and AI automatically recognizes transactions
- **📊 Smart Analytics** - Interactive charts and AI-powered insights
- **🔐 100% Local** - Your financial data never leaves your computer
- **💾 One-Click Backup** - Export all data anytime

### 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Streamlit |
| AI Engine | Ollama (Local LLM) |
| Database | SQLite |
| Charts | Plotly |

### 📦 Installation

#### Prerequisites

- Python 3.9+
- [Ollama](https://ollama.ai/)

#### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/rongjiedu0-code/LocalMoneyAI-refactored.git
cd LocalMoneyAI-refactored

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Ollama and download a model
ollama pull qwen2.5:7b

# 5. Run the app
streamlit run app.py
🏗️ Project Structure
LocalMoneyAI_v0.4.0/
├── app.py                 # Main entry point
├── config.json            # Configuration
├── database/              # Data layer
├── services/              # Business logic
│   ├── ai/               # AI services
│   └── transaction/      # Transaction management
├── views/                 # Streamlit UI pages
└── utils/                 # Utilities
📄 License
MIT License

 [blocked]

中文
📖 项目简介
一款以隐私为优先的本地 AI 记账工具。所有数据都保存在你的设备上——无需联网、无需注册、无追踪。

✨ 功能特性
🤖 AI 智能记账 - 自然语言输入："午饭35，打车20"，AI 自动提取数据
📸 票据识别 - 上传小票照片，AI 自动识别交易记录
📊 智能分析 - 交互式图表和 AI 财务洞察
🔐 100% 本地运行 - 你的财务数据从不离开电脑
💾 一键备份 - 随时导出所有数据
🛠️ 技术栈
| 组件 | 技术 |
|------|------|
| 前端 | Streamlit |
| AI 引擎 | Ollama (本地大模型) |
| 数据库 | SQLite |
| 图表 | Plotly |

📦 安装指南
环境要求
Python 3.9+
Ollama
快速开始
# 1. 克隆仓库
git clone https://github.com/rongjiedu0-code/LocalMoneyAI-refactored.git
cd LocalMoneyAI-refactored

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装 Ollama 并下载模型
ollama pull qwen2.5:7b

# 5. 运行应用
streamlit run app.py
🏗️ 项目结构
LocalMoneyAI_v0.4.0/
├── app.py                 # 主入口
├── config.json            # 配置文件
├── database/              # 数据层
├── services/              # 业务逻辑层
│   ├── ai/               # AI 服务
│   └── transaction/      # 交易管理
├── views/                 # Streamlit 页面
└── utils/                 # 工具函数
📄 开源协议
MIT License

⭐ Star History
如果这个项目对你有帮助，请给个 Star ⭐

Made with ❤️ by rongjiedu0-code
