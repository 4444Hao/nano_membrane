# ShinkaEvolve Nano-Membrane Fork

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)


**基于大语言模型（LLM）的垂直碳纳米管（VACNT）膜异质孔径排布优化项目**

![项目Logo](https://example.com/shinkaevolve-logo.png)


本仓库旨在利用 **ShinkaEvolve** 的进化算法框架，解决海水淡化 VACNT 膜设计中的核心难题——**非等圆圆形打包问题（Non-Equal Circle Packing），实现通量与截留率的动态平衡**。

**💡 核心逻辑**
传统膜分离受限于“渗透性-选择性”权衡。本项目引入**动态振荡范式**，通过微小机械振荡激活大孔径（3.5nm）能力，并设计 **1nm（高选择性）至3.5nm（高通量）的6种类型的异质孔协同**。本代码库负责寻找在安全距离约束下，最大化膜功能利用效率的最优排布方案。

---

## 📂 仓库结构

本仓库已对上游源码进行精简，专注于 `nano_membrane` 场景：

*   `shinka/` - ShinkaEvolve 运行框架核心代码
*   `examples/nano_membrane/` - **核心工作区**：包含 VACNT 膜优化的任务定义、配置与评估脚本
*   `pyproject.toml` - 依赖配置
*   `LICENSE` - Apache License 2.0

---

## ⚙️ 快速开始

### 1. 环境准备
建议使用 Python 3.11 环境。

```bash
# 1. 克隆仓库
git clone https://github.com/4444Hao/nano_membrane.git
cd VACNT-Membrane-Optimizer

# 2. 推荐使用 uv (也可用 pip)
uv venv --python 3.11
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate

# 3. 安装依赖
uv pip install -e .
```

### 2. 运行单点评估 (Debug)
无需 API Key，用于验证初始设计方案的适应度。

```bash
cd examples/nano_membrane
python evaluate.py --program_path initial.py --results_dir results/manual_eval
```

### 3. 启动 AI 进化 (Evolution)
让 LLM 开始寻找最优的孔隙排布方案。

```bash
python run_evo_async.py --config_path shinka_small.yaml
```

> **注意**：运行进化任务需要配置 LLM API Key。
> 默认配置使用 OpenAI 模型（gpt-5-mini），请确保环境变量中包含 `OPENAI_API_KEY`。
> 若使用其他模型，请修改 `shinka_small.yaml` 中的配置。

---

## 📊 结果说明

*   **输出目录**：`examples/nano_membrane/results/`
*   **预期产出**：
    *   进化过程中生成的最优孔隙排布代码（Python 脚本）。
    *   对应的适应度评分（基于单位面积过滤率与速率的数学模型预测）。
    *   *后续步骤*：将此处生成的最优坐标导入 LAMMPS/GROMACS 进行分子动力学模拟验证。

---

## 🏛️ 上游来源
本项目基于 <SakanaAI/ShinkaEvolve> 修改，遵循 Apache License 2.0.
```
