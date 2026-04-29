"""
比较 single_layouts 文件夹中所有排布的性能，找出最优方案

用法：
  python compare_layouts.py
  python compare_layouts.py --sort-by P    # 按渗透性排序
  python compare_layouts.py --top 5        # 只显示前 5 名
"""
import os
import json
import argparse
from pathlib import Path


def load_all_layouts(directory="results/single_layouts"):
    """加载所有 layout JSON 文件"""
    layouts = []
    path = Path(directory)

    if not path.exists():
        print(f"错误：目录不存在 {directory}")
        return []

    for json_file in path.glob("layout_*.json"):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                if data.get('valid', False):
                    layouts.append({
                        'file': json_file.name,
                        'gen': data['gen'],
                        'alpha': data['alpha'],
                        'seed': data['seed'],
                        'score': data['scores']['score'],
                        'P': data['metrics']['P'],
                        'R': data['metrics']['R'],
                        'Pn': data['scores']['Pn'],
                        'Rn': data['scores']['Rn'],
                        'N': data['num_holes'],
                        'porosity': data['metrics']['porosity']
                    })
        except Exception as e:
            print(f"警告：无法读取 {json_file.name}: {e}")

    return layouts


def main():
    parser = argparse.ArgumentParser(description='比较所有排布方案')
    parser.add_argument('--sort-by', default='score',
                        choices=['score', 'P', 'R', 'Pn', 'Rn', 'N', 'porosity'],
                        help='排序依据（默认：score）')
    parser.add_argument('--top', type=int, default=None,
                        help='只显示前 N 个（默认：全部）')
    parser.add_argument('--filter-gen', default=None,
                        help='只显示特定 gen（如 "best" 或 "22"）')
    parser.add_argument('--filter-alpha', type=float, default=None,
                        help='只显示特定 alpha（如 0.5）')
    args = parser.parse_args()

    layouts = load_all_layouts()

    if not layouts:
        print("未找到任何有效的排布文件")
        return

    # 过滤
    if args.filter_gen:
        layouts = [l for l in layouts if str(l['gen']) == str(args.filter_gen)]
    if args.filter_alpha is not None:
        layouts = [l for l in layouts if abs(l['alpha'] - args.filter_alpha) < 0.01]

    # 排序
    reverse = True  # 大多数指标越大越好
    layouts.sort(key=lambda x: x[args.sort_by], reverse=reverse)

    # 限制数量
    if args.top:
        layouts = layouts[:args.top]

    # 显示结果
    print(f"\n{'='*100}")
    print(f"排布方案对比 (共 {len(layouts)} 个，按 {args.sort_by} 排序)")
    print(f"{'='*100}")
    print(f"{'排名':<4} {'Gen':<6} {'Alpha':<6} {'Seed':<6} {'Score':<8} {'P':<8} {'R':<7} {'孔数':<5} {'孔隙率':<8} {'文件名':<40}")
    print(f"{'-'*100}")

    for i, layout in enumerate(layouts, 1):
        marker = "⭐" if i == 1 else "  "
        print(f"{marker}{i:<3} {layout['gen']:<6} {layout['alpha']:<6.2f} {layout['seed']:<6} "
              f"{layout['score']:<8.4f} {layout['P']:<8.1f} {layout['R']:<7.1f} "
              f"{layout['N']:<5} {layout['porosity']:<8.2%} {layout['file']:<40}")

    if layouts:
        best = layouts[0]
        print(f"\n{'='*100}")
        print(f"🏆 最优方案（按 {args.sort_by}）")
        print(f"{'='*100}")
        print(f"  文件:     {best['file']}")
        print(f"  来源:     gen_{best['gen']}, alpha={best['alpha']}, seed={best['seed']}")
        print(f"  Score:    {best['score']:.6f}")
        print(f"  P:        {best['P']:.2f}")
        print(f"  R:        {best['R']:.1f}%")
        print(f"  Pn:       {best['Pn']:.6f}")
        print(f"  Rn:       {best['Rn']:.6f}")
        print(f"  孔数:     {best['N']}")
        print(f"  孔隙率:   {best['porosity']:.2%}")
        print(f"\n  用于模拟验证:")
        print(f"    python visualize_layout.py results/single_layouts/{best['file']}")
        print(f"{'='*100}\n")


if __name__ == "__main__":
    main()
