# ShinkaEvolve Nano-Membrane Fork

这个 fork 是面向 `examples/nano_membrane` 的精简版本，目标是：

- 可在新设备快速安装
- 可复现 nano_membrane 评估与进化流程
- 删除与该任务无关的示例/文档/测试，减少仓库体积与认知负担

## 保留内容

- `shinka/`：运行框架核心代码
- `examples/nano_membrane/`：任务代码与配置
- `pyproject.toml`：依赖与打包配置
- `LICENSE`：许可证

## 环境要求

- Python `>=3.10`（建议 `3.11`）
- 建议使用 `uv`（也可用 `pip`）

## 新设备快速开始

1. 克隆你的 fork

```bash
git clone <your-fork-url>
cd ShinkaEvolve
```

2. 创建虚拟环境并安装

```bash
uv venv --python 3.11
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

uv pip install -e .
```

3. 进入 nano_membrane 示例

```bash
cd examples/nano_membrane
```

4. 先做单点评估（无需 API Key）

```bash
python evaluate.py --program_path initial.py --results_dir results/manual_eval
```

5. 跑异步进化（需要模型 API 配置）

```bash
python run_evo_async.py --config_path shinka_small.yaml
```

## API Key 说明

- 仅执行 `evaluate.py` 时，不需要 LLM API Key。
- 执行 `run_evo_async.py` 时，需要根据 `shinka_small.yaml` 中的模型配置提供对应 API Key。

当前默认模型是 `gpt-5-mini`，请在环境变量中设置 OpenAI Key（例如 `OPENAI_API_KEY`）。

## 结果目录说明

- 运行产物写入 `examples/nano_membrane/results/`
- 该目录通常体积较大，不建议提交到 Git

本仓库已通过 `.gitignore` 忽略 `results/` 与 `__pycache__/`。

## 上游来源

本仓库基于 [SakanaAI/ShinkaEvolve](https://github.com/SakanaAI/ShinkaEvolve) 精简修改，遵循 Apache License 2.0。
