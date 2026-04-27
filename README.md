# ShinkaEvolve Nano-Membrane Fork

![Python](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**<img src="assets\image_177667519376202.png" alt="项目logo" width="18"> 基于大语言模型（LLM）的垂直碳纳米管（VACNT）膜异质孔径排布优化项目**

本仓库旨在利用 **ShinkaEvolve** 的进化算法框架，解决海水淡化 VACNT 膜设计中的核心难题——**非等圆圆形打包问题（Non-Equal Circle Packing），实现通量与截留率的多目标优化**。

### 💡 核心逻辑
传统膜分离受限于“渗透性-选择性”权衡。本项目引入**动态振荡范式**，通过微小机械振荡激活大孔径（3.5nm）能力，并设计 **1nm（高选择性）至3.5nm（高通量）的6种类型的异质孔协同**。在此前提下，本代码库负责在安全距离约束下，寻找最大化膜功能利用效率的最优口径排布方案。

---

## 📂 仓库结构

本仓库已对上游源码进行精简，专注于 `nano_membrane` 场景：

*   `shinka/` - ShinkaEvolve 运行框架核心代码
*   `examples/nano_membrane/` - **核心工作区**：包含 VACNT 膜优化的任务定义、配置与评估脚本
*   `pyproject.toml` - 依赖配置
*   `LICENSE` - Apache License 2.0

---

## 🎏  为什么选择 ShinkaEvolve 框架？

纳米膜布局是一个带硬约束的多目标优化问题（渗透性 P vs 截留率 R）。传统做法是让 AI 一次性生成求解器代码，但这种方式缺乏迭代反馈，难以持续改进。ShinkaEvolve 提供了**程序级进化**方案，将算法本身作为可进化的个体，通过 LLM 驱动的变异与真实评估驱动的筛选，自动在算法空间中进行搜索。

### 框架运作机制（以本问题为例）

1. **初始化**  
   提供一个初始求解器（`initial.py`），其中 `EVOLVE-BLOCK` 标记了可编辑区域。

2. **异步进化循环**  
   - **采样**：从数据库中选择父代程序及若干高绩效“灵感”程序。  
   - **生成补丁**：LLM 生成 `diff`（局部修改）或 `full`（整体重写）补丁，仅作用于 `EVOLVE-BLOCK` 内。  
   - **评估**：自动运行 5 次（不同 α 权重），计算 Pareto 前沿的超体积与可行率，得到 `combined_score`。  
   - **入库与选择**：存储代码、得分、补丁类型、父代关系等，并更新最优快照。  
   - **新颖性保护**：通过嵌入相似度 + LLM 判定，避免早熟收敛。  
   - **多岛与元学习**（可选）：保持多样性，并定期总结成功/失败模式注入后续提示。

3. **停止条件**  
   达到预设代数（如 90 代）或累计 API 成本上限（如 $4.0）。

### 与“直接让 AI 生成代码”的核心优势

| 维度 | 直接 AI 生成 | ShinkaEvolve 程序级进化 |
|------|--------------|--------------------------|
| **迭代性** | 一次性生成，无法根据运行结果改进 | 多轮“生成→评估→筛选→变异”，持续优化 |
| **探索能力** | 受限于单次 prompt 的随机性 | 通过父代选择与变异算子探索算法结构，可产生非平凡的新策略 |
| **反馈利用** | 只能人工介入 | 自动收集 metrics 与错误日志，失败程序作为“修复目标”，成功模式作为灵感 |
| **鲁棒性** | 可能违反约束或数值不稳定 | 多次不同权重运行 + 可行性惩罚，进化压力直接导向高可行率 + 高质量前沿 |
| **可复现性** | 难以追溯版本 | 数据库完整记录每代代码、得分、diff、父代关系，可回溯最佳路径 |
| **工程效率** | 需人工反复改写 prompt | 一次配置，自动运行数百代，支持并行评估 |

### 实际效果（纳米膜案例）

- **初始程序**（`initial.py`）：随机放置 + 模拟退火，`combined_score` ≈ 0.51  
- **进化后最优程序**（第 74 代）：算法突变为“多尺度网格 + 最大间隙贪心 + 局部细化”，`combined_score` ≈ **0.84**，且可行性保持 **100%**  
- **结构创新**：LLM 在观察到前代失败模式后，自主生成 `full` 补丁，完成了算法范式的迁移——这超出了单纯调参或一次性生成的能力范围。

### 结论

ShinkaEvolve 非常适合求解器可塑性强、约束复杂、多目标评价的工程优化问题。它把“编写算法”转化为一个可进化的对象，利用 LLM 作为变异算子，用真实评估作为适应度函数，在算法空间中进行系统性搜索，最终获得远超初始方案的性能与鲁棒性。

---

## ⚙️ 快速开始

### 1. 环境准备
建议使用 Python 3.11 环境。

```bash
# 1. 克隆仓库
git clone https://github.com/4444Hao/nano_membrane.git
cd nano_membrane

# 2. 推荐使用 uv（也可用 pip，见下方）
uv venv --python 3.11

# Windows（PowerShell / VSCode 集成终端）:
.venv\Scripts\activate
# Linux / macOS:
# source .venv/bin/activate

# 3. 安装依赖（必须在仓库根目录执行，即含 pyproject.toml 的那一层）
uv pip install -e .
```

> **如果没有安装 uv，用 pip 替代：**
> ```powershell
> python -m venv .venv
> .venv\Scripts\activate
> pip install -e .
> ```

### 2. 运行单点评估 (Debug)
无需 API Key，用于验证初始设计方案的适应度。

```bash
# 先切换到工作目录
cd examples/nano_membrane

python evaluate.py --program_path initial.py --results_dir results/manual_eval
```

### 3. 启动 AI 进化 (Evolution)
让 LLM 开始寻找最优的孔隙排布方案。

**第一步：配置 API Key**

```powershell
# Windows PowerShell / VSCode 集成终端
$env:OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxx"
```

```bash
# Linux / macOS
export OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxx"
```

**第二步：切换目录并启动进化**

```bash
cd examples/nano_membrane

python run_evo_async.py --config_path shinka_small.yaml
```

> **注意**：默认配置使用 OpenAI 模型（gpt-5-mini）。
> 若使用其他模型，请修改 `shinka_small.yaml` 中的 `llm_models` 字段（需符合上游支持的模型型号）。

---

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

#### 下面为测试的best_viz/文件内容（75代）： 

**膜孔布局图**  
<img src="assets/evolve75.svg" alt="进化75代的best排布" width="200">

**Pareto 前沿图**   
<img src="assets\pareto.png" alt="best对应的对应5个alpha 评估" width="200">

### 2. 官方 WebUI 实时监控
在运行进化任务（`run_evo_async.py`）的同时，你可以启动官方的 WebUI 工具，在浏览器中实时查看进化进度、种群分布和最优解的图形化展示。

**操作步骤：**
1.  保持进化脚本运行。
2.  打开一个新的终端窗口。
3.  执行以下命令启动可视化服务：

```bash
python -m shinka.webui.visualization --port 8888 --open
```

#### 进化过程监控示例（75代）
以下为典型监控结果可视化：

**进化树结构**  
<img src="assets/gentree.jpeg" alt="进化75代的树状结构" width="400">

**Score分析**  
<div style="display: flex; gap: 10px; margin-top: 10px">
  <img src="assets/scorerank.png" alt="进化75代的适应度排名" width="200">
  <img src="assets/Evolvescore.png" alt="进化75代的适应度变化趋势" width="200">
</div>

> **左图说明**：`scorerank.png` - 进化中Score排名  
> **右图说明**：`Evolvescore.png` - 进化过程Score的变化

> **建议**：在运行进化任务时同时启动监控，以便及时调整参数或处理异常。

---

## 📊 评分与进化策略详解

本节详细说明本项目中**膜性能评估的数学模型**、**进化档案管理**以及**续跑配置**，帮助理解 `combined_score` 的计算逻辑和参数调优依据。

### 1. 计算层面：从孔属性到综合得分

#### 🧱 第一层：每个孔的物理属性
根据孔径 `d` 查表 `HOLE_TYPES` 得到 `(P_type, R_type)`：

| 孔径 d (nm) | P_type (渗透性因子) | R_type (截留率, %) | 说明 |
|:-----------:|:-------------------:|:------------------:|:-----|
| 1.0         | 143                 | 100.0              | 最小孔：水流慢，盐完全挡住 |
| 1.5         | 778                 | 99.6               | |
| 2.0         | 815                 | 99.8               | |
| 2.5         | 1048                | 99.5               | |
| 3.0         | 1435                | 96.8               | |
| 3.5         | 1437                | 94.3               | 最大孔：水流快，盐有点漏 |

#### 🔢 第二层：整张膜的原始值
- **原始渗透性**  
  `P_raw = (1.64 × Σ(面积_i × P_type_i)) / 100`  
  面积加权后除以膜面积归一。

- **原始截留率**  
  `R_raw = Σ(面积_i × R_type_i) / Σ(面积_i)`  
  纯面积加权平均。

#### 📏 第三层：归一化到 [0,1]
- **Pn（归一化渗透性）**  
  - 当 `P_raw ≤ 600` 时：线性增长到 0.8  
  - 当 `600 < P_raw ≤ 1100` 时：缓慢增长到 1.0  
  - 拐点设计：超过 600 后收益递减，避免只堆大孔。

- **Rn（归一化截留率）**  
  `Rn = (R_raw - 96) / (100 - 96)`  
  工程下限为 96%，低于 96 直接得 0。

#### ⚖️ 第四层：单次运行得分
`score = α × Pn + (1 - α) × Rn`

α 按 5 个值轮流：`[0.2, 0.35, 0.5, 0.65, 0.8]`

| α 值 | 侧重方向     |
|------|--------------|
| 0.2  | 偏重 R（截留率优先） |
| 0.35 |              |
| 0.5  | 均衡         |
| 0.65 |              |
| 0.8  | 偏重 P（渗透性优先） |

#### 🏆 第五层：5 次运行聚合 → `combined_score`
1. 5 次运行得到 5 个 `(Pn, Rn)` 点。  
2. 找出**非支配前沿**（Pareto前沿）：没有任何一个点在两个维度上同时比它更好。  
3. 计算**超体积（HV）**：设定一个参考点（最差情况），HV = Pareto 前沿与参考点之间围成的面积。  
   - HV 越大，说明 P 和 R 的折中方案越好（前沿越靠右上角）。  
   - **为什么用 HV 而不是平均分？**  

   | 方案 | Pn   | Rn   | 平均分 | 问题 |
   |------|------|------|--------|------|
   | A    | 0.95 | 0.60 | 0.775  | Rn 对应 R=98.4%，低于工程下限，偏科严重 |
   | B    | 0.80 | 0.85 | 0.825  | 均衡且都在可行域内 |

   平均分看 B 更好，但 A 实际上不可行。HV 会惩罚“一条腿长一条腿短”的情况——极端偏科的前沿面积反而小。

4. 最终综合分：  
   `combined_score = HV × feasible_rate`  
   - `feasible_rate = 可行运行次数 / 总运行次数`  
   - 不稳定的程序在实际部署中没有价值，因此乘上可行率。

### 2. 档案（Archive）配置：精英与多样性兼顾

不同总代数需要调整 `archive_size` 和 `elite_selection_ratio`：

- **`archive_size`**：档案保留的优秀程序总数（如 40 个名额）  
  - `elite_selection_ratio = 0.5` → 20 个名额：按 `combined_score` 从高到低保留（精英）  
  - 剩余 50%（20 个名额）：按代码嵌入向量的**多样性**保留（与已有档案里程序“最不像”的程序优先入选）

→ 档案里同时有高分程序和代码风格独特的程序，**不是纯精英制**。

### 3. 续跑（Resume Evolution）配置示例

框架支持断点续跑，`programs.sqlite` 和 `bandit_state.pkl` 会保留已有进化历史，直接修改 YAML 重新运行即可继承。

**场景**：从 30 代续跑到 60 代，需要修改以下 3 个值：

```yaml
db_config:
  archive_size: 40            # 25 → 40（60 代程序变多，扩大档案容量）
  elite_selection_ratio: 0.4  # 0.5 → 0.4（积累更多，适当降低精英比例）

evo_config:
  num_generations: 60         # 30 → 60（告诉框架目标总代数）
  max_api_costs: 4.0          # 2.0 → 4.0（预算翻倍）
```

**不需要修改的**：
- `results_dir`：保持相同路径，框架自动识别已有的 `programs.sqlite` 续跑  
- `init_program_path`：续跑时框架不会重新初始化，此参数被忽略  
- 其他所有参数保持不变

> **注意**：`num_generations: 60` 是**总代数**，不是“再跑 30 代”。  
> 框架从数据库读取当前已完成的代数，如果已经跑了 30 代，设为 60 就会再跑 30 代；设为 30 则框架认为目标已达成，直接退出。

---

## 📊 结果说明

*   **输出目录**：`examples/nano_membrane/results/`
*   **预期产出**：
    *   进化过程中生成的最优孔隙排布代码（best文件）。
    *   对应的适应度评分（基于单位面积过滤率与速率的数学模型预测）。
    *   *后续步骤*：将此处生成的最优坐标导入 LAMMPS/GROMACS 进行分子动力学模拟验证。

---

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

---

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
gen_<k>/
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

#### `rollback_backup_*`
-   **说明**：回滚安全备份目录（含 `programs.sqlite` 备份）。
-   **用途**：异常后恢复历史状态。

---

## 🏛️ 上游来源
本项目基于 <SakanaAI/ShinkaEvolve> 修改，遵循 Apache License 2.0.
