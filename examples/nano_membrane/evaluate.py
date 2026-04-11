import os
import argparse
import pickle
import json
from datetime import datetime
from math import pi, sqrt
from collections import Counter
from typing import Dict, List, Tuple, Any

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from shinka.core import run_shinka_eval

"""
纳米膜布局评估器。

职责：
1) 校验几何可行性；
2) 计算单次运行的 P/R/孔隙率与标量分数；
3) 汇总多次运行结果，输出最终 combined_score。
"""

# --------------------------- 几何与评分常量 ---------------------------
DOMAIN_SIZE = 10.0
MIN_SPACING = 0.5
ATOL = 1e-4
C = 1.64
EPS = 1e-6
# 避免权重参数取端点（0/1），降低单目标退化风险
ALPHA_SCHEDULE = [0.2, 0.35, 0.5, 0.65, 0.8]

HOLE_TYPES = {
    1.0: (143.94, 100.0),
    1.5: (778.82, 99.6),
    2.0: (815.70, 99.8),
    2.5: (1048.16, 99.5),
    3.0: (1435.74, 96.8),
    3.5: (1437.24, 94.3),
}

VALID_DIAMETERS = sorted(HOLE_TYPES.keys())

# 归一化参数
P_KNEE = 600.0
P_CAP = 1100.0
R_FLOOR = 96.0

def circle_area(d: float) -> float:
    """计算孔径 d 对应的圆孔面积。"""
    return pi * (d / 2.0) ** 2


def normalize_metrics(P: float, R: float) -> Tuple[float, float]:
    """将原始 P、R 映射到 [0,1]，用于后续统一评分。"""
    # 拐点前保持高灵敏度，拐点后降低增益
    p = max(0.0, float(P))
    knee = max(1e-9, float(P_KNEE))
    cap = max(knee + 1e-9, float(P_CAP))
    if p <= knee:
        Pn = 0.8 * (p / knee)
    else:
        p_eff = min(p, cap)
        Pn = 0.8 + 0.2 * ((p_eff - knee) / (cap - knee))
    Pn = max(0.0, min(1.0, Pn))

    # 用工程下限对过低 R 进行惩罚
    denom = max(100.0 - float(R_FLOOR), 1e-9)
    Rn = (float(R) - float(R_FLOOR)) / denom
    Rn = max(0.0, min(1.0, Rn))
    return Pn, Rn


def compute_score_components(P: float, R: float, alpha: float = 0.5) -> Dict[str, float]:
    """
    计算单次运行的分数组件。

    返回值包含：
    - score: 总分
    - Pn/Rn: 归一化指标
    - score_p/score_r: 两个目标各自贡献
    """
    # 基础目标：同时提升通量与截留
    # 跨多次运行采样权重参数，用于描绘帕累托权衡关系
    Pn, Rn = normalize_metrics(P, R)
    alpha = max(0.0, min(1.0, float(alpha)))
    score_p = alpha * Pn
    score_r = (1.0 - alpha) * Rn
    score_pr = score_p + score_r
    score = score_pr
    base_score = score_pr
    return {
        "score": float(max(0.0, min(1.0, score))),
        "base_score": float(max(0.0, min(1.0, base_score))),
        "score_pr": float(max(0.0, min(1.0, score_pr))),
        "Pn": float(Pn),
        "Rn": float(Rn),
        "alpha": float(alpha),
        "pr_core": float(score_pr),
        "score_p": float(score_p),
        "score_r": float(score_r),
    }


def validate_solution(circles: List[Tuple[float, float, float]]) -> Tuple[bool, str]:
    """
    检查布局是否合法：
    - 孔径是否合法
    - 是否重复坐标
    - 是否越界
    - 是否违反最小间距
    """
    if not circles:
        return False, "No circles"

    seen = set()

    for i, (x, y, d) in enumerate(circles):
        if d not in VALID_DIAMETERS:
            return False, "Invalid diameter"

        key = (round(x, 2), round(y, 2))
        if key in seen:
            return False, "Duplicate coordinate"
        seen.add(key)

        r = d / 2.0
        if not (r - ATOL <= x <= DOMAIN_SIZE - r + ATOL):
            return False, "Boundary"
        if not (r - ATOL <= y <= DOMAIN_SIZE - r + ATOL):
            return False, "Boundary"

        for j in range(i + 1, len(circles)):
            x2, y2, d2 = circles[j]
            dist = sqrt((x - x2) ** 2 + (y - y2) ** 2)
            min_dist = (d + d2) / 2.0 + MIN_SPACING
            if dist < min_dist - ATOL:
                return False, "Spacing violation"

    return True, ""


