import random
import math
import numpy as np
from math import sqrt, exp, pi, sin, cos, log, ceil, floor, atan2, hypot, inf

"""
纳米膜孔布局求解器（启发式优化版）。

核心思路：
1) 先随机生成可行初始解；
2) 再用“松弛 + 模拟退火 + 局部微调”持续改进；
3) 最后离散到 0.01 网格，并做一次可行性兜底修复。
"""

# --------------------------- 几何与物理常量（不可修改）---------------------------
DOMAIN_SIZE = 10.0
MIN_SPACING = 0.5
ATOL = 1e-4
C = 1.64

# EVOLVE-BLOCK-START

# 不同孔径对应的 (渗透贡献 P_type, 截留贡献 R_type)
HOLE_TYPES = {
    1.0: (143.94, 100.0),
    1.5: (778.82, 99.6),
    2.0: (815.70, 99.8),
    2.5: (1048.16, 99.5),
    3.0: (1435.74, 96.8),
    3.5: (1437.24, 94.3),
}
DIAMETERS = sorted(HOLE_TYPES.keys(), reverse=True)

# --------------------------- 搜索超参数 ---------------------------
INIT_ATTEMPTS = 1800
RELAX_STEPS = 220
SA_STEPS = 1800
REFINE_TRIALS = 30

TEMP0 = 0.8
COOL = 0.997
ANNEAL_RELAX_INTERVAL = 30
ANNEAL_RELAX_STEPS = 10
ANNEAL_PATIENCE = 260

OBJECTIVE_ALPHA = 0.5

# 归一化参数
P_KNEE = 600.0
P_CAP = 1100.0
R_FLOOR = 96.0


def set_objective_alpha(alpha):
    """设置目标权重 alpha,并限制在 [0, 1]。"""
    global OBJECTIVE_ALPHA
    try:
        a = float(alpha)
    except (TypeError, ValueError):
        a = 0.5
    OBJECTIVE_ALPHA = max(0.0, min(1.0, a))


def circle_area(d):
    """根据孔径 d 计算圆孔面积。"""
    return pi * (d / 2.0) ** 2


def clamp(v, lo, hi):
    """将数值截断到 [lo, hi] 区间。"""
    return max(lo, min(hi, v))


def inside(x, y, d):
    """判断圆孔是否完整落在膜区域内部。"""
    r = d / 2.0
    return r <= x <= DOMAIN_SIZE - r and r <= y <= DOMAIN_SIZE - r


def pair_clearance(c1, c2):
    """计算两个孔之间的净间隙（负值表示重叠/间距不足）。"""
    x1, y1, d1 = c1
    x2, y2, d2 = c2
    dist = sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
    min_dist = (d1 + d2) / 2.0 + MIN_SPACING
    return dist - min_dist


def spacing(x, y, d, circles, ignore_idx=None):
    """判断待放置孔与已有孔是否满足最小间距约束。"""
    for j, (cx, cy, cd) in enumerate(circles):
        if ignore_idx is not None and j == ignore_idx:
            continue
        dist = sqrt((x - cx) ** 2 + (y - cy) ** 2)
        min_dist = (d + cd) / 2.0 + MIN_SPACING
        if dist < min_dist - ATOL:
            return False
    return True


def valid(x, y, d, circles, ignore_idx=None):
    """同时检查边界约束与孔间距约束。"""
    return inside(x, y, d) and spacing(x, y, d, circles, ignore_idx=ignore_idx)


def round_solution(circles):
    """将坐标统一保留两位小数，便于输出与复现实验。"""
    out = []
    for x, y, d in circles:
        rx = round(x, 2)
        ry = round(y, 2)
        out.append([rx, ry, d])
    return out


def solution_metrics(circles):
    """
    计算布局的核心工程指标：
    - P: 渗透性（按膜面积归一）
    - R: 截留率（按孔面积加权平均）
    - porosity: 孔隙率
    """
    total_area = 0.0
    p_area_sum = 0.0
    r_area_sum = 0.0

    for x, y, d in circles:
        area = circle_area(d)
        p_val, r_val = HOLE_TYPES[d]
        p_area = area * p_val
        r_area = area * r_val
        total_area += area
        p_area_sum += p_area
        r_area_sum += r_area

    if total_area <= 0:
        return 0.0, 0.0, 0.0

    # 目标函数的基础定义
    # P 按膜总面积归一，而不是按孔总面积归一
    P = C * p_area_sum / max(DOMAIN_SIZE * DOMAIN_SIZE, 1e-12)
    R = r_area_sum / max(total_area, 1e-12)
    R = max(0.0, min(100.0, R))
    porosity = total_area / (DOMAIN_SIZE * DOMAIN_SIZE)
    return P, R, porosity


