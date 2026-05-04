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
import random
import math
import numpy as np
from math import sqrt, exp, pi

"""
纳米膜孔布局求解器（基于Tabu搜索的最大权独立集优化，结合局部组合改进）。

输入输出接口保持不变：
- construct_solution(ablation_mode="full", seed=None) -> list of (x,y,d) 保留两位小数
- run_experiment(seed=None, ablation_mode="full", alpha=0.5) -> {"circles": circles, "alpha": OBJECTIVE_ALPHA}
"""

DOMAIN_SIZE = 10.0
MIN_SPACING = 0.5
ATOL = 1e-4
C = 1.64

HOLE_TYPES = {
    1.0: (143.94, 100.0),
    1.5: (778.82, 99.6),
    2.0: (815.70, 99.8),
    2.5: (1048.16, 99.5),
    3.0: (1435.74, 96.8),
    3.5: (1437.24, 94.3),
}
DIAMETERS = sorted(HOLE_TYPES.keys(), reverse=True)

P_KNEE = 600.0
P_CAP = 1100.0
R_FLOOR = 96.0
OBJECTIVE_ALPHA = 0.5

CANDIDATE_PER_DIAMETER = 700
RANDOM_CANDIDATE_FRACTION = 0.35
MAX_SELECT = 90
TABU_TENURE_MIN = 6
TABU_TENURE_MAX = 16
LOCAL_ITERS = 1400
SAMPLE_ADD = 220
MAX_REMOVALS_ON_ADD = 5
DISCRETIZE_NEIGHBOR_TRIES = 36

def set_objective_alpha(alpha):
    global OBJECTIVE_ALPHA
    try:
        a = float(alpha)
    except (TypeError, ValueError):
        a = 0.5
    OBJECTIVE_ALPHA = max(0.0, min(1.0, a))

def circle_area(d):
    return pi * (d / 2.0) ** 2

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def inside(x, y, d):
    r = d / 2.0
    return r <= x <= DOMAIN_SIZE - r and r <= y <= DOMAIN_SIZE - r

def normalize_metrics(P, R):
    p = max(0.0, float(P))
    knee = max(1e-9, float(P_KNEE))
    cap = max(knee + 1e-9, float(P_CAP))
    if p <= knee:
        Pn = 0.8 * (p / knee)
    else:
        p_eff = min(p, cap)
        Pn = 0.8 + 0.2 * ((p_eff - knee) / (cap - knee))
    Pn = max(0.0, min(1.0, Pn))
    denom = max(100.0 - float(R_FLOOR), 1e-9)
    Rn = (float(R) - float(R_FLOOR)) / denom
    Rn = max(0.0, min(1.0, Rn))
    return Pn, Rn

def engineering_score(P, R, alpha=None):
    Pn, Rn = normalize_metrics(P, R)
    if alpha is None:
        alpha = OBJECTIVE_ALPHA
    alpha = max(0.0, min(1.0, float(alpha)))
    return alpha * Pn + (1.0 - alpha) * Rn