def compute_metrics(circles: List[Tuple[float, float, float]]) -> Dict[str, Any]:
    """
    计算布局的详细指标字典：
    包含 P_raw、R_raw、孔隙率、孔径分布等。
    """
    total_area = 0.0
    p_area_sum = 0.0
    r_area_sum = 0.0
    type_count: Dict[float, int] = {}
    type_area: Dict[float, float] = {}

    for x, y, d in circles:
        if d not in HOLE_TYPES:
            raise ValueError(f"Invalid diameter {d}")

        p_val, r_val = HOLE_TYPES[d]
        area = circle_area(d)
        # 使用面积加权公式计算 P 和 R
        p_area = area * p_val
        r_area = area * r_val

        total_area += area
        p_area_sum += p_area
        r_area_sum += r_area
        type_count[d] = type_count.get(d, 0) + 1
        type_area[d] = type_area.get(d, 0.0) + area

    if total_area <= 0:
        raise ValueError("Total hole area must be positive")

    # 基础定义
    # P 按膜总面积归一，而不是按孔总面积归一
    P_raw = C * p_area_sum / max(DOMAIN_SIZE * DOMAIN_SIZE, 1e-12)
    R_raw = max(0.0, min(100.0, r_area_sum / max(total_area, 1e-12)))
    porosity = total_area / (DOMAIN_SIZE * DOMAIN_SIZE)
    area_frac_by_type = {d: (a / total_area) for d, a in type_area.items()}

    return {
        "P_raw": float(P_raw),
        "R_raw": float(R_raw),
        "P": round(P_raw, 2),
        "R": round(R_raw, 1),
        "A_total": round(total_area, 6),
        "porosity": round(porosity, 6),
        "N": len(circles),
        "num_types": len(type_count),
        "holes_by_type": dict(sorted(type_count.items())),
        "area_by_type": {k: round(v, 6) for k, v in dict(sorted(type_area.items())).items()},
        "area_frac_by_type": {k: round(v, 6) for k, v in dict(sorted(area_frac_by_type.items())).items()},
        "circles": circles,
    }


