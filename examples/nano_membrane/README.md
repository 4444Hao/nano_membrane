# Nano Membrane 示例

使用 ShinkaEvolve 优化 `10 x 10` 二维膜区域内的纳米孔布局问题。

## 运行前提

- 已安装 Python 环境，并在仓库根目录执行过 `uv pip install -e .` 安装 `shinka`
- 工作目录：`examples/nano_membrane`

## 任务目标

- 在膜区域中放置离散孔径圆孔 `{1.0, 1.5, 2.0, 2.5, 3.0, 3.5}`
- 满足严格几何约束：
  - 圆孔必须完全位于边界内
  - 任意两孔最小间距为 `0.5`
  - 不允许重复坐标
- 在多权重条件下优化渗透性-截留率折中

## 核心文件

- `initial.py`：初始求解器（仅 `EVOLVE-BLOCK` 区域用于进化）
- `evaluate.py`：合法性校验、指标计算、聚合评分
- `run_evo_async.py`：异步进化入口
- `shinka_small.yaml`：默认配置
- `results/`：候选程序、日志、数据库与产物目录

## 评分机制

对每个候选程序：

- 默认执行 `num_runs=5`
- 每次运行使用一个 `alpha`，序列为 `[0.2, 0.35, 0.5, 0.65, 0.8]`
- 单次分数：
  - `score = alpha * Pn + (1 - alpha) * Rn`
- 最终分数：
  - `combined_score = hypervolume_norm * feasible_rate`

解释：

- `hypervolume_norm`：衡量 `(P, R)` 平面上 Pareto 前沿质量
- `feasible_rate`：衡量多次运行的可行性与稳定性

## 快速开始

在仓库根目录执行：

```bash
cd examples/nano_membrane
```

启动异步进化（推荐）：

```bash
python run_evo_async.py --config_path shinka_small.yaml
```

仅评估单个程序（不进化）：

```bash
python evaluate.py --program_path initial.py --results_dir results/manual_eval
```

评估某一代候选程序：

```bash
python evaluate.py --program_path results/membrane_run/gen_74/main.py --results_dir results/gen_74_eval
```

导出可视化产物（`none | best_only | all`）：

```bash
python evaluate.py --program_path initial.py --results_dir results/manual_eval_artifacts --save_artifacts all
```

基于当前 best 候选重新生成完整可视化：

```bash
python evaluate.py --program_path results/membrane_run/best/main.py --results_dir results/membrane_run/best_viz --save_artifacts all
```

## 默认配置（`shinka_small.yaml`）

- `num_generations: 90`
- `max_api_costs: 4.0`
- `llm_models: ["gpt-5-mini"]`
- `patch_types: [full, diff]`
- `results_dir: results/membrane_run`
- `max_evaluation_jobs: 1`
- `max_proposal_jobs: 1`
- `max_db_workers: 2`

## 输出结构

每代常见目录：

- `results/membrane_run/gen_<k>/main.py`
- `results/membrane_run/gen_<k>/results/metrics.json`
- `results/membrane_run/gen_<k>/results/run_summary.json`
- `results/membrane_run/gen_<k>/results/correct.json`
- `results/membrane_run/gen_<k>/attempts/`

全局常见产物：

- `results/membrane_run/evolution_run.log`
- `results/membrane_run/programs.sqlite`
- `results/membrane_run/best/`

当评估使用 `save_artifacts=all` 时，还会生成：

- `membrane.svg`
- `pareto_archive.pkl`
- `figures/pareto.png`

## 当前本地基线快照

来自现有本地运行结果：

- 来源：`results/membrane_run/best/results/metrics.json`
- 时间戳：`2026-04-04T11:34:30Z`
- `combined_score = 0.844544`
- `feasible_rate = 1.0`
- `hypervolume_norm = 0.844544`
- `best_P = 629.59`，`best_R = 99.6`

该值可作为你 fork 的复现参考，不是理论上限。

## 推荐使用流程

1. 先完整跑一轮，建立初始 Pareto 候选集
2. 不只看 `best/`，同时比较多个前沿候选
3. 对入围候选做更多轮次与固定种子复评
4. 再进入下游仿真或实验验证

## 说明

- 若要在既有 `results_dir` 上续跑，建议先备份目录
- 调试时请结合 `metrics.json` 与 `evolution_run.log`
- 若某代出现格式或补丁失败，可查看对应 `attempts/` 子目录