class SpatialHash:
    def __init__(self, cell_size=None):
        if cell_size is None:
            cell_size = max(DIAMETERS) + MIN_SPACING
        self.cell_size = float(cell_size)
        self.buckets = {}

    def key(self, x, y):
        return (int(x // self.cell_size), int(y // self.cell_size))

    def add(self, idx, x, y):
        k = self.key(x, y)
        self.buckets.setdefault(k, []).append(idx)

    def nearby(self, x, y):
        kx, ky = self.key(x, y)
        out = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                k = (kx + dx, ky + dy)
                if k in self.buckets:
                    out.extend(self.buckets[k])
        return out

def generate_hex_candidates(diameter, limit=CANDIDATE_PER_DIAMETER):
    r = diameter / 2.0
    h = diameter + MIN_SPACING
    v = h * math.sqrt(3.0) / 2.0
    cands = []
    y = r
    row = 0
    while y <= DOMAIN_SIZE - r + 1e-9 and len(cands) < limit:
        x_start = r + (0.5 * h if (row % 2) else 0.0)
        x = x_start
        while x <= DOMAIN_SIZE - r + 1e-9 and len(cands) < limit:
            px = clamp(round(x + random.uniform(-0.03, 0.03), 4), r, DOMAIN_SIZE - r)
            py = clamp(round(y + random.uniform(-0.03, 0.03), 4), r, DOMAIN_SIZE - r)
            cands.append((px, py, diameter))
            x += h
        row += 1
        y += v
    random.shuffle(cands)
    return cands

def generate_random_candidates(diameter, count):
    r = diameter / 2.0
    out = []
    for _ in range(count):
        px = random.uniform(r, DOMAIN_SIZE - r)
        py = random.uniform(r, DOMAIN_SIZE - r)
        out.append((px, py, diameter))
    random.shuffle(out)
    return out

def build_candidates_pool():
    candidates = []
    for d in DIAMETERS:
        n_hex = int(CANDIDATE_PER_DIAMETER * (1.0 - RANDOM_CANDIDATE_FRACTION))
        n_rand = CANDIDATE_PER_DIAMETER - n_hex
        hex_c = generate_hex_candidates(d, limit=max(40, n_hex))
        rand_c = generate_random_candidates(d, max(0, n_rand))
        pool = hex_c + rand_c
        if len(pool) > CANDIDATE_PER_DIAMETER:
            pool = pool[:CANDIDATE_PER_DIAMETER]
        for (x, y, dd) in pool:
            area = circle_area(dd)
            p_val, r_val = HOLE_TYPES[dd]
            P_single = C * (area * p_val) / (DOMAIN_SIZE * DOMAIN_SIZE)
            R_single = r_val
            base_w = engineering_score(P_single, R_single)
            candidates.append({"x": float(x), "y": float(y), "d": dd,
                               "area": area, "p": p_val, "r": r_val, "w": base_w})
    for idx, c in enumerate(candidates):
        c["i"] = idx
    sh = SpatialHash(cell_size=max(DIAMETERS) + MIN_SPACING)
    for c in candidates:
        sh.add(c["i"], c["x"], c["y"])
    n = len(candidates)
    conflicts = [set() for _ in range(n)]
    for i, c in enumerate(candidates):
        for nb in sh.nearby(c["x"], c["y"]):
            if nb <= i:
                continue
            c2 = candidates[nb]
            min_dist = (c["d"] + c2["d"]) / 2.0 + MIN_SPACING
            if sqrt((c["x"] - c2["x"])**2 + (c["y"] - c2["y"])**2) < min_dist - ATOL:
                conflicts[i].add(nb)
                conflicts[nb].add(i)
    return candidates, conflicts

def greedy_initial(candidates, conflicts):
    remaining = set(c["i"] for c in candidates)
    selected = []
    sorted_idx = sorted(remaining, key=lambda ii: candidates[ii]["w"], reverse=True)
    for ii in sorted_idx:
        if ii not in remaining:
            continue
        selected.append(ii)
        to_remove = {ii} | conflicts[ii]
        remaining -= to_remove
        if len(selected) >= MAX_SELECT:
            break
    return set(selected)

class Totals:
    def __init__(self, candidates, selected_indices=None):
        self.candidates = candidates
        self.selected = set() if selected_indices is None else set(selected_indices)
        self.total_area = 0.0
        self.p_sum = 0.0
        self.r_sum = 0.0
        self._accumulate_all()

    def _accumulate_all(self):
        self.total_area = 0.0
        self.p_sum = 0.0
        self.r_sum = 0.0
        for i in self.selected:
            c = self.candidates[i]
            a = c["area"]
            self.total_area += a
            self.p_sum += a * c["p"]
            self.r_sum += a * c["r"]

    def add_index(self, i):
        c = self.candidates[i]
        a = c["area"]
        self.selected.add(i)
        self.total_area += a
        self.p_sum += a * c["p"]
        self.r_sum += a * c["r"]

    def remove_index(self, i):
        if i not in self.selected:
            return
        c = self.candidates[i]
        a = c["area"]
        self.selected.remove(i)
        self.total_area -= a
        self.p_sum -= a * c["p"]
        self.r_sum -= a * c["r"]

    def compute_score(self):
        if self.total_area <= 0.0:
            return engineering_score(0.0, 0.0)
        P = C * (self.p_sum) / (DOMAIN_SIZE * DOMAIN_SIZE)
        R = self.r_sum / max(self.total_area, 1e-12)
        R = max(0.0, min(100.0, R))
        return engineering_score(P, R)

    def score_with_add_and_remove(self, add_idx, remove_set):
        a_add = self.candidates[add_idx]["area"]
        p_add = a_add * self.candidates[add_idx]["p"]
        r_add = a_add * self.candidates[add_idx]["r"]
        new_total = self.total_area + a_add
        new_p = self.p_sum + p_add
        new_r = self.r_sum + r_add
        for j in remove_set:
            if j == add_idx:
                continue
            c = self.candidates[j]
            a = c["area"]
            new_total -= a
            new_p -= a * c["p"]
            new_r -= a * c["r"]
        if new_total <= 0.0:
            P = 0.0
            R = 0.0
        else:
            P = C * (new_p) / (DOMAIN_SIZE * DOMAIN_SIZE)
            R = new_r / max(new_total, 1e-12)
            R = max(0.0, min(100.0, R))
        return engineering_score(P, R), P, R

    def apply_add_and_remove(self, add_idx, remove_set):
        for j in sorted(remove_set):
            if j in self.selected:
                self.remove_index(j)
        if add_idx not in self.selected:
            self.add_index(add_idx)

def tabu_search(candidates, conflicts, seed=None, alpha=OBJECTIVE_ALPHA):
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    n = len(candidates)
    if n == 0:
        return []

    selected = greedy_initial(candidates, conflicts)
    totals = Totals(candidates, selected_indices=selected)
    best_selected = set(selected)
    best_score = totals.compute_score()
    current_selected = set(selected)
    current_score = best_score
    tabu = {}

    for it in range(LOCAL_ITERS):
        to_del = []
        for k in tabu:
            tabu[k] -= 1
            if tabu[k] <= 0:
                to_del.append(k)
        for k in to_del:
            del tabu[k]

        non_selected = [i for i in range(n) if i not in current_selected]
        if not non_selected:
            remove_choice = None
            for sel in list(current_selected):
                tot_copy = Totals(candidates, selected_indices=current_selected)
                tot_copy.remove_index(sel)
                s_after = tot_copy.compute_score()
                if s_after > current_score + 1e-9:
                    remove_choice = (sel, s_after)
                    break
            if remove_choice is None:
                break
            rem_idx, new_s = remove_choice
            if rem_idx in tabu and new_s <= best_score:
                pass
            else:
                current_selected.remove(rem_idx)
                totals.remove_index(rem_idx)
                current_score = totals.compute_score()
                if current_score > best_score + 1e-12:
                    best_score = current_score
                    best_selected = set(current_selected)
                tabu[rem_idx] = random.randint(TABU_TENURE_MIN, TABU_TENURE_MAX)
            continue

        sample = non_selected
        if len(non_selected) > SAMPLE_ADD:
            weights = [candidates[i]["w"] for i in non_selected]
            ssum = sum(weights)
            if ssum <= 0:
                sample = random.sample(non_selected, SAMPLE_ADD)
            else:
                sample = []
                pop = non_selected[:]
                pop_weights = weights[:]
                for _ in range(SAMPLE_ADD):
                    if not pop:
                        break
                    r = random.random() * sum(pop_weights)
                    acc = 0.0
                    for idx_w, w in enumerate(pop_weights):
                        acc += w
                        if r <= acc:
                            sample.append(pop.pop(idx_w))
                            pop_weights.pop(idx_w)
                            break

        best_move = None
        best_move_gain = -float('inf')
        best_move_new_score = current_score

        for i in sample:
            conflicts_sel = conflicts[i] & current_selected
            if len(conflicts_sel) > MAX_REMOVALS_ON_ADD:
                continue
            s_after, _, _ = totals.score_with_add_and_remove(i, conflicts_sel)
            gain = s_after - current_score
            if i in tabu and s_after <= best_score + 1e-12:
                continue
            if gain > best_move_gain + 1e-12 or (abs(gain - best_move_gain) <= 1e-12 and s_after > best_move_new_score):
                best_move_gain = gain
                best_move = ("add", i, conflicts_sel)
                best_move_new_score = s_after

        if current_selected:
            sel_list = list(current_selected)
            random.shuffle(sel_list)
            sample_rem = sel_list[:min(40, len(sel_list))]
            for j in sample_rem:
                tot_copy = Totals(candidates, selected_indices=current_selected)
                tot_copy.remove_index(j)
                s_after = tot_copy.compute_score()
                gain = s_after - current_score
                if j in tabu and s_after <= best_score + 1e-12:
                    continue
                if gain > best_move_gain + 1e-12 or (abs(gain - best_move_gain) <= 1e-12 and s_after > best_move_new_score):
                    best_move_gain = gain
                    best_move = ("remove", j, set())
                    best_move_new_score = s_after

        if best_move is None:
            top_non = sorted(non_selected, key=lambda ii: candidates[ii]["w"], reverse=True)[:40]
            found = False
            for i in top_non:
                conflicts_sel = conflicts[i] & current_selected
                if len(conflicts_sel) <= (MAX_REMOVALS_ON_ADD + 2):
                    s_after, _, _ = totals.score_with_add_and_remove(i, conflicts_sel)
                    if i not in tabu or s_after > best_score + 1e-12:
                        best_move = ("add", i, conflicts_sel)
                        best_move_new_score = s_after
                        found = True
                        break
            if not found:
                if current_selected:
                    j = random.choice(list(current_selected))
                    best_move = ("remove", j, set())
                    tot_copy = Totals(candidates, selected_indices=current_selected)
                    tot_copy.remove_index(j)
                    best_move_new_score = tot_copy.compute_score()

        if best_move is None:
            break

        typ, idx, remset = best_move
        if typ == "add":
            totals.apply_add_and_remove(idx, remset)
            for r in remset:
                if r in current_selected:
                    current_selected.remove(r)
                    tabu[r] = random.randint(TABU_TENURE_MIN, TABU_TENURE_MAX)
            current_selected.add(idx)
            tabu[idx] = random.randint(TABU_TENURE_MIN, TABU_TENURE_MAX)
            current_score = totals.compute_score()
        else:
            if idx in current_selected:
                totals.remove_index(idx)
                current_selected.remove(idx)
                tabu[idx] = random.randint(TABU_TENURE_MIN, TABU_TENURE_MAX)
                current_score = totals.compute_score()

        if current_score > best_score + 1e-12:
            best_score = current_score
            best_selected = set(current_selected)

        if len(best_selected) >= MAX_SELECT and it > 40 and best_move_gain <= 1e-6:
            break

    return sorted(list(best_selected))

def local_combinatorial_improve(candidates, conflicts, selected_indices, passes=6, seed=None, alpha=OBJECTIVE_ALPHA):
    """
    Multi-pass local combinatorial improvement: single-add, 1-for-1 and 1-for-2 swaps.
    """
    if seed is not None:
        random.seed(seed)
    n = len(candidates)
    sel = set(selected_indices)
    totals = Totals(candidates, selected_indices=sel)
    base_score = totals.compute_score()
    non_sel = [i for i in range(n) if i not in sel]

    for _ in range(passes):
        improved = False

        # Single-adds
        cand_order = sorted(non_sel, key=lambda i: candidates[i]["w"], reverse=True)
        for i in cand_order[:800]:
            conflicts_sel = conflicts[i] & sel
            if len(conflicts_sel) > MAX_REMOVALS_ON_ADD:
                continue
            s_after, _, _ = totals.score_with_add_and_remove(i, conflicts_sel)
            if s_after > base_score + 1e-10:
                totals.apply_add_and_remove(i, conflicts_sel)
                for r in conflicts_sel:
                    if r in sel:
                        sel.remove(r)
                        if r not in non_sel:
                            non_sel.append(r)
                if i in non_sel:
                    non_sel.remove(i)
                sel.add(i)
                base_score = s_after
                improved = True
                break
        if improved:
            continue

        # 1-for-1 swaps
        if sel and non_sel:
            sel_list = list(sel)
            random.shuffle(sel_list)
            for rem in sel_list[:60]:
                neighborhood = set()
                for nb in conflicts[rem]:
                    if nb in non_sel:
                        neighborhood.add(nb)
                if not neighborhood:
                    neighborhood.update(non_sel[:40])
                neighborhood = list(neighborhood)
                random.shuffle(neighborhood)
                for cand in neighborhood[:120]:
                    conflicts_sel = conflicts[cand] & sel
                    if rem in conflicts_sel:
                        conflicts_sel = set(conflicts_sel)
                        conflicts_sel.discard(rem)
                    if len(conflicts_sel) > MAX_REMOVALS_ON_ADD:
                        continue
                    remove_set = set(conflicts_sel)
                    remove_set.add(rem)
                    s_after, _, _ = totals.score_with_add_and_remove(cand, remove_set)
                    if s_after > base_score + 1e-10:
                        totals.apply_add_and_remove(cand, remove_set)
                        for r in remove_set:
                            if r in sel:
                                sel.remove(r)
                                if r not in non_sel:
                                    non_sel.append(r)
                        if cand in non_sel:
                            non_sel.remove(cand)
                        sel.add(cand)
                        base_score = s_after
                        improved = True
                        break
                if improved:
                    break
            if improved:
                continue

        # 1-for-2 swaps
        if sel and len(non_sel) >= 2:
            sel_list = list(sel)
            random.shuffle(sel_list)
            found_pair = False
            for rem in sel_list[:30]:
                rx = candidates[rem]["x"]
                ry = candidates[rem]["y"]
                rd = candidates[rem]["d"]
                pool = []
                for cand in non_sel:
                    if len(conflicts[cand] & sel) > 4:
                        continue
                    dx = candidates[cand]["x"] - rx
                    dy = candidates[cand]["y"] - ry
                    if dx*dx + dy*dy <= ((candidates[cand]["d"]+rd)**2 + 9.0):
                        pool.append(cand)
                if len(pool) < 2:
                    continue
                random.shuffle(pool)
                tries = 0
                limit_pairs = min(200, len(pool)*(len(pool)-1)//2)
                for a_idx in range(min(len(pool), 30)):
                    for b_idx in range(a_idx+1, min(len(pool), 50)):
                        a = pool[a_idx]
                        b = pool[b_idx]
                        if b in conflicts[a]:
                            continue
                        remset = set(conflicts[a] & sel) | set(conflicts[b] & sel)
                        remset.add(rem)
                        if len(remset) > MAX_REMOVALS_ON_ADD + 2:
                            continue
                        a_add = candidates[a]["area"]
                        b_add = candidates[b]["area"]
                        new_total = totals.total_area + a_add + b_add
                        new_p = totals.p_sum + a_add * candidates[a]["p"] + b_add * candidates[b]["p"]
                        new_r = totals.r_sum + a_add * candidates[a]["r"] + b_add * candidates[b]["r"]
                        for j in remset:
                            if j == a or j == b:
                                continue
                            cj = candidates[j]
                            aj = cj["area"]
                            new_total -= aj
                            new_p -= aj * cj["p"]
                            new_r -= aj * cj["r"]
                        if new_total <= 0.0:
                            s_after = engineering_score(0.0, 0.0)
                        else:
                            P = C * (new_p) / (DOMAIN_SIZE * DOMAIN_SIZE)
                            R = new_r / new_total
                            R = max(0.0, min(100.0, R))
                            s_after = engineering_score(P, R)
                        if s_after > base_score + 1e-10:
                            totals.apply_add_and_remove(a, remset)
                            for r in remset:
                                if r in sel:
                                    sel.remove(r)
                                    if r not in non_sel:
                                        non_sel.append(r)
                            if a in non_sel:
                                non_sel.remove(a)
                            sel.add(a)
                            conf_b = conflicts[b] & sel
                            totals.apply_add_and_remove(b, conf_b)
                            for r in conf_b:
                                if r in sel:
                                    sel.remove(r)
                                    if r not in non_sel:
                                        non_sel.append(r)
                            if b in non_sel:
                                non_sel.remove(b)
                            sel.add(b)
                            base_score = totals.compute_score()
                            improved = True
                            found_pair = True
                            break
                        tries += 1
                        if tries >= limit_pairs:
                            break
                    if found_pair:
                        break
                if found_pair:
                    break
            if improved:
                continue

        if not improved:
            break

    return sorted(list(sel))

def snap_candidates(v):
    base = round(v, 2)
    cands = [base, round(base - 0.01, 2), round(base + 0.01, 2)]
    out = []
    seen = set()
    for x in cands:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def discretize_and_repair(circles):
    if not circles:
        return []
    ordered = sorted(circles, key=lambda c: circle_area(c[2]), reverse=True)
    snapped = []
    for x, y, d in ordered:
        placed = False
        for rx in snap_candidates(x):
            for ry in snap_candidates(y):
                if inside(rx, ry, d):
                    ok = True
                    for cx, cy, cd in snapped:
                        if sqrt((rx - cx)**2 + (ry - cy)**2) < (d + cd)/2.0 + MIN_SPACING - ATOL:
                            ok = False
                            break
                    if ok:
                        snapped.append([rx, ry, d])
                        placed = True
                        break
            if placed:
                break
        if not placed:
            best_local = None
            best_score = -float("inf")
            for _ in range(DISCRETIZE_NEIGHBOR_TRIES):
                rx = round(clamp(x + random.uniform(-0.04, 0.04), d/2.0, DOMAIN_SIZE - d/2.0), 2)
                ry = round(clamp(y + random.uniform(-0.04, 0.04), d/2.0, DOMAIN_SIZE - d/2.0), 2)
                if not inside(rx, ry, d):
                    continue
                ok = True
                for cx, cy, cd in snapped:
                    if sqrt((rx - cx)**2 + (ry - cy)**2) < (d + cd)/2.0 + MIN_SPACING - ATOL:
                        ok = False
                        break
                if ok:
                    trial = snapped + [[rx, ry, d]]
                    P, R, _ = solution_metrics(trial)
                    s = engineering_score(P, R)
                    if s > best_score:
                        best_score = s
                        best_local = [rx, ry, d]
            if best_local is not None:
                snapped.append(best_local)
    final = []
    for x, y, d in snapped:
        if not inside(x, y, d):
            continue
        ok = True
        for cx, cy, cd in final:
            if sqrt((x - cx)**2 + (y - cy)**2) < (d + cd)/2.0 + MIN_SPACING - ATOL:
                ok = False
                break
        if ok:
            final.append([round(x, 2), round(y, 2), d])
    return [(round(x, 2), round(y, 2), d) for x, y, d in final]

def solution_metrics(circles):
    total_area = 0.0
    p_area_sum = 0.0
    r_area_sum = 0.0
    for x, y, d in circles:
        area = circle_area(d)
        p_val, r_val = HOLE_TYPES[d]
        total_area += area
        p_area_sum += area * p_val
        r_area_sum += area * r_val
    if total_area <= 0.0:
        return 0.0, 0.0, 0.0
    P = C * p_area_sum / (DOMAIN_SIZE * DOMAIN_SIZE)
    R = r_area_sum / total_area
    R = max(0.0, min(100.0, R))
    porosity = total_area / (DOMAIN_SIZE * DOMAIN_SIZE)
    return P, R, porosity

def diameter_tune(circles, passes=2, alpha=OBJECTIVE_ALPHA):
    if not circles:
        return circles
    best = [list(c) for c in circles]
    base_score = engineering_score(*solution_metrics(best)[:2], alpha=alpha)
    n = len(best)
    for _ in range(max(1, int(passes))):
        improved = False
        for i in range(n):
            x, y, d0 = best[i]
            for nd in DIAMETERS:
                if nd == d0:
                    continue
                if not inside(x, y, nd):
                    continue
                ok = True
                for j, (cx, cy, cd) in enumerate(best):
                    if j == i:
                        continue
                    if sqrt((x - cx) ** 2 + (y - cy) ** 2) < (nd + cd) / 2.0 + MIN_SPACING - ATOL:
                        ok = False
                        break
                if not ok:
                    continue
                cand = [c.copy() for c in best]
                cand[i][2] = nd
                P, R, _ = solution_metrics(cand)
                s = engineering_score(P, R, alpha=alpha)
                if s > base_score + 1e-10:
                    best = cand
                    base_score = s
                    improved = True
                    break
        if not improved:
            break
    return [(c[0], c[1], c[2]) for c in best]

def construct_solution(ablation_mode="full", seed=None):
    enable_discretize = ablation_mode != "no_discretize"
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    candidates, conflicts = build_candidates_pool()
    if not candidates:
        return []

    selected_indices = tabu_search(candidates, conflicts, seed=seed, alpha=OBJECTIVE_ALPHA)

    selected_indices = local_combinatorial_improve(candidates, conflicts, selected_indices, passes=6, seed=seed, alpha=OBJECTIVE_ALPHA)

    circles = [(candidates[i]["x"], candidates[i]["y"], candidates[i]["d"]) for i in selected_indices]

    if circles:
        current = [list(c) for c in circles]
        base_score = engineering_score(*solution_metrics(current)[:2])
        for idx in range(len(current)):
            x, y, d = current[idx]
            best_local = [x, y, d]
            best_local_score = base_score
            for _ in range(6):
                nx = clamp(x + random.uniform(-0.06, 0.06), d/2.0, DOMAIN_SIZE - d/2.0)
                ny = clamp(y + random.uniform(-0.06, 0.06), d/2.0, DOMAIN_SIZE - d/2.0)
                if not inside(nx, ny, d):
                    continue
                conflict = False
                for j, (cx, cy, cd) in enumerate(current):
                    if j == idx:
                        continue
                    if sqrt((nx - cx)**2 + (ny - cy)**2) < (d + cd)/2.0 + MIN_SPACING - ATOL:
                        conflict = True
                        break
                if conflict:
                    continue
                trial = [c.copy() for c in current]
                trial[idx] = [nx, ny, d]
                P, R, _ = solution_metrics(trial)
                s = engineering_score(P, R)
                if s > best_local_score + 1e-9:
                    best_local_score = s
                    best_local = [nx, ny, d]
            current[idx] = best_local
        circles = [(c[0], c[1], c[2]) for c in current]

    circles = diameter_tune(circles, passes=2, alpha=OBJECTIVE_ALPHA)

    if enable_discretize:
        final = discretize_and_repair(circles)
    else:
        final = [(round(x, 2), round(y, 2), d) for x, y, d in circles]

    out = []
    for x, y, d in final:
        if not inside(x, y, d):
            continue
        ok = True
        for cx, cy, cd in out:
            if sqrt((x - cx)**2 + (y - cy)**2) < (d + cd)/2.0 + MIN_SPACING - ATOL:
                ok = False
                break
        if ok:
            out.append([round(x, 2), round(y, 2), d])

    return [(round(x, 2), round(y, 2), d) for x, y, d in out]

def run_experiment(seed=None, ablation_mode="full", alpha=0.5, **kwargs):
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
    set_objective_alpha(alpha)
    circles = construct_solution(ablation_mode=ablation_mode)
    return {"circles": circles, "alpha": OBJECTIVE_ALPHA}
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