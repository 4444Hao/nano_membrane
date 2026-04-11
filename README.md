# VACNT-Membrane-Optimizer: AI-Driven Heterogeneous Pore Arrangement

**基于大语言模型（LLM）的垂直碳纳米管（VACNT）膜异质孔径排布优化项目**

本仓库旨在利用 [SakanaAI/ShinkaEvolve](https://github.com/SakanaAI/ShinkaEvolve) 的进化算法框架，解决海水淡化 VACNT 膜设计中的核心难题——**非等圆圆形打包问题（Non-Equal Circle Packing）**。

## 🎯 研究愿景：从“均质严苛”到“异质协同”

传统膜分离技术受限于“渗透性-选择性”权衡（Trade-off），要求膜孔高度均一且尺寸严苛（通常 <1nm）。本项目使用了一种创新的**动态振荡范式**：
1.  **引入振荡**：通过微小的机械振荡（~2Å），破坏水合层，激活大孔径（3.5nm）的过滤能力。
2.  **异质协同**：不再追求孔径均一，而是设计 **1nm（高选择性）** 与 **3.5nm（高通量）** 的异质孔协同分布。
3.  **AI 破局**：利用大语言模型（LLM）驱动的进化算法，寻找在保持最小安全距离约束下，最大化膜利用效率的最优排布方案。

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
git clone https://github.com/your-username/VACNT-Membrane-Optimizer.git
cd VACNT-Membrane-Optimizer

# 2. 推荐使用 uv (也可用 pip)
uv venv --python 3.11
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate

# 3. 安装依赖
uv pip install -e .


