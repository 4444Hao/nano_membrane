"""
运行指定 gen 或 best 的 main.py，获取单个排布并计算评分。

用法：
  python run_single.py                      # 默认运行 best
  python run_single.py --gen 5              # 运行 gen_5
  python run_single.py --gen 5 --alpha 0.8  # 指定 alpha
  python run_single.py --gen 5 --seed 123   # 指定随机种子
"""
import sys
import os
import argparse
import importlib.util
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evaluate import (
    validate_solution,
    compute_metrics,
    compute_score_components,
    diagnose_violations
)


def load_main(gen):
    if gen == "best":
        path = os.path.join("results", "research_run", "best", "main.py")
    else:
        path = os.path.join("results", "research_run", f"gen_{gen}", "main.py")

    if not os.path.exists(path):
        print(f"错误：找不到文件 {path}")
        sys.exit(1)

    spec = importlib.util.spec_from_file_location("main", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gen", default="best", help="代数编号，如 5、12，或 best（默认）")
    parser.add_argument("--alpha", type=float, default=0.5, help="目标权重，0=纯截留，1=纯渗透（默认 0.5）")
    parser.add_argument("--seed", type=int, default=42, help="随机种子（默认 42）")
    args = parser.parse_args()

    # 运行算法获取排布
    module = load_main(args.gen)
    result = module.run_experiment(seed=args.seed, alpha=args.alpha)

    circles = result["circles"]
    alpha = result["alpha"]

    print(f"\n{'='*60}")
    print(f"来源：gen_{args.gen}/main.py  |  alpha={alpha}  |  seed={args.seed}")
    print(f"{'='*60}")

    # 验证可行性
    is_valid, error_msg = validate_solution(circles)

    if not is_valid:
        print(f"\n❌ 排布不可行：{error_msg}")
        diag = diagnose_violations(circles)
        print(f"\n违规详情：")
        for v in diag.get("violations_summary", []):
            print(f"  - {v}")
        print(f"\n提示：{diag.get('hint', '')}")
        return

    # 计算指标
    metrics = compute_metrics(circles)
    score_components = compute_score_components(
        metrics["P_raw"],
        metrics["R_raw"],
        alpha=alpha
    )

    # 输出结果
    print(f"\n✓ 排布可行")
    print(f"\n【核心指标】")
    print(f"  渗透性 P:  {metrics['P']:>8.2f}")
    print(f"  截留率 R:  {metrics['R']:>8.1f}%")
    print(f"  孔隙率:    {metrics['porosity']:>8.2%}")
    print(f"  孔数:      {metrics['N']:>8d}")
    print(f"  孔径种类:  {metrics['num_types']:>8d}")

    print(f"\n【归一化指标】")
    print(f"  Pn (归一化渗透性): {score_components['Pn']:.6f}")
    print(f"  Rn (归一化截留率): {score_components['Rn']:.6f}")

    print(f"\n【评分】")
    print(f"  Alpha:       {alpha:.2f}")
    print(f"  Score:       {score_components['score']:.6f}")
    print(f"  Score_P:     {score_components['score_p']:.6f}  (alpha × Pn)")
    print(f"  Score_R:     {score_components['score_r']:.6f}  ((1-alpha) × Rn)")

    print(f"\n【孔径分布】")
    for d, count in sorted(metrics['holes_by_type'].items()):
        area_frac = metrics['area_frac_by_type'][d]
        print(f"  直径 {d}: {count:2d} 个  (面积占比 {area_frac:.1%})")

    print(f"\n【孔径坐标】")
    for i, (x, y, d) in enumerate(circles, 1):
        print(f"  {i:2d}. ({x:5.2f}, {y:5.2f}, d={d})")

    # 保存完整数据
    output_dir = os.path.join("results", "single_layouts")
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"layout_gen{args.gen}_alpha{alpha}_seed{args.seed}.json")

    output_data = {
        "gen": args.gen,
        "alpha": alpha,
        "seed": args.seed,
        "valid": is_valid,
        "num_holes": len(circles),
        "circles": circles,
        "metrics": {
            "P": metrics["P"],
            "R": metrics["R"],
            "P_raw": metrics["P_raw"],
            "R_raw": metrics["R_raw"],
            "porosity": metrics["porosity"],
            "total_area": metrics["A_total"],
            "num_types": metrics["num_types"],
            "holes_by_type": metrics["holes_by_type"],
            "area_frac_by_type": metrics["area_frac_by_type"]
        },
        "scores": {
            "score": score_components["score"],
            "Pn": score_components["Pn"],
            "Rn": score_components["Rn"],
            "score_p": score_components["score_p"],
            "score_r": score_components["score_r"]
        }
    }

    with open(out_path, "w") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"✓ 已保存到 {out_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
