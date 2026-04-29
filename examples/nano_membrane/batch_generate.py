"""
批量生成多个 seed 的排布，找到最优方案

用法：
  python batch_generate.py                    # 默认：best, alpha=0.5, seed 1-20
  python batch_generate.py --count 50         # 生成 50 个不同 seed
  python batch_generate.py --gen 22 --count 30
"""
import os
import sys
import argparse
import json
import importlib.util
from evaluate import validate_solution, compute_metrics, compute_score_components


def load_main(gen):
    if gen == "best":
        path = os.path.join("results", "membrane_run", "best", "main.py")
    else:
        path = os.path.join("results", "membrane_run", f"gen_{gen}", "main.py")

    if not os.path.exists(path):
        print(f"错误：找不到文件 {path}")
        sys.exit(1)

    spec = importlib.util.spec_from_file_location("main", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_single(module, gen, alpha, seed):
    """运行单次并返回结果"""
    result = module.run_experiment(seed=seed, alpha=alpha)
    circles = result["circles"]
    alpha_actual = result["alpha"]

    is_valid, error_msg = validate_solution(circles)
    if not is_valid:
        return None

    metrics = compute_metrics(circles)
    score_components = compute_score_components(
        metrics["P_raw"], metrics["R_raw"], alpha=alpha_actual
    )

    return {
        "gen": gen,
        "alpha": alpha_actual,
        "seed": seed,
        "valid": True,
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


def main():
    parser = argparse.ArgumentParser(description='批量生成排布并找到最优方案')
    parser.add_argument('--gen', default='best', help='代数（默认：best）')
    parser.add_argument('--alpha', type=float, default=0.5, help='权重（默认：0.5）')
    parser.add_argument('--count', type=int, default=20, help='生成数量（默认：20）')
    parser.add_argument('--start-seed', type=int, default=1, help='起始 seed（默认：1）')
    parser.add_argument('--skip-existing', action='store_true',
                        help='跳过已存在的文件（默认：否）')
    args = parser.parse_args()

    print(f"\n{'='*70}")
    print(f"批量生成排布方案")
    print(f"{'='*70}")
    print(f"  算法:     gen_{args.gen}")
    print(f"  Alpha:    {args.alpha}")
    print(f"  数量:     {args.count}")
    print(f"  Seed:     {args.start_seed} ~ {args.start_seed + args.count - 1}")
    print(f"{'='*70}\n")

    module = load_main(args.gen)
    output_dir = os.path.join("results", "single_layouts")
    os.makedirs(output_dir, exist_ok=True)

    results = []
    best_result = None
    best_score = -1
    skipped_count = 0

    for i in range(args.count):
        seed = args.start_seed + i

        # 检查文件是否已存在
        out_path = os.path.join(
            output_dir,
            f"layout_gen{args.gen}_alpha{args.alpha}_seed{seed}.json"
        )

        if args.skip_existing and os.path.exists(out_path):
            print(f"[{i+1:3d}/{args.count}] Seed {seed:4d} ... ⊘ 已存在，跳过")
            skipped_count += 1

            # 读取已存在的文件以更新最优结果
            try:
                with open(out_path, 'r') as f:
                    result = json.load(f)
                    if result.get('valid', False):
                        results.append(result)
                        score = result['scores']['score']
                        if score > best_score:
                            best_score = score
                            best_result = result
            except:
                pass
            continue

        print(f"[{i+1:3d}/{args.count}] Seed {seed:4d} ... ", end='', flush=True)

        try:
            result = run_single(module, args.gen, args.alpha, seed)

            if result:
                results.append(result)
                score = result['scores']['score']
                P = result['metrics']['P']
                R = result['metrics']['R']
                N = result['num_holes']

                print(f"✓ Score={score:.4f} P={P:6.1f} R={R:4.1f}% N={N:2d}")

                # 保存文件
                with open(out_path, 'w') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

                # 跟踪最优
                if score > best_score:
                    best_score = score
                    best_result = result
            else:
                print(f"✗ 不可行")

        except Exception as e:
            print(f"✗ 错误: {e}")

    # 打印汇总
    print(f"\n{'='*70}")
    print(f"生成完成")
    print(f"{'='*70}")
    print(f"  总数:       {args.count}")
    print(f"  新生成:     {len(results) - skipped_count}")
    print(f"  跳过:       {skipped_count}")
    print(f"  可行:       {len(results)} ({len(results)/args.count*100:.1f}%)")
    print(f"  不可行:     {args.count - len(results)}")

    if best_result:
        print(f"\n🏆 最优方案")
        print(f"{'='*70}")
        print(f"  Seed:       {best_result['seed']}")
        print(f"  Score:      {best_result['scores']['score']:.6f}")
        print(f"  P:          {best_result['metrics']['P']:.2f}")
        print(f"  R:          {best_result['metrics']['R']:.1f}%")
        print(f"  Pn:         {best_result['scores']['Pn']:.6f}")
        print(f"  Rn:         {best_result['scores']['Rn']:.6f}")
        print(f"  孔数:       {best_result['num_holes']}")
        print(f"  孔隙率:     {best_result['metrics']['porosity']:.2%}")

        best_file = f"layout_gen{args.gen}_alpha{args.alpha}_seed{best_result['seed']}.json"
        print(f"\n  文件:       results/single_layouts/{best_file}")
        print(f"\n  可视化:")
        print(f"    python visualize_layout.py results/single_layouts/{best_file}")

    if results:
        scores = [r['scores']['score'] for r in results]
        Ps = [r['metrics']['P'] for r in results]
        Rs = [r['metrics']['R'] for r in results]

        print(f"\n📊 统计分布")
        print(f"{'='*70}")
        print(f"  Score:  {min(scores):.4f} ~ {max(scores):.4f}  (均值 {sum(scores)/len(scores):.4f})")
        print(f"  P:      {min(Ps):.1f} ~ {max(Ps):.1f}  (均值 {sum(Ps)/len(Ps):.1f})")
        print(f"  R:      {min(Rs):.1f}% ~ {max(Rs):.1f}%  (均值 {sum(Rs)/len(Rs):.1f}%)")

    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
