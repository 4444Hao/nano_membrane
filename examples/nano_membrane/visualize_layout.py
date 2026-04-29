"""
可视化 JSON 格式的孔径排布

用法：
  python visualize_layout.py results/layout_gen22_alpha0.5_seed429.json
  python visualize_layout.py results/layout_gen22_alpha0.5_seed429.json --output my_layout.svg
"""
import json
import argparse
import os


def export_svg(circles, output_path, domain_size=10.0):
    """将排布导出为 SVG 图"""
    size = 600
    scale = size / domain_size

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f'<svg width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">\n')

        # 背景和边框
        f.write(f'<rect x="0" y="0" width="{size}" height="{size}" '
                f'fill="white" stroke="black" stroke-width="2"/>\n')

        # 网格线（可选）
        f.write('<g stroke="lightgray" stroke-width="0.5">\n')
        for i in range(1, int(domain_size)):
            pos = i * scale
            f.write(f'<line x1="{pos}" y1="0" x2="{pos}" y2="{size}"/>\n')
            f.write(f'<line x1="0" y1="{pos}" x2="{size}" y2="{pos}"/>\n')
        f.write('</g>\n')

        # 孔径圆圈（按直径分组着色）
        colors = {1.0: "#4CAF50", 1.5: "#2196F3", 2.0: "#FF9800",
                  2.5: "#9C27B0", 3.0: "#F44336", 3.5: "#E91E63"}

        for x, y, d in circles:
            cx = x * scale
            cy = size - y * scale  # SVG 坐标系 y 轴向下
            r = (d / 2.0) * scale
            color = colors.get(d, "steelblue")

            f.write(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" '
                    f'fill="{color}" stroke="black" stroke-width="1.5" '
                    f'fill-opacity="0.7"/>\n')

            # 标注孔径
            f.write(f'<text x="{cx:.2f}" y="{cy:.2f}" '
                    f'text-anchor="middle" dominant-baseline="middle" '
                    f'font-size="12" fill="white" font-weight="bold">{d}</text>\n')

        # 图例
        legend_x = 10
        legend_y = size - 120
        f.write(f'<rect x="{legend_x}" y="{legend_y}" width="80" height="110" '
                f'fill="white" stroke="black" fill-opacity="0.9"/>\n')
        f.write(f'<text x="{legend_x + 40}" y="{legend_y + 15}" '
                f'text-anchor="middle" font-size="12" font-weight="bold">孔径</text>\n')

        for i, (d, color) in enumerate(sorted(colors.items())):
            y_pos = legend_y + 30 + i * 15
            f.write(f'<circle cx="{legend_x + 15}" cy="{y_pos}" r="5" fill="{color}"/>\n')
            f.write(f'<text x="{legend_x + 25}" y="{y_pos + 4}" font-size="11">{d}</text>\n')

        f.write('</svg>')

    print(f"✓ SVG 已保存到: {output_path}")


def export_png(circles, output_path, domain_size=10.0):
    """使用 matplotlib 导出 PNG 图"""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
    except ImportError:
        print("错误：需要安装 matplotlib")
        print("运行: pip install matplotlib")
        return

    fig, ax = plt.subplots(figsize=(8, 8))

    # 设置坐标轴
    ax.set_xlim(0, domain_size)
    ax.set_ylim(0, domain_size)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.set_xlabel('X', fontsize=12)
    ax.set_ylabel('Y', fontsize=12)

    # 颜色映射
    colors = {1.0: "#4CAF50", 1.5: "#2196F3", 2.0: "#FF9800",
              2.5: "#9C27B0", 3.0: "#F44336", 3.5: "#E91E63"}

    # 绘制圆圈
    for x, y, d in circles:
        circle = patches.Circle((x, y), d/2,
                                color=colors.get(d, 'steelblue'),
                                alpha=0.7, edgecolor='black', linewidth=1.5)
        ax.add_patch(circle)
        ax.text(x, y, f'{d}', ha='center', va='center',
                color='white', fontsize=10, fontweight='bold')

    # 图例
    legend_elements = [patches.Patch(facecolor=colors[d], label=f'直径 {d}')
                       for d in sorted(set(c[2] for c in circles))]
    ax.legend(handles=legend_elements, loc='upper right')

    plt.title(f'纳米膜孔径排布 (共 {len(circles)} 个孔)', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ PNG 已保存到: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='可视化孔径排布 JSON 文件')
    parser.add_argument('json_path', nargs='?',
                        default='results/single_layouts/layout_gen22_alpha0.5_seed429.json',
                        help='JSON 文件路径（默认：最近生成的文件）')
    parser.add_argument('--output', '-o', help='输出文件路径（默认：同名 .svg）')
    parser.add_argument('--format', '-f', choices=['svg', 'png', 'both'],
                        default='svg', help='输出格式（默认：svg）')
    args = parser.parse_args()

    # 读取 JSON
    if not os.path.exists(args.json_path):
        print(f"错误：找不到文件 {args.json_path}")
        return

    with open(args.json_path, 'r') as f:
        data = json.load(f)

    circles = data['circles']
    gen = data.get('gen', 'unknown')
    alpha = data.get('alpha', 'unknown')
    seed = data.get('seed', 'unknown')

    print(f"\n读取排布信息:")
    print(f"  来源: gen_{gen}")
    print(f"  Alpha: {alpha}")
    print(f"  Seed: {seed}")
    print(f"  孔数: {len(circles)}")

    # 确定输出路径
    if args.output:
        base_path = os.path.splitext(args.output)[0]
    else:
        base_path = os.path.splitext(args.json_path)[0]

    # 生成可视化
    if args.format in ['svg', 'both']:
        export_svg(circles, f"{base_path}.svg")

    if args.format in ['png', 'both']:
        export_png(circles, f"{base_path}.png")

    print(f"\n可以用浏览器打开 SVG 文件查看")


if __name__ == "__main__":
    main()
