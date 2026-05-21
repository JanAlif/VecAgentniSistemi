from pogema import GridConfig

# noinspection PyUnresolvedReferences
import cppimport.import_hook
# noinspection PyUnresolvedReferences
from follower_cpp.planner import planner

from pydantic import BaseModel

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal


class PlannerConfig(BaseModel):
    use_static_cost: bool = True
    use_dynamic_cost: bool = True
    reset_dynamic_cost: bool = True

    use_corridor_penalty: bool = False
    corridor_penalty_weight: float = 1.5

    # PIBT-inspired: decay factor for dynamic occupations (0 = hard reset, 0<x<1 = decay)
    # Instead of fully resetting dynamic costs on goal change (original behavior),
    # multiply by decay_factor to preserve historical congestion memory.
    # Inspired by PIBT's priority accumulation scheme (Okumura et al., AIJ 2022).
    decay_factor: float = 0.0

    # PIBT-inspired: extra cost per nearby agent to penalize dense clusters.
    # Mirrors PIBT's focus on adjacent agent interactions and local conflict resolution.
    density_weight: float = 0.0

    # RHCR-inspired: replan interval (0 = replan every step, n>0 = replan every n steps).
    # Based on RHCR's rolling-horizon approach (Li et al., AAAI 2021) where planning
    # is done every h timesteps instead of every timestep, reducing overhead.
    replan_interval: int = 0


class Planner:
    def __init__(self, cfg: PlannerConfig):
        self.planner = None
        self.obstacles = None
        self.starts = None
        self.cfg = cfg
        # RHCR-inspired: track steps since last replan per agent
        self.steps_since_replan = None
        # RHCR-inspired: cached paths per agent
        self.cached_paths = None
        # Track previous positions to detect if agent deviated from path
        self.prev_positions = None

    def add_grid_obstacles(self, obstacles, starts):
        self.obstacles = obstacles
        self.starts = starts
        self.planner = None
        self.steps_since_replan = None
        self.cached_paths = None
        self.prev_positions = None

    def update(self, obs):
        num_agents = len(obs)
        obs_radius = len(obs[0]['obstacles']) // 2
        if self.planner is None:
            self.planner = [
                planner(
                    self.obstacles,
                    self.cfg.use_static_cost,
                    self.cfg.use_dynamic_cost,
                    self.cfg.reset_dynamic_cost,
                    self.cfg.decay_factor,
                    self.cfg.density_weight,
                )
                for _ in range(num_agents)
            ]
            for i, p in enumerate(self.planner):
                p.set_abs_start(self.starts[i])
            if self.cfg.use_static_cost:
                pen_calc = planner(self.obstacles, self.cfg.use_static_cost, self.cfg.use_dynamic_cost, self.cfg.reset_dynamic_cost)
                penalties = pen_calc.precompute_penalty_matrix(obs_radius)
    
                # Idea 6: add corridor penalty to bottleneck cells
                if self.cfg.use_corridor_penalty:
                    from follower.corridor_penalty import add_corridor_penalty
                    penalties = add_corridor_penalty(
                        penalties,
                        self.obstacles,
                        weight=self.cfg.corridor_penalty_weight,
                        obs_radius=obs_radius,
                    )
    
                for p in self.planner:
                    p.set_penalties(penalties)
            # Initialize RHCR-inspired tracking
            self.steps_since_replan = [0] * num_agents
            self.cached_paths = [None] * num_agents
            self.prev_positions = [None] * num_agents

        replan_interval = self.cfg.replan_interval

        for k in range(num_agents):
            if obs[k]['xy'] == obs[k]['target_xy']:
                self.steps_since_replan[k] = 0
                self.cached_paths[k] = None
                continue

            cur_pos = obs[k]['xy']

            # Always update dynamic occupations (cheap, and keeps congestion info fresh)
            obs[k]['agents'][obs_radius][obs_radius] = 0
            self.planner[k].update_occupations(obs[k]['agents'], (obs[k]['xy'][0] - obs_radius, obs[k]['xy'][1] - obs_radius), obs[k]['target_xy'])
            obs[k]['agents'][obs_radius][obs_radius] = 1

            # RHCR-inspired windowed replanning: only replan A* if needed
            # Based on RHCR (Li et al., AAAI 2021) idea of replanning every h timesteps
            # instead of every timestep, reducing computational overhead while
            # keeping plans adaptive to new goal locations.
            need_replan = True
            if replan_interval > 0 and self.cached_paths[k] is not None:
                # Check if agent is still following cached path
                path = self.cached_paths[k]
                on_path = any(
                    (cur_pos[0] == px and cur_pos[1] == py)
                    for px, py in path
                )
                # Replan if: agent off-path or interval elapsed
                # Note: goal changes are already handled above (target_xy == xy resets)
                # and by the C++ planner's update_h_values when goal differs.
                if on_path and self.steps_since_replan[k] < replan_interval:
                    need_replan = False

            if need_replan:
                self.planner[k].update_path(obs[k]['xy'], obs[k]['target_xy'])
                self.steps_since_replan[k] = 0
            else:
                self.steps_since_replan[k] += 1

            self.prev_positions[k] = cur_pos

    def get_path(self):
        results = []
        for idx in range(len(self.planner)):
            path = self.planner[idx].get_path()
            # Cache the path for RHCR-inspired windowed replanning
            if self.cached_paths is not None:
                self.cached_paths[idx] = list(path) if path else None
            results.append(path)
        return results


class ResettablePlanner:
    def __init__(self, cfg: PlannerConfig):
        self._cfg = cfg
        self._agent = None

    def update(self, observations):
        return self._agent.update(observations)

    def get_path(self):
        return self._agent.get_path()

    def reset_states(self, ):
        self._agent = Planner(self._cfg)