def dominates(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """判断 a 是否帕累托支配 b（至少不差且有一项更好）。"""
    beq = (a["P_raw"] >= b["P_raw"] - EPS and a["R_raw"] >= b["R_raw"] - EPS)
    better = (a["P_raw"] > b["P_raw"] + EPS or a["R_raw"] > b["R_raw"] + EPS)
    return beq and better


def update_pareto(results_dir: str, solutions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """将本轮可行解并入历史 Pareto 档案，并去除被支配解。"""
    path = os.path.join(results_dir, "pareto_archive.pkl")

    if os.path.exists(path):
        with open(path, "rb") as f:
            archive = pickle.load(f)
    else:
        archive = []

    for solution in solutions:
        new_archive = []
        dominated_by_existing = False
        for s in archive:
            if dominates(solution, s):
                continue
            if dominates(s, solution):
                dominated_by_existing = True
                break
            new_archive.append(s)

        if dominated_by_existing:
            continue
        new_archive.append(solution)
        archive = new_archive

    with open(path, "wb") as f:
        pickle.dump(archive, f)

    return archive


def non_dominated_set(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """从记录集合中提取当前非支配解集合。"""
    nd = []
    for cand in records:
        dominated = False
        kept = []
        for old in nd:
            if dominates(old, cand):
                dominated = True
                break
            if not dominates(cand, old):
                kept.append(old)
        if not dominated:
            kept.append(cand)
            nd = kept
    return nd


def pareto_hypervolume(records: List[Dict[str, Any]]) -> float:
    """
    计算归一化后的二维超体积（Pn-Rn 平面）。
    数值越大表示“Pareto 前沿覆盖质量”越好。
    """
    if not records:
        return 0.0
    nd = non_dominated_set(records)
    pts = []
    for r in nd:
        pn, rn = normalize_metrics(r["P_raw"], r["R_raw"])
        pts.append((pn, rn))
    pts.sort(key=lambda x: x[0])

    hv = 0.0
    prev_x = 0.0
    suffix_best_y = [0.0] * len(pts)
    suffix_best_y[-1] = pts[-1][1]
    for i in range(len(pts) - 2, -1, -1):
        suffix_best_y[i] = max(pts[i][1], suffix_best_y[i + 1])
    for i, (x, _) in enumerate(pts):
        hv += max(0.0, x - prev_x) * suffix_best_y[i]
        prev_x = x
    return float(max(0.0, min(1.0, hv)))


def export_svg(results_dir: str, circles: List[Tuple[float, float, float]], name: str = "membrane.svg") -> None:
    """将最佳布局导出为 SVG 图。"""
    size = 600
    scale = size / DOMAIN_SIZE
    path = os.path.join(results_dir, name)

    with open(path, "w", encoding="utf-8") as f:
        f.write(f'<svg width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">')
        f.write(f'<rect x="0" y="0" width="{size}" height="{size}" fill="white" stroke="black"/>')

        for x, y, d in circles:
            cx = x * scale
            cy = size - y * scale
            r = (d / 2.0) * scale
            f.write(
                f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="steelblue" '
                f'stroke="black" fill-opacity="0.60"/>'
            )

        f.write("</svg>")


def plot_pareto(results_dir: str, archive: List[Dict[str, Any]]) -> None:
    """绘制并保存 P-R 平面的 Pareto 散点图。"""
    if not archive:
        return

    pts = sorted((s["P"], s["R"]) for s in archive)
    xs = [p for p, _ in pts]
    ys = [r for _, r in pts]

    os.makedirs(os.path.join(results_dir, "figures"), exist_ok=True)

    plt.figure(figsize=(6, 5))
    plt.scatter(xs, ys)
    plt.plot(xs, ys)
    plt.xlabel("Permeability P")
    plt.ylabel("Rejection R")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, "figures", "pareto.png"), dpi=300)
    plt.close()


def save_run_summary(results_dir: str, payload: Dict[str, Any]) -> None:
    """保存每次运行的完整摘要 JSON。"""
    path = os.path.join(results_dir, "run_summary.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def aggregate_fn(results: List[Any], results_dir: str, save_artifacts: str = "none") -> Dict[str, Any]:
    """
    多次运行汇总入口（Shinka 会调用此函数）：
    1) 逐条校验可行性并计算单次指标；
    2) 统计 Pareto 前沿与超体积；
    3) 输出最终 combined_score。
    """
    run_records = []
    failure_counter = Counter()
    feasible_metrics = []

    for idx, raw_result in enumerate(results):
        if isinstance(raw_result, dict) and "circles" in raw_result:
            circles = raw_result.get("circles", [])
            alpha = float(raw_result.get("alpha", 0.5))
        else:
            circles = raw_result
            alpha = 0.5

        valid, msg = validate_solution(circles)
        if not valid:
            failure_counter[msg] += 1
            run_records.append(
                {
                    "run_id": idx,
                    "valid": False,
                    "error": msg,
                    "alpha": round(alpha, 3),
                }
            )
            continue

        metrics = compute_metrics(circles)
        components = compute_score_components(
            metrics["P_raw"],
            metrics["R_raw"],
            alpha=alpha,
        )
        score = components["score"]

        record = {
            "run_id": idx,
            "valid": True,
            "alpha": round(components.get("alpha", alpha), 3),
            "score": round(score, 6),
            "score_pr": round(components.get("score_pr", 0.0), 6),
            "base_score": round(components.get("base_score", 0.0), 6),
            "score_core": round(components["pr_core"], 6),
            "score_Pn": round(components["Pn"], 6),
            "score_Rn": round(components.get("Rn", 0.0), 6),
            "score_p": round(components.get("score_p", 0.0), 6),
            "score_r": round(components.get("score_r", 0.0), 6),
            **metrics,
        }
        run_records.append(record)
        feasible_metrics.append(record)

    summary_payload = {
        "timestamp_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "num_runs": len(results),
        "num_feasible": len(feasible_metrics),
        "feasible_rate": 0.0 if len(results) == 0 else len(feasible_metrics) / len(results),
        "failure_counter": dict(failure_counter),
        "runs": run_records,
    }
    save_run_summary(results_dir, summary_payload)

    if not feasible_metrics:
        return {
            "combined_score": 0.0,
            "error": f"No feasible runs. Failure stats: {dict(failure_counter)}",
            "private": summary_payload,
        }

    best = max(
        feasible_metrics,
        key=lambda x: (
            x["score"],
            x["R_raw"],
            x["porosity"],
            x["P_raw"],
            x["num_types"],
            x["N"],
        ),
    )
    mean_score = float(np.mean([r["score"] for r in feasible_metrics]))
    score_std = float(np.std([r["score"] for r in feasible_metrics])) if feasible_metrics else 0.0
    front = non_dominated_set(feasible_metrics)
    hv = pareto_hypervolume(feasible_metrics)
    feasible_rate = summary_payload["feasible_rate"]
    # 最终总分：前沿质量（hv）乘以可行率（feasible_rate）
    robust_score = max(0.0, min(1.0, hv * feasible_rate))

    archive_size = 0
    if save_artifacts == "all":
        archive = update_pareto(results_dir, feasible_metrics)
        export_svg(results_dir, best["circles"])
        plot_pareto(results_dir, archive)
        archive_size = len(archive)
    elif save_artifacts == "best_only":
        export_svg(results_dir, best["circles"])

    return {
        "combined_score": round(robust_score, 6),
        "public": {
            "best_P": best["P"],
            "best_R": best["R"],
            "best_N": best["N"],
            "best_porosity": best["porosity"],
            "best_num_types": best["num_types"],
            "feasible_rate": round(summary_payload["feasible_rate"], 3),
            "pareto_count": len(front),
            "hypervolume_norm": round(hv, 6),
            "mean_scalar_score": round(mean_score, 6),
        },
        "private": {
            "best": best,
            "score_std_penalty": 0.0,
            "robust_combined_score": round(robust_score, 6),
            "combined_score_mean": round(mean_score, 6),
            "mean_feasible_score": round(mean_score, 6),
            "std_feasible_score": round(score_std, 6),
            "pareto_front_current_run": front,
            "hypervolume_norm": round(hv, 6),
            "failure_counter": dict(failure_counter),
            "archive_size": archive_size,
            "runs": run_records,
        },
    }


def get_experiment_kwargs(run_index: int) -> Dict[str, Any]:
    """为第 run_index 次运行生成参数（seed + alpha）。"""
    alpha = ALPHA_SCHEDULE[run_index % len(ALPHA_SCHEDULE)]
    return {"seed": run_index + 1, "alpha": alpha}


def main(
    program_path: str,
    results_dir: str,
    num_runs: int,
    run_workers: int,
    save_artifacts: str = "none",
) -> None:
    """命令行入口：执行评估并打印汇总指标。"""
    os.makedirs(results_dir, exist_ok=True)

    metrics, correct, error = run_shinka_eval(
        program_path=program_path,
        results_dir=results_dir,
        experiment_fn_name="run_experiment",
        num_runs=num_runs,
        get_experiment_kwargs=get_experiment_kwargs,
        validate_fn=None,
        aggregate_metrics_fn=lambda r: aggregate_fn(r, results_dir, save_artifacts=save_artifacts),
        run_workers=run_workers,
    )

    print(metrics)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--program_path", default="initial.py")
    parser.add_argument("--results_dir", default="results")
    parser.add_argument("--num_runs", type=int, default=5)
    parser.add_argument("--run_workers", type=int, default=1)
    parser.add_argument(
        "--save_artifacts",
        choices=["none", "best_only", "all"],
        default="none",
        help="Artifact output mode: none (fast), best_only (save membrane.svg), all (svg + pareto archive + plot).",
    )

    args = parser.parse_args()
    main(
        args.program_path,
        args.results_dir,
        args.num_runs,
        args.run_workers,
        save_artifacts=args.save_artifacts,
    )