def normalize_metrics(P, R):
    """将 P、R 归一到 [0,1]，用于统一加权打分。"""
    # 在拐点前保持较高增益，超过拐点后降低边际收益
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


def engineering_score(P, R, alpha=None):
    """计算单次工程分数：alpha*Pn + (1-alpha)*Rn。"""
    # 核心目标：归一化后的通量/截留加权和
    Pn, Rn = normalize_metrics(P, R)
    if alpha is None:
        alpha = OBJECTIVE_ALPHA
    alpha = max(0.0, min(1.0, float(alpha)))
    return alpha * Pn + (1.0 - alpha) * Rn


def violation(circles):
    """
    计算几何违规惩罚项。
    违规越严重，penalty 越大。
    """
    penalty = 0.0

    seen = set()

    for i, (x, y, d) in enumerate(circles):
        if d not in HOLE_TYPES:
            penalty += 100.0
            continue

        r = d / 2.0
        if x < r:
            penalty += (r - x) ** 2 * 100.0
        if x > DOMAIN_SIZE - r:
            penalty += (x - (DOMAIN_SIZE - r)) ** 2 * 100.0
        if y < r:
            penalty += (r - y) ** 2 * 100.0
        if y > DOMAIN_SIZE - r:
            penalty += (y - (DOMAIN_SIZE - r)) ** 2 * 100.0

        key = (round(x, 2), round(y, 2))
        if key in seen:
            penalty += 20.0
        seen.add(key)

        for j in range(i + 1, len(circles)):
            clr = pair_clearance(circles[i], circles[j])
            if clr < 0.0:
                penalty += (-clr) ** 2 * 200.0

    return penalty


def objective(circles):
    """
    让内部搜索目标尽量与评估器打分保持一致。
    该目标值越小越好。
    """
    v = violation(circles)
    P, R, _ = solution_metrics(circles)
    alphas = [0.2, 0.35, 0.5, 0.65, 0.8]
    score = sum(engineering_score(P, R, a) for a in alphas) / len(alphas)
    return v - score


def try_place_circle(circles, d, max_trials=80):
    """尝试随机放入一个指定孔径的孔，成功则写回列表。"""
    for _ in range(max_trials):
        x = random.uniform(d / 2.0, DOMAIN_SIZE - d / 2.0)
        y = random.uniform(d / 2.0, DOMAIN_SIZE - d / 2.0)
        if valid(x, y, d, circles):
            circles.append([x, y, d])
            return True
    return False


def poisson_init():
    """
    构造初始解：
    先按“大孔优先”放置，再用随机采样补充。
    """
    circles = []

    # 先用大孔打底，再混合补充
    staged_diameters = [3.5] * 12 + [3.0] * 12 + [2.5] * 10 + [2.0] * 8 + [1.5] * 6 + [1.0] * 4
    attempts = 0

    for d in staged_diameters:
        try_place_circle(circles, d, max_trials=25)

    while attempts < INIT_ATTEMPTS:
        d = random.choice(DIAMETERS)
        try_place_circle(circles, d, max_trials=1)
        attempts += 1

    return circles


def relax(circles, steps=RELAX_STEPS):
    """
    基于简化“力学推开”思想做几何松弛：
    - 重叠孔彼此排斥；
    - 越界孔被推回边界内。
    """
    if not circles:
        return circles

    circles = np.array(circles, dtype=float)
    n = len(circles)

    for _ in range(max(1, steps)):
        forces = np.zeros((n, 2), dtype=float)

        for i in range(n):
            xi, yi, di = circles[i]

            # 边界软回弹
            ri = di / 2.0
            if xi < ri:
                forces[i, 0] += (ri - xi) * 0.8
            if xi > DOMAIN_SIZE - ri:
                forces[i, 0] -= (xi - (DOMAIN_SIZE - ri)) * 0.8
            if yi < ri:
                forces[i, 1] += (ri - yi) * 0.8
            if yi > DOMAIN_SIZE - ri:
                forces[i, 1] -= (yi - (DOMAIN_SIZE - ri)) * 0.8

            for j in range(i + 1, n):
                xj, yj, dj = circles[j]
                dx = xi - xj
                dy = yi - yj
                dist = sqrt(dx * dx + dy * dy) + 1e-8
                min_dist = (di + dj) / 2.0 + MIN_SPACING
                overlap = min_dist - dist

                if overlap > 0.0:
                    f = overlap * 0.7
                    ux = dx / dist
                    uy = dy / dist
                    forces[i] += np.array([ux, uy]) * f
                    forces[j] -= np.array([ux, uy]) * f

        circles[:, :2] += 0.15 * forces

        # 投影回可行边界盒
        for i in range(n):
            d = circles[i, 2]
            r = d / 2.0
            circles[i, 0] = clamp(circles[i, 0], r, DOMAIN_SIZE - r)
            circles[i, 1] = clamp(circles[i, 1], r, DOMAIN_SIZE - r)

    return circles.tolist()


