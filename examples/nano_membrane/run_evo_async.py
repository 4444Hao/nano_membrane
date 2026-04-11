#!/usr/bin/env python3
from pathlib import Path
import yaml
import asyncio
import argparse

from shinka.core import AsyncEvolutionRunner, EvolutionConfig
from shinka.database import DatabaseConfig
from shinka.launch import LocalJobConfig

"""
异步进化运行入口。

作用：
1) 读取 YAML 配置；
2) 构建演化配置、数据库配置、任务配置；
3) 启动 AsyncEvolutionRunner 持续迭代。
"""


async def main(config_path: str):
    """按配置启动一次完整的异步进化流程。"""
    config_path = Path(config_path).resolve()
    work_dir = config_path.parent

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 从配置文件反序列化核心配置对象
    evo_config = EvolutionConfig(**config["evo_config"])
    db_config = DatabaseConfig(**config["db_config"])

    # 指定评估程序（evaluate.py）与单任务时间上限
    job_config = LocalJobConfig(
        eval_program_path=str((work_dir / "evaluate.py").resolve()),
        time=config.get("job_time", "00:10:00"),
    )

    # 创建异步进化执行器（负责提案、评估、入库与调度）
    runner = AsyncEvolutionRunner(
        evo_config=evo_config,
        job_config=job_config,
        db_config=db_config,
        max_evaluation_jobs=config["max_evaluation_jobs"],
        max_proposal_jobs=config["max_proposal_jobs"],
        max_db_workers=config["max_db_workers"],
        verbose=True,
    )

    # 进入主循环，直到达到代数/预算等停止条件
    await runner.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_path", default="shinka_small.yaml")
    args = parser.parse_args()

    asyncio.run(main(args.config_path))
