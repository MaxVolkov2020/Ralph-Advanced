"""
PRD Planner - Analyzes dependencies and recommends optimal execution order
"""
import json
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, deque


@dataclass
class ExecutionPhase:
    """Represents a phase of execution"""
    phase_number: int
    stories: List[str]
    can_parallelize: bool
    rationale: str


@dataclass
class PlanningResult:
    """Result of PRD planning analysis"""
    execution_order: List[str]
    phases: List[ExecutionPhase]
    critical_path: List[str]
    critical_path_length: int
    parallelization_opportunities: List[List[str]]
    recommendations: List[str]

    def to_dict(self) -> Dict:
        return {
            "execution_order": self.execution_order,
            "phases": [asdict(p) for p in self.phases],
            "critical_path": self.critical_path,
            "critical_path_length": self.critical_path_length,
            "parallelization_opportunities": self.parallelization_opportunities,
            "recommendations": self.recommendations
        }


class PRDPlanner:
    """
    Analyzes PRD and generates optimal execution plan.

    Features:
    - Topological sort for valid execution order
    - Critical path analysis
    - Phase grouping for parallel execution
    - Recommendations for optimization
    """

    def plan(self, prd_json: str) -> PlanningResult:
        """
        Generate execution plan for PRD.

        Args:
            prd_json: PRD as JSON string

        Returns:
            PlanningResult with execution order, phases, and recommendations
        """
        try:
            prd = json.loads(prd_json)
        except json.JSONDecodeError:
            return PlanningResult(
                execution_order=[],
                phases=[],
                critical_path=[],
                critical_path_length=0,
                parallelization_opportunities=[],
                recommendations=["Error: Invalid JSON format"]
            )

        stories = prd.get("userStories", [])
        if not stories:
            return PlanningResult(
                execution_order=[],
                phases=[],
                critical_path=[],
                critical_path_length=0,
                parallelization_opportunities=[],
                recommendations=["No user stories found in PRD"]
            )

        # Build dependency graph
        graph, reverse_graph = self._build_graphs(stories)

        # Get story metadata
        story_meta = self._extract_story_metadata(stories)

        # Topological sort for execution order
        execution_order = self._topological_sort(graph)

        # Find critical path
        critical_path, cp_length = self._find_critical_path(graph, story_meta)

        # Group into phases
        phases = self._create_phases(graph, story_meta)

        # Find parallelization opportunities
        parallel_groups = self._find_parallel_groups(graph)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            stories, story_meta, phases, critical_path, parallel_groups, reverse_graph
        )

        return PlanningResult(
            execution_order=execution_order,
            phases=phases,
            critical_path=critical_path,
            critical_path_length=cp_length,
            parallelization_opportunities=parallel_groups,
            recommendations=recommendations
        )

    def _build_graphs(self, stories: List[Dict]) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """Build forward and reverse dependency graphs"""
        graph: Dict[str, List[str]] = {}
        reverse_graph: Dict[str, List[str]] = defaultdict(list)

        for story in stories:
            story_id = story.get("id")
            if not story_id:
                continue

            deps = story.get("dependencies", [])
            if not isinstance(deps, list):
                deps = []

            graph[story_id] = deps

            for dep in deps:
                reverse_graph[dep].append(story_id)

        return graph, dict(reverse_graph)

    def _extract_story_metadata(self, stories: List[Dict]) -> Dict[str, Dict]:
        """Extract metadata for each story"""
        meta = {}
        for story in stories:
            story_id = story.get("id")
            if not story_id:
                continue

            # Estimate complexity based on acceptance criteria count
            criteria = story.get("acceptanceCriteria", [])
            if len(criteria) <= 3:
                complexity = 1
            elif len(criteria) <= 6:
                complexity = 2
            else:
                complexity = 3

            meta[story_id] = {
                "title": story.get("title", ""),
                "repo": story.get("repo", ""),
                "priority": story.get("priority", 5),
                "complexity": complexity,
                "criteria_count": len(criteria)
            }

        return meta

    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """
        Kahn's algorithm for topological sort.
        Returns stories in valid execution order (dependencies first).
        """
        # Calculate in-degrees
        in_degree = defaultdict(int)
        for node in graph:
            in_degree[node]  # Initialize
            for dep in graph.get(node, []):
                # This node has one more incoming edge
                pass

        # Count how many times each node appears as a dependency
        for node in graph:
            for dep in graph.get(node, []):
                in_degree[node] += 1

        # Actually, in_degree should count dependencies, not dependents
        in_degree = {node: len(deps) for node, deps in graph.items()}

        # Start with nodes that have no dependencies
        queue = deque([node for node in graph if in_degree[node] == 0])
        result = []

        # Process nodes level by level
        remaining = dict(in_degree)

        while queue:
            node = queue.popleft()
            result.append(node)

            # For each node that depends on this one, reduce its in-degree
            for other_node, deps in graph.items():
                if node in deps and other_node not in result:
                    remaining[other_node] -= 1
                    if remaining[other_node] == 0:
                        queue.append(other_node)

        # If we couldn't process all nodes, there's a cycle
        if len(result) != len(graph):
            # Return what we have, cycle detection is done elsewhere
            for node in graph:
                if node not in result:
                    result.append(node)

        return result

    def _find_critical_path(
        self,
        graph: Dict[str, List[str]],
        story_meta: Dict[str, Dict]
    ) -> Tuple[List[str], int]:
        """
        Find the critical path (longest path through dependency graph).
        Uses complexity weights for more accurate estimation.
        """
        # Calculate longest path to each node
        dist: Dict[str, int] = {}
        parent: Dict[str, Optional[str]] = {}

        def get_weight(node: str) -> int:
            return story_meta.get(node, {}).get("complexity", 1)

        # Initialize
        for node in graph:
            dist[node] = get_weight(node)
            parent[node] = None

        # Relax edges based on topological order
        topo_order = self._topological_sort(graph)

        for node in topo_order:
            node_weight = get_weight(node)
            for dep in graph.get(node, []):
                if dep in dist:
                    new_dist = dist[dep] + node_weight
                    if new_dist > dist[node]:
                        dist[node] = new_dist
                        parent[node] = dep

        # Find the end of critical path (node with max distance)
        if not dist:
            return [], 0

        end_node = max(dist, key=dist.get)
        max_length = dist[end_node]

        # Reconstruct path
        path = []
        current = end_node
        while current:
            path.append(current)
            current = parent[current]

        path.reverse()

        return path, max_length

    def _create_phases(
        self,
        graph: Dict[str, List[str]],
        story_meta: Dict[str, Dict]
    ) -> List[ExecutionPhase]:
        """
        Group stories into execution phases.
        Stories in the same phase can potentially run in parallel.
        """
        phases = []
        remaining = set(graph.keys())
        completed: Set[str] = set()
        phase_num = 1

        while remaining:
            # Find all stories whose dependencies are complete
            ready = []
            for story_id in remaining:
                deps = graph.get(story_id, [])
                if all(dep in completed or dep not in graph for dep in deps):
                    ready.append(story_id)

            if not ready:
                # Shouldn't happen with valid DAG, but handle gracefully
                ready = list(remaining)[:1]  # Take first remaining

            # Sort ready stories by priority and repo for grouping
            ready.sort(key=lambda s: (
                story_meta.get(s, {}).get("priority", 5),
                story_meta.get(s, {}).get("repo", "")
            ))

            can_parallel = len(ready) > 1

            # Generate rationale
            if can_parallel:
                repos = set(story_meta.get(s, {}).get("repo", "") for s in ready)
                if len(repos) == 1:
                    rationale = f"Phase {phase_num}: {len(ready)} stories in same codebase can run in parallel"
                else:
                    rationale = f"Phase {phase_num}: {len(ready)} stories across {len(repos)} codebases can run in parallel"
            else:
                rationale = f"Phase {phase_num}: Sequential execution required due to dependencies"

            phases.append(ExecutionPhase(
                phase_number=phase_num,
                stories=ready,
                can_parallelize=can_parallel,
                rationale=rationale
            ))

            completed.update(ready)
            remaining -= set(ready)
            phase_num += 1

        return phases

    def _find_parallel_groups(self, graph: Dict[str, List[str]]) -> List[List[str]]:
        """
        Find groups of stories that can run in parallel.
        Stories with the same set of dependencies can run together.
        """
        dep_groups: Dict[Tuple[str, ...], List[str]] = defaultdict(list)

        for story_id, deps in graph.items():
            dep_key = tuple(sorted(deps))
            dep_groups[dep_key].append(story_id)

        # Return only groups with more than one story
        return [group for group in dep_groups.values() if len(group) > 1]

    def _generate_recommendations(
        self,
        stories: List[Dict],
        story_meta: Dict[str, Dict],
        phases: List[ExecutionPhase],
        critical_path: List[str],
        parallel_groups: List[List[str]],
        reverse_graph: Dict[str, List[str]]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # 1. Critical path recommendation
        if critical_path:
            cp_titles = [story_meta.get(s, {}).get("title", s)[:30] for s in critical_path[:3]]
            recommendations.append(
                f"CRITICAL PATH: {len(critical_path)} stories form the longest chain. "
                f"Prioritize: {' -> '.join(critical_path[:5])}{'...' if len(critical_path) > 5 else ''}"
            )

        # 2. First stories to start
        first_phase = phases[0] if phases else None
        if first_phase and first_phase.stories:
            start_stories = first_phase.stories[:3]
            recommendations.append(
                f"START WITH: {', '.join(start_stories)} - these have no dependencies"
            )

        # 3. Parallelization opportunities
        if parallel_groups:
            total_parallel = sum(len(g) for g in parallel_groups)
            recommendations.append(
                f"PARALLEL EXECUTION: {len(parallel_groups)} groups ({total_parallel} stories total) "
                f"can run simultaneously. Consider scaling agents."
            )

        # 4. Bottleneck warnings
        bottlenecks = [(story_id, len(deps))
                       for story_id, deps in reverse_graph.items()
                       if len(deps) >= 3]
        if bottlenecks:
            bottleneck_info = ", ".join(f"{s}({c} dependents)" for s, c in sorted(bottlenecks, key=lambda x: -x[1])[:3])
            recommendations.append(
                f"BOTTLENECKS: {bottleneck_info} - prioritize these to unblock other work"
            )

        # 5. Codebase distribution
        repo_counts = defaultdict(int)
        for story in stories:
            repo = story.get("repo", "unknown")
            repo_counts[repo] += 1

        if repo_counts:
            dominant_repo = max(repo_counts.items(), key=lambda x: x[1])
            if dominant_repo[1] > len(stories) * 0.6:
                recommendations.append(
                    f"WORKLOAD: '{dominant_repo[0]}' codebase has {dominant_repo[1]}/{len(stories)} stories. "
                    f"Consider assigning multiple agents to this codebase."
                )

        # 6. Phase count recommendation
        if len(phases) > 6:
            recommendations.append(
                f"OPTIMIZATION: {len(phases)} sequential phases detected. "
                f"Consider reducing dependencies to allow more parallel execution."
            )
        elif len(phases) <= 3 and len(stories) > 5:
            recommendations.append(
                f"EFFICIENT: Only {len(phases)} phases for {len(stories)} stories - good parallelization potential."
            )

        # 7. Quick wins - low complexity, no dependents
        quick_wins = []
        for story_id, meta in story_meta.items():
            deps = reverse_graph.get(story_id, [])
            if meta.get("complexity", 2) == 1 and len(deps) == 0:
                quick_wins.append(story_id)

        if quick_wins:
            recommendations.append(
                f"QUICK WINS: {', '.join(quick_wins[:3])} are low complexity with no dependents - "
                f"good candidates for early completion"
            )

        return recommendations


# Module-level planner instance
planner = PRDPlanner()