def mutate_move(circles):
    """随机选择一个孔做小幅平移变异。"""
    if not circles:
        return circles

    i = random.randrange(len(circles))
    x, y, d = circles[i]
    old = [x, y, d]

    for _ in range(25):
        nx = x + random.uniform(-0.35, 0.35)
        ny = y + random.uniform(-0.35, 0.35)
        nx = clamp(nx, d / 2.0, DOMAIN_SIZE - d / 2.0)
        ny = clamp(ny, d / 2.0, DOMAIN_SIZE - d / 2.0)

        if valid(nx, ny, d, circles, ignore_idx=i):
            circles[i] = [nx, ny, d]
            return circles

    circles[i] = old
    return circles


def mutate_diameter(circles):
    """随机选择一个孔并尝试替换为其他孔径。"""
    if not circles:
        return circles

    i = random.randrange(len(circles))
    x, y, old_d = circles[i]

    candidate_ds = DIAMETERS[:]
    random.shuffle(candidate_ds)

    for new_d in candidate_ds:
        if valid(x, y, new_d, circles, ignore_idx=i):
            circles[i] = [x, y, new_d]
            return circles

    circles[i] = [x, y, old_d]
    return circles


def mutate_add(circles):
    """尝试新增一个孔（按随机孔径顺序试放）。"""
    candidate_ds = DIAMETERS[:]
    random.shuffle(candidate_ds)

    for d in candidate_ds:
        if try_place_circle(circles, d, max_trials=20):
            return circles
    return circles


def mutate_remove(circles):
    """删除贡献较低的孔，帮助重构布局。"""
    if len(circles) <= 3:
        return circles

    # 优先移除对 P/R 综合贡献较低的孔
    p_max_ref = max(v[0] for v in HOLE_TYPES.values())
    alpha = OBJECTIVE_ALPHA
    utilities = []
    for _, _, d in circles:
        p_val, r_val = HOLE_TYPES[d]
        area = circle_area(d)
        pn_type = p_val / max(p_max_ref, 1e-12)
        rn_type = r_val / 100.0
        utilities.append(area * (alpha * pn_type + (1.0 - alpha) * rn_type))
    i = int(np.argmin(np.array(utilities))) if utilities else random.randrange(len(circles))
    circles.pop(i)
    return circles


def mutate_swap_diameters(circles):
    """
    在两处位置都保持可行时，交换两个孔的直径。
    这是低成本的拓扑变化操作，有助于跳出局部最优。
    """
    if len(circles) < 2:
        return circles

    i, j = random.sample(range(len(circles)), 2)
    xi, yi, di = circles[i]
    xj, yj, dj = circles[j]

    if di == dj:
        return circles

    if valid(xi, yi, dj, circles, ignore_idx=i) and valid(xj, yj, di, circles, ignore_idx=j):
        circles[i] = [xi, yi, dj]
        circles[j] = [xj, yj, di]
    return circles


def mutate_relocate_large_circle(circles):
    """
    将一个大孔重定位到新的可行区域。
    可缓解“大孔阻塞小孔布局”导致的局部最优问题。
    """
    if not circles:
        return circles

    areas = [circle_area(d) for _, _, d in circles]
    i = int(np.argmax(areas))
    _, _, d = circles[i]
    old = circles[i]

    for _ in range(40):
        nx = round(random.uniform(d / 2.0, DOMAIN_SIZE - d / 2.0), 2)
        ny = round(random.uniform(d / 2.0, DOMAIN_SIZE - d / 2.0), 2)
        if valid(nx, ny, d, circles, ignore_idx=i):
            circles[i] = [nx, ny, d]
            return circles

    circles[i] = old
    return circles


def anneal(circles, enable_swap=True):
    """
    模拟退火主过程：
    - 随机选择变异算子生成候选解；
    - 依据温度按 Metropolis 准则接受或拒绝；
    - 跟踪并返回历史最优解。
    """
    current = [c.copy() for c in circles]
    currentE = objective(current)

    best = [c.copy() for c in current]
    bestE = currentE

    temp = TEMP0
    stagnation = 0

    for step in range(SA_STEPS):
        cand = [c.copy() for c in current]

        move = random.random()
        # 不同变异算子的采样概率（总和为 1）
        if move < 0.30:
            cand = mutate_move(cand)
        elif move < 0.52:
            cand = mutate_diameter(cand)
        elif move < 0.68 and enable_swap:
            cand = mutate_swap_diameters(cand)
        elif move < 0.84:
            cand = mutate_add(cand)
        elif move < 0.94:
            cand = mutate_remove(cand)
        else:
            cand = mutate_relocate_large_circle(cand)

        if step % ANNEAL_RELAX_INTERVAL == 0:
            cand = relax(cand, steps=ANNEAL_RELAX_STEPS)
        E = objective(cand)
        delta = E - currentE

        if delta <= 0.0 or random.random() < exp(-delta / max(temp, 1e-8)):
            current = cand
            currentE = E

            if E < bestE:
                best = [c.copy() for c in cand]
                bestE = E
                stagnation = 0
            else:
                stagnation += 1
        else:
            stagnation += 1

        temp *= COOL
        if stagnation >= ANNEAL_PATIENCE:
            break

    return best


