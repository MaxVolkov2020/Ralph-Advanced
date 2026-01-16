"""
PRD Quality Evaluator - Scores PRD quality and provides improvement suggestions
"""
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class QualityIssue:
    """Represents a quality issue found in the PRD"""
    category: str  # clarity, dependencies, feasibility
    story_id: Optional[str]
    issue: str
    suggestion: str
    impact: int  # Points deducted


@dataclass
class QualityBreakdown:
    """Score breakdown by category"""
    clarity: int  # 0-100
    dependencies: int  # 0-100
    feasibility: int  # 0-100


@dataclass
class QualityResult:
    """Result of PRD quality evaluation"""
    score: int  # 0-100
    grade: str  # A, B, C, D, F
    issues: List[QualityIssue]
    breakdown: QualityBreakdown

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "grade": self.grade,
            "issues": [asdict(i) for i in self.issues],
            "breakdown": asdict(self.breakdown)
        }


class PRDQualityEvaluator:
    """
    Evaluates PRD quality and provides a score with actionable suggestions.

    Scoring Categories:
    - Clarity (40%): Title, description, and acceptance criteria quality
    - Dependencies (30%): Dependency structure and parallelization potential
    - Feasibility (30%): Implementation complexity and scope
    """

    WEIGHTS = {
        "clarity": 40,
        "dependencies": 30,
        "feasibility": 30
    }

    # Minimum lengths for quality scoring
    MIN_TITLE_LENGTH = 15
    MIN_DESCRIPTION_LENGTH = 50
    MIN_CRITERIA_COUNT = 2
    MIN_CRITERION_LENGTH = 20

    # Scope creep indicators
    SCOPE_CREEP_KEYWORDS = [
        "and also", "additionally", "plus", "as well as",
        "while we're at it", "might as well", "along with"
    ]

    # Technical complexity indicators
    COMPLEXITY_KEYWORDS = {
        "high": ["database migration", "schema change", "breaking change", "refactor", "architecture"],
        "medium": ["api endpoint", "authentication", "validation", "integration"],
        "low": ["ui change", "text update", "style change", "bug fix"]
    }

    def evaluate(self, prd_json: str) -> QualityResult:
        """
        Evaluate PRD quality.

        Args:
            prd_json: PRD as JSON string

        Returns:
            QualityResult with score, grade, and issues
        """
        try:
            prd = json.loads(prd_json)
        except json.JSONDecodeError:
            return QualityResult(
                score=0,
                grade="F",
                issues=[QualityIssue(
                    category="clarity",
                    story_id=None,
                    issue="Invalid JSON format",
                    suggestion="Ensure PRD is valid JSON",
                    impact=100
                )],
                breakdown=QualityBreakdown(clarity=0, dependencies=0, feasibility=0)
            )

        stories = prd.get("userStories", [])
        if not stories:
            return QualityResult(
                score=0,
                grade="F",
                issues=[QualityIssue(
                    category="clarity",
                    story_id=None,
                    issue="No user stories found",
                    suggestion="Add at least one user story to the PRD",
                    impact=100
                )],
                breakdown=QualityBreakdown(clarity=0, dependencies=0, feasibility=0)
            )

        issues: List[QualityIssue] = []

        # Evaluate each category
        clarity_score, clarity_issues = self._evaluate_clarity(stories)
        issues.extend(clarity_issues)

        dep_score, dep_issues = self._evaluate_dependencies(stories)
        issues.extend(dep_issues)

        feas_score, feas_issues = self._evaluate_feasibility(stories)
        issues.extend(feas_issues)

        # Calculate weighted score
        breakdown = QualityBreakdown(
            clarity=clarity_score,
            dependencies=dep_score,
            feasibility=feas_score
        )

        total_score = (
            breakdown.clarity * (self.WEIGHTS["clarity"] / 100) +
            breakdown.dependencies * (self.WEIGHTS["dependencies"] / 100) +
            breakdown.feasibility * (self.WEIGHTS["feasibility"] / 100)
        )

        grade = self._score_to_grade(total_score)

        return QualityResult(
            score=round(total_score),
            grade=grade,
            issues=issues,
            breakdown=breakdown
        )

    def _evaluate_clarity(self, stories: List[Dict[str, Any]]) -> Tuple[int, List[QualityIssue]]:
        """Evaluate story clarity"""
        score = 100
        issues = []
        points_per_story = 100 / max(len(stories), 1)

        for story in stories:
            story_id = story.get("id", "unknown")

            # Title quality
            title = story.get("title", "")
            if len(title) < self.MIN_TITLE_LENGTH:
                deduction = min(5, points_per_story * 0.15)
                score -= deduction
                issues.append(QualityIssue(
                    category="clarity",
                    story_id=story_id,
                    issue=f"Title is too short ({len(title)} chars)",
                    suggestion=f"Use descriptive titles of at least {self.MIN_TITLE_LENGTH} characters that explain the user goal",
                    impact=round(deduction)
                ))

            # Check if title follows user story format
            if not self._is_user_story_format(title):
                deduction = min(3, points_per_story * 0.1)
                score -= deduction
                issues.append(QualityIssue(
                    category="clarity",
                    story_id=story_id,
                    issue="Title doesn't follow user story format",
                    suggestion="Consider using format: 'As a [user], I want [goal] so that [benefit]'",
                    impact=round(deduction)
                ))

            # Description quality
            description = story.get("description", "")
            if len(description) < self.MIN_DESCRIPTION_LENGTH:
                deduction = min(10, points_per_story * 0.25)
                score -= deduction
                issues.append(QualityIssue(
                    category="clarity",
                    story_id=story_id,
                    issue=f"Description lacks detail ({len(description)} chars)",
                    suggestion=f"Include context, user persona, expected behavior, and edge cases. Aim for at least {self.MIN_DESCRIPTION_LENGTH} characters.",
                    impact=round(deduction)
                ))

            # Acceptance criteria quality
            criteria = story.get("acceptanceCriteria", [])
            if len(criteria) < self.MIN_CRITERIA_COUNT:
                deduction = min(10, points_per_story * 0.25)
                score -= deduction
                issues.append(QualityIssue(
                    category="clarity",
                    story_id=story_id,
                    issue=f"Insufficient acceptance criteria ({len(criteria)} criteria)",
                    suggestion=f"Include at least {self.MIN_CRITERIA_COUNT} specific, testable criteria per story",
                    impact=round(deduction)
                ))

            # Check individual criteria quality
            for i, criterion in enumerate(criteria):
                if isinstance(criterion, str) and len(criterion) < self.MIN_CRITERION_LENGTH:
                    deduction = min(3, points_per_story * 0.08)
                    score -= deduction
                    issues.append(QualityIssue(
                        category="clarity",
                        story_id=story_id,
                        issue=f"Acceptance criterion {i+1} is vague",
                        suggestion="Make criteria specific and testable with clear success conditions",
                        impact=round(deduction)
                    ))

        return max(0, round(score)), issues

    def _evaluate_dependencies(self, stories: List[Dict[str, Any]]) -> Tuple[int, List[QualityIssue]]:
        """Evaluate dependency structure"""
        score = 100
        issues = []

        # Build dependency counts
        dep_counts = {}
        reverse_deps = defaultdict(list)  # Who depends on this story

        for story in stories:
            story_id = story.get("id")
            deps = story.get("dependencies", [])
            if not isinstance(deps, list):
                deps = []
            dep_counts[story_id] = len(deps)
            for dep in deps:
                reverse_deps[dep].append(story_id)

        # Check for over-dependency
        for story in stories:
            story_id = story.get("id")
            dep_count = dep_counts.get(story_id, 0)

            if dep_count > 5:
                deduction = 10
                score -= deduction
                issues.append(QualityIssue(
                    category="dependencies",
                    story_id=story_id,
                    issue=f"Story has {dep_count} dependencies - too many",
                    suggestion="Consider breaking into smaller stories or reducing coupling between stories",
                    impact=deduction
                ))

        # Check for bottleneck stories (many stories depend on one)
        for story_id, dependents in reverse_deps.items():
            if len(dependents) > 3:
                deduction = 8
                score -= deduction
                issues.append(QualityIssue(
                    category="dependencies",
                    story_id=story_id,
                    issue=f"Story is a bottleneck - {len(dependents)} other stories depend on it",
                    suggestion="Consider splitting this story or implementing it early in the sprint",
                    impact=deduction
                ))

        # Check for parallelization opportunities
        stories_without_deps = sum(1 for c in dep_counts.values() if c == 0)
        if stories_without_deps == 0 and len(stories) > 1:
            deduction = 15
            score -= deduction
            issues.append(QualityIssue(
                category="dependencies",
                story_id=None,
                issue="No stories can run in parallel - all have dependencies",
                suggestion="Design some stories to be independent for parallel execution by different agents",
                impact=deduction
            ))
        elif stories_without_deps == 1 and len(stories) > 3:
            deduction = 8
            score -= deduction
            issues.append(QualityIssue(
                category="dependencies",
                story_id=None,
                issue="Limited parallelization - only 1 story can start independently",
                suggestion="Consider redesigning dependencies to allow more parallel work",
                impact=deduction
            ))

        # Check dependency chain depth
        max_depth = self._calculate_dependency_depth(stories)
        if max_depth > 5:
            deduction = 10
            score -= deduction
            issues.append(QualityIssue(
                category="dependencies",
                story_id=None,
                issue=f"Deep dependency chain (depth: {max_depth})",
                suggestion="Long chains increase risk. Consider flattening the dependency structure.",
                impact=deduction
            ))

        return max(0, round(score)), issues

    def _evaluate_feasibility(self, stories: List[Dict[str, Any]]) -> Tuple[int, List[QualityIssue]]:
        """Evaluate implementation feasibility"""
        score = 100
        issues = []

        # Track complexity distribution
        complexity_counts = {"high": 0, "medium": 0, "low": 0}
        total_criteria = 0

        for story in stories:
            story_id = story.get("id")
            description = story.get("description", "").lower()
            title = story.get("title", "").lower()
            full_text = f"{title} {description}"

            # Check for scope creep indicators
            for keyword in self.SCOPE_CREEP_KEYWORDS:
                if keyword in full_text:
                    deduction = 5
                    score -= deduction
                    issues.append(QualityIssue(
                        category="feasibility",
                        story_id=story_id,
                        issue=f"Possible scope creep detected ('{keyword}')",
                        suggestion="Split into multiple focused stories for cleaner implementation",
                        impact=deduction
                    ))
                    break

            # Estimate complexity
            complexity = self._estimate_complexity(full_text)
            complexity_counts[complexity] += 1

            # Check story size (too many acceptance criteria)
            criteria = story.get("acceptanceCriteria", [])
            total_criteria += len(criteria)
            if len(criteria) > 8:
                deduction = 10
                score -= deduction
                issues.append(QualityIssue(
                    category="feasibility",
                    story_id=story_id,
                    issue=f"Story is too large ({len(criteria)} acceptance criteria)",
                    suggestion="Break into smaller, focused stories of 3-6 criteria each",
                    impact=deduction
                ))

            # Check for vague implementation requirements
            vague_terms = ["etc", "and more", "similar", "appropriate", "suitable"]
            for term in vague_terms:
                if term in full_text:
                    deduction = 3
                    score -= deduction
                    issues.append(QualityIssue(
                        category="feasibility",
                        story_id=story_id,
                        issue=f"Vague requirement term detected ('{term}')",
                        suggestion="Be specific about all requirements to avoid implementation ambiguity",
                        impact=deduction
                    ))
                    break

        # Check complexity distribution
        if complexity_counts["high"] > len(stories) * 0.5:
            deduction = 10
            score -= deduction
            issues.append(QualityIssue(
                category="feasibility",
                story_id=None,
                issue="High concentration of complex stories",
                suggestion="Consider breaking down complex stories or spreading them across sprints",
                impact=deduction
            ))

        # Check average criteria per story
        avg_criteria = total_criteria / max(len(stories), 1)
        if avg_criteria > 6:
            deduction = 8
            score -= deduction
            issues.append(QualityIssue(
                category="feasibility",
                story_id=None,
                issue=f"High average acceptance criteria per story ({avg_criteria:.1f})",
                suggestion="Stories with many criteria are harder to implement. Aim for 3-5 criteria per story.",
                impact=deduction
            ))

        return max(0, round(score)), issues

    def _is_user_story_format(self, title: str) -> bool:
        """Check if title follows user story format"""
        user_story_patterns = [
            r"as a.*i want",
            r"as an.*i want",
            r"^add\s",
            r"^create\s",
            r"^implement\s",
            r"^update\s",
            r"^fix\s"
        ]
        title_lower = title.lower()
        return any(re.search(pattern, title_lower) for pattern in user_story_patterns)

    def _estimate_complexity(self, text: str) -> str:
        """Estimate story complexity based on keywords"""
        text_lower = text.lower()

        for keyword in self.COMPLEXITY_KEYWORDS["high"]:
            if keyword in text_lower:
                return "high"

        for keyword in self.COMPLEXITY_KEYWORDS["medium"]:
            if keyword in text_lower:
                return "medium"

        return "low"

    def _calculate_dependency_depth(self, stories: List[Dict[str, Any]]) -> int:
        """Calculate maximum dependency chain depth"""
        graph = {}
        for story in stories:
            story_id = story.get("id")
            deps = story.get("dependencies", [])
            graph[story_id] = deps if isinstance(deps, list) else []

        memo = {}

        def depth(node: str, visited: set) -> int:
            if node in memo:
                return memo[node]
            if node in visited:
                return 0  # Cycle
            if node not in graph or not graph[node]:
                return 0

            visited.add(node)
            max_d = 0
            for dep in graph[node]:
                max_d = max(max_d, depth(dep, visited))
            visited.remove(node)

            memo[node] = max_d + 1
            return memo[node]

        max_depth = 0
        for node in graph:
            max_depth = max(max_depth, depth(node, set()))

        return max_depth

    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"


# Module-level evaluator instance
evaluator = PRDQualityEvaluator()
