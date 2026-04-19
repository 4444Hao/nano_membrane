# ShinkaEvolve Nano-Membrane Fork

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)


**基于大语言模型（LLM）的垂直碳纳米管（VACNT）膜异质孔径排布优化项目**

![项目Logo](https://example.com/shinkaevolve-logo.png)


本仓库旨在利用 **ShinkaEvolve** 的进化算法框架，解决海水淡化 VACNT 膜设计中的核心难题——**非等圆圆形打包问题（Non-Equal Circle Packing），实现通量与截留率的多目标优化**。

**💡 核心逻辑**
传统膜分离受限于“渗透性-选择性”权衡。本项目引入**动态振荡范式**，通过微小机械振荡激活大孔径（3.5nm）能力，并设计 **1nm（高选择性）至3.5nm（高通量）的6种类型的异质孔协同**。在此前提下，本代码库负责在安全距离约束下，寻找最大化膜功能利用效率的最优口径排布方案。

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
python evaluate.py --program_path initial.py --results_dir results/manual_eval
```

### 3. 启动 AI 进化 (Evolution)
让 LLM 开始寻找最优的孔隙排布方案。

```bash
python run_evo_async.py --config_path shinka_small.yaml
```

> **注意**：运行进化任务需要配置 LLM API Key。
> 默认配置使用 OpenAI 模型（gpt-5-mini），请确保环境变量中包含 `OPENAI_API_KEY`。
> 若使用其他模型，请修改 `shinka_small.yaml` 中的配置（需符合上游支持的模型型号）。

---

## 📊 结果说明

*   **输出目录**：`examples/nano_membrane/results/`
*   **预期产出**：
    *   进化过程中生成的最优孔隙排布代码（best文件）。
    *   对应的适应度评分（基于单位面积过滤率与速率的数学模型预测）。
    *   *后续步骤*：将此处生成的最优坐标导入 LAMMPS/GROMACS 进行分子动力学模拟验证。

---

## 🏛️ 上游来源
本项目基于 <SakanaAI/ShinkaEvolve> 修改，遵循 Apache License 2.0.


## 🎨 可视化与实时监控

### 1. 最优解可视化 (Best Solution Viz)
在进化结束后，你可以使用以下命令对找到的最优解进行详细的可视化分析。这将生成包含孔隙排布图、适应度分布等信息的报告。

**Windows PowerShell 命令：**
```powershell
python examples\nano_membrane\evaluate.py `
  --program_path examples\nano_membrane\results\membrane_run\best\main.py `
  --results_dir examples\nano_membrane\results\membrane_run\best_viz `
  --num_runs 5 `
  --run_workers 1 `
  --save_artifacts best_only
```

### 2. 官方 WebUI 实时监控
在运行进化任务（`run_evo_async.py`）的同时，你可以启动官方的 WebUI 工具，在浏览器中实时查看进化进度、种群分布和最优解的图形化展示。

**操作步骤：**
1.  保持进化脚本运行。
2.  打开一个新的终端窗口。
3.  执行以下命令启动可视化服务：

```bash
python -m shinka.webui.visualization --port 8888 --open
```

## 📂 Nano Membrane 结果目录说明（交接文档）

### 1. 目录快照示例

```text
examples/nano_membrane/results/
`-- membrane_run/
   |-- programs.sqlite
   |-- bandit_state.pkl
   |-- evolution_run.log
   |-- best/
   |-- best_viz/
   |-- gen_0 ... gen_75
```

### 2. 术语对照（交接建议统一用词）

| 术语 | 说明 |
| :--- | :--- |
| **Generation** | 代（一次候选迭代单元） |
| **Candidate** | 候选程序（本代要评估的代码） |
| **Archive** | 归档池（历史高质量候选集合） |
| **Best** | 当前全局最优候选快照 |
| **Recheck** | 复评（对某候选再次评估） |
| **Attempt** | 补丁尝试记录（含重采样与多次 patch） |
| **Public Metrics** | 对外展示指标（用于排序/汇报） |
| **Private Metrics** | 内部细节指标（用于调试与分析） |
| **Combined Score** | 最终综合分（本任务核心排序分） |

---

### 3. 根目录关键文件说明（`membrane_run/`）

#### `programs.sqlite`
-   **用途**：主数据库，存放整轮进化状态与历史。
-   **核心内容**：`programs`（候选代码、父子关系、分数）、`archive`（归档成员）、`metadata_store`（运行状态）。
-   **场景**：查询演化路径、可视化工具读取、续跑恢复。

#### `evolution_run.log`
-   **用途**：全局运行日志（**最先看的排障入口**）。
-   **内容**：并发配置、模型调用成本、调度与失败信息。

#### `bandit_state.pkl`
-   **用途**：模型选择器（bandit/UCB）状态快照。
-   **场景**：续跑时延续模型策略，分析模型偏置。

---

### 4. 代目录标准结构（`gen_<k>/`）

```text
gen_/
|-- main.py                  # 本代最终被评估的候选代码
|-- original.py              # 打补丁前的父版本代码
|-- edit.diff                # 最终应用后的差异补丁
|-- rewrite.txt              # LLM 输出的中间补丁表示
`-- attempts/                # 补丁尝试轨迹
    `-- novelty_/resample_/patch_/
       |-- llm_response.txt  # 模型原始回复全文
       |-- metadata.json     # 尝试元数据（成功标记、错误等）
       `-- patch.txt         # 提取出的可应用补丁
`-- results/                 # 评估输出
    |-- correct.json         # 是否通过
    |-- metrics.json         # 核心评分文件
    |-- run_summary.json     # 多次运行汇总
    |-- job_log.out          # 标准输出
    `-- job_log.err          # 标准错误
```

---

### 5. `results/` 评估输出文件详解

-   **`correct.json`**：最简状态，`"correct": true/false`。
-   **`metrics.json`**：**核心排序依据**。包含 `combined_score`、`public`（展示指标）、`private`（调试指标）。
-   **`run_summary.json`**：多次运行汇总（如 5 次运行的 `feasible_rate`、失败统计）。
-   **`job_log.out/err`**：评估进程的标准输出与错误堆栈。

---

### 6. 特殊目录说明

#### `best/`
-   **说明**：当前全局最优候选快照。
-   **用途**：快速提取当前最优代码，复验冠军候选。

#### `best_viz/`
-   **说明**：面向可视化导出的独立结果目录。
-   **关键文件**：`membrane.svg`（膜孔布局图）、`pareto.png`（Pareto 前沿图）。
-   **用途**：报告插图、方案展示。

    下面为测试75代后的best可视化
 -   <img src="assets/evolve75.svg" alt="进化75代的best排布" width="200">
 -   <img src="assets\pareto.png" alt="best对应的对应5个alpha 评估" width="200">

#### `rollback_backup_*`
-   **说明**：回滚安全备份目录（含 `programs.sqlite` 备份）。
-   **用途**：异常后恢复历史状态。

---