def refine(circles):
    """对每个孔做小范围局部搜索，进一步压低目标值。"""
    if not circles:
        return circles

    improved = [c.copy() for c in circles]

    for i in range(len(improved)):
        x, y, d = improved[i]
        local_best = [x, y, d]
        local_best_E = objective(improved)

        for _ in range(REFINE_TRIALS):
            step = random.uniform(0.05, 0.20)
            nx = x + random.choice([-step, step])
            ny = y + random.choice([-step, step])

            nx = clamp(nx, d / 2.0, DOMAIN_SIZE - d / 2.0)
            ny = clamp(ny, d / 2.0, DOMAIN_SIZE - d / 2.0)

            if not valid(nx, ny, d, improved, ignore_idx=i):
                continue

            old = improved[i]
            improved[i] = [nx, ny, d]
            E = objective(improved)

            if E < local_best_E:
                local_best_E = E
                local_best = [nx, ny, d]

            improved[i] = old

        improved[i] = local_best

    return improved


def snap_candidates(v):
    """
    围绕连续值生成附近的 0.01 网格候选点。
    """
    base = round(v, 2)
    cands = [base, round(base - 0.01, 2), round(base + 0.01, 2)]
    # 去重并保持原顺序
    out = []
    seen = set()
    for x in cands:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def discretize(circles):
    """
    将坐标离散到 0.01 网格。
    通过局部修复尽量保持可行性，而不是只做简单四舍五入。
    """
    if not circles:
        return []

    # 优先处理大孔，尽量保留影响更大的几何结构
    ordered = sorted(circles, key=lambda c: circle_area(c[2]), reverse=True)

    snapped = []
    for x, y, d in ordered:
        placed = False
        for rx in snap_candidates(x):
            for ry in snap_candidates(y):
                if valid(rx, ry, d, snapped):
                    snapped.append([rx, ry, d])
                    placed = True
                    break
            if placed:
                break

        # 若邻域吸附失败，尝试随机局部网格扰动修复
        if not placed:
            best = None
            best_e = float("inf")
            for _ in range(20):
                rx = round(clamp(x + random.uniform(-0.03, 0.03), d / 2.0, DOMAIN_SIZE - d / 2.0), 2)
                ry = round(clamp(y + random.uniform(-0.03, 0.03), d / 2.0, DOMAIN_SIZE - d / 2.0), 2)
                if valid(rx, ry, d, snapped):
                    trial = snapped + [[rx, ry, d]]
                    e = objective(trial)
                    if e < best_e:
                        best_e = e
                        best = [rx, ry, d]
            if best is not None:
                snapped.append(best)

    return [(round(x, 2), round(y, 2), d) for x, y, d in snapped]


def construct_solution(ablation_mode="full"):
    """
    组合完整求解流程，并支持消融开关：
    - no_relax / no_swap / no_discretize
    """
    enable_relax = ablation_mode != "no_relax"
    enable_swap = ablation_mode != "no_swap"
    enable_discretize = ablation_mode != "no_discretize"

    circles = poisson_init()
    if enable_relax:
        circles = relax(circles)
    circles = anneal(circles, enable_swap=enable_swap)
    circles = refine(circles)
    if enable_discretize:
        circles = discretize(circles)
    else:
        circles = round_solution(circles)

    # 最后一层防守：若取整后仍异常，则回退到可行子集
    final = []
    for x, y, d in circles:
        if valid(x, y, d, final):
            final.append([x, y, d])

    return [(round(x, 2), round(y, 2), d) for x, y, d in final]

# EVOLVE-BLOCK-END


def run_experiment(seed=None, ablation_mode="full", alpha=0.5, **kwargs):
    """
    评估入口函数：
    由外部框架多次调用，返回当前一次试验的孔布局与 alpha。
    """

    if seed is not None:

        random.seed(seed)
        np.random.seed(seed)

    set_objective_alpha(alpha)
    circles = construct_solution(ablation_mode=ablation_mode)
    return {"circles": circles, "alpha": OBJECTIVE_ALPHA}
