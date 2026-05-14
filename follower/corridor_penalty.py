"""
Idea 6: Corridor penalty for FOLLOWER's heuristic path planner.

Identifies "passage" cells — free cells in 1-wide corridors — and adds an
additive penalty on top of the existing static cost. The intent is to make
A* prefer wider, less-bottlenecked routes when alternatives of similar
length exist.

A free cell is a passage cell if it has exactly two free neighbors AND those
neighbors are opposite each other (vertically or horizontally). This catches
the cells that make up narrow corridors without needing a full articulation-
point detection.

Computed once per map at reset time. Pure Python; no C++ changes.
"""

import numpy as np


def _is_passage_cell(grid, i, j, H, W):
    """True iff (i, j) is a free cell with exactly two opposite free neighbors."""
    if grid[i][j] != 0:
        return False

    up    = (i > 0)       and grid[i - 1][j] == 0
    down  = (i < H - 1)   and grid[i + 1][j] == 0
    left  = (j > 0)       and grid[i][j - 1] == 0
    right = (j < W - 1)   and grid[i][j + 1] == 0

    vertical   = up and down and not left and not right
    horizontal = left and right and not up and not down
    return vertical or horizontal


def compute_passage_mask(obstacles, obs_radius=0):
    """Return a boolean mask marking 1-wide-corridor cells.

    Parameters
    ----------
    obstacles : list[list[int]] or np.ndarray
        Map grid. 0 = free, 1 = obstacle.
    obs_radius : int
        Margin around the grid border to skip. The C++ planner leaves an
        `obs_radius`-wide border, so we don't penalize cells there either.

    Returns
    -------
    mask : np.ndarray of shape (H, W), dtype bool
        True at passage cells, False elsewhere.
    """
    if isinstance(obstacles, np.ndarray):
        grid = obstacles
    else:
        grid = np.asarray(obstacles)

    H, W = grid.shape
    mask = np.zeros((H, W), dtype=bool)

    lo = max(obs_radius, 1)
    hi_i = H - max(obs_radius, 1)
    hi_j = W - max(obs_radius, 1)

    for i in range(lo, hi_i):
        for j in range(lo, hi_j):
            if _is_passage_cell(grid, i, j, H, W):
                mask[i, j] = True

    return mask


def add_corridor_penalty(base_penalties, obstacles, weight, obs_radius=0):
    """Return `base_penalties` with `weight` added at every passage cell.

    `base_penalties` is the matrix returned by the C++ planner's
    `precompute_penalty_matrix`, which arrives as a list-of-lists. We
    convert to numpy, add the corridor term, and return as list-of-lists
    so it round-trips cleanly through pybind11's `set_penalties`.
    """
    base = np.asarray(base_penalties, dtype=np.float32)
    mask = compute_passage_mask(obstacles, obs_radius=obs_radius)
    base = base + (mask.astype(np.float32) * float(weight))
    return base.tolist()