"""
PRD Validator - Validates PRD JSON structure and content before acceptance
"""
import json
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict


@dataclass
class ValidationError:
    """Represents a validation error or warning"""
    path: str  # JSONPath to error location
    code: str  # Error code
    message: str  # Human-readable message
    severity: str  # error, warning


@dataclass
class ValidationResult:
    """Result of PRD validation"""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": [asdict(e) for e in self.errors],
            "warnings": [asdict(w) for w in self.warnings]
        }


class PRDValidator:
    """
    Validates PRD JSON structure and content.
    Ensures PRD meets quality standards before being accepted for implementation.
    """

    # Required top-level fields in PRD
    REQUIRED_TOP_LEVEL_FIELDS = {
        "userStories": list
    }

    # Optional but recommended top-level fields
    RECOMMENDED_TOP_LEVEL_FIELDS = ["project", "feature", "branchName", "repos"]

    # Required fields for each story
    STORY_REQUIRED_FIELDS = {
        "id": str,
        "title": str,
        "description": str,
        "repo": str,
        "acceptanceCriteria": list
    }

    # Optional story fields
    STORY_OPTIONAL_FIELDS = ["priority", "status", "dependencies"]

    # Valid repo/codebase types (can be extended)
    DEFAULT_VALID_REPOS = ["backend", "mobile", "frontend", "api", "web", "ios", "android"]

    def validate(
        self,
        prd_json: str,
        project_codebases: Optional[List[str]] = None
    ) -> ValidationResult:
        """
        Full PRD validation.

        Args:
            prd_json: PRD as JSON string
            project_codebases: List of valid codebase names for the project.
                               If None, uses DEFAULT_VALID_REPOS.

        Returns:
            ValidationResult with errors and warnings
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        # Parse JSON
        try:
            prd = json.loads(prd_json)
        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    path="$",
                    code="INVALID_JSON",
                    message=f"Invalid JSON: {str(e)}",
                    severity="error"
                )],
                warnings=[]
            )

        if not isinstance(prd, dict):
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    path="$",
                    code="INVALID_FORMAT",
                    message="PRD must be a JSON object",
                    severity="error"
                )],
                warnings=[]
            )

        # Use project codebases or defaults
        valid_repos = project_codebases or self.DEFAULT_VALID_REPOS

        # Validate top-level structure
        schema_errors = self._validate_schema(prd)
        errors.extend(schema_errors)

        # Check for recommended fields
        schema_warnings = self._check_recommended_fields(prd)
        warnings.extend(schema_warnings)

        # If we have critical schema errors, return early
        if errors:
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # Validate stories
        stories = prd.get("userStories", [])

        if len(stories) == 0:
            errors.append(ValidationError(
                path="$.userStories",
                code="EMPTY_STORIES",
                message="PRD must contain at least one user story",
                severity="error"
            ))
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # Track story IDs for uniqueness check
        story_ids: Set[str] = set()

        for i, story in enumerate(stories):
            # Validate story structure
            story_errors, story_warnings = self._validate_story(story, i, valid_repos, story_ids)
            errors.extend(story_errors)
            warnings.extend(story_warnings)

            # Add to seen IDs
            story_id = story.get("id")
            if story_id:
                story_ids.add(story_id)

        # Validate dependencies
        dep_errors, dep_warnings = self._validate_dependencies(stories)
        errors.extend(dep_errors)
        warnings.extend(dep_warnings)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _validate_schema(self, prd: Dict[str, Any]) -> List[ValidationError]:
        """Validate required top-level fields"""
        errors = []

        for field, expected_type in self.REQUIRED_TOP_LEVEL_FIELDS.items():
            if field not in prd:
                errors.append(ValidationError(
                    path=f"$.{field}",
                    code="MISSING_FIELD",
                    message=f"Required field '{field}' is missing",
                    severity="error"
                ))
            elif not isinstance(prd[field], expected_type):
                errors.append(ValidationError(
                    path=f"$.{field}",
                    code="INVALID_TYPE",
                    message=f"Field '{field}' must be of type {expected_type.__name__}",
                    severity="error"
                ))

        return errors

    def _check_recommended_fields(self, prd: Dict[str, Any]) -> List[ValidationError]:
        """Check for recommended but optional fields"""
        warnings = []

        for field in self.RECOMMENDED_TOP_LEVEL_FIELDS:
            if field not in prd:
                warnings.append(ValidationError(
                    path=f"$.{field}",
                    code="MISSING_RECOMMENDED_FIELD",
                    message=f"Recommended field '{field}' is missing",
                    severity="warning"
                ))

        return warnings

    def _validate_story(
        self,
        story: Dict[str, Any],
        index: int,
        valid_repos: List[str],
        existing_ids: Set[str]
    ) -> tuple:
        """Validate a single story"""
        errors = []
        warnings = []
        path = f"$.userStories[{index}]"

        if not isinstance(story, dict):
            errors.append(ValidationError(
                path=path,
                code="INVALID_STORY_TYPE",
                message="Story must be an object",
                severity="error"
            ))
            return errors, warnings

        # Check required fields
        for field, expected_type in self.STORY_REQUIRED_FIELDS.items():
            if field not in story:
                errors.append(ValidationError(
                    path=f"{path}.{field}",
                    code="MISSING_FIELD",
                    message=f"Story missing required field '{field}'",
                    severity="error"
                ))
            elif not isinstance(story[field], expected_type):
                errors.append(ValidationError(
                    path=f"{path}.{field}",
                    code="INVALID_TYPE",
                    message=f"Story field '{field}' must be of type {expected_type.__name__}",
                    severity="error"
                ))

        # Check story ID uniqueness
        story_id = story.get("id")
        if story_id and story_id in existing_ids:
            errors.append(ValidationError(
                path=f"{path}.id",
                code="DUPLICATE_STORY_ID",
                message=f"Duplicate story ID: '{story_id}'",
                severity="error"
            ))

        # Validate repo/codebase reference
        repo = story.get("repo")
        if repo and repo not in valid_repos:
            errors.append(ValidationError(
                path=f"{path}.repo",
                code="INVALID_CODEBASE",
                message=f"Repository '{repo}' not found in valid codebases. Valid options: {valid_repos}",
                severity="error"
            ))

        # Validate acceptance criteria
        criteria = story.get("acceptanceCriteria", [])
        if isinstance(criteria, list):
            if len(criteria) == 0:
                warnings.append(ValidationError(
                    path=f"{path}.acceptanceCriteria",
                    code="EMPTY_ACCEPTANCE_CRITERIA",
                    message="Story has no acceptance criteria",
                    severity="warning"
                ))
            for j, criterion in enumerate(criteria):
                if not isinstance(criterion, str):
                    errors.append(ValidationError(
                        path=f"{path}.acceptanceCriteria[{j}]",
                        code="INVALID_CRITERION_TYPE",
                        message="Acceptance criterion must be a string",
                        severity="error"
                    ))
                elif len(criterion.strip()) < 10:
                    warnings.append(ValidationError(
                        path=f"{path}.acceptanceCriteria[{j}]",
                        code="SHORT_CRITERION",
                        message="Acceptance criterion is very short, consider adding more detail",
                        severity="warning"
                    ))

        # Validate priority if present
        priority = story.get("priority")
        if priority is not None:
            if not isinstance(priority, int):
                errors.append(ValidationError(
                    path=f"{path}.priority",
                    code="INVALID_PRIORITY_TYPE",
                    message="Priority must be an integer",
                    severity="error"
                ))
            elif priority < 1 or priority > 10:
                warnings.append(ValidationError(
                    path=f"{path}.priority",
                    code="PRIORITY_OUT_OF_RANGE",
                    message="Priority should be between 1 and 10",
                    severity="warning"
                ))

        # Validate dependencies if present
        deps = story.get("dependencies", [])
        if deps and not isinstance(deps, list):
            errors.append(ValidationError(
                path=f"{path}.dependencies",
                code="INVALID_DEPENDENCIES_TYPE",
                message="Dependencies must be an array",
                severity="error"
            ))

        # Check title length
        title = story.get("title", "")
        if isinstance(title, str) and len(title) < 10:
            warnings.append(ValidationError(
                path=f"{path}.title",
                code="SHORT_TITLE",
                message="Story title is very short, consider being more descriptive",
                severity="warning"
            ))

        # Check description length
        description = story.get("description", "")
        if isinstance(description, str) and len(description) < 30:
            warnings.append(ValidationError(
                path=f"{path}.description",
                code="SHORT_DESCRIPTION",
                message="Story description is very short, consider adding more context",
                severity="warning"
            ))

        return errors, warnings

    def _validate_dependencies(self, stories: List[Dict[str, Any]]) -> tuple:
        """Validate dependency graph for missing refs and circular deps"""
        errors = []
        warnings = []

        # Build set of all story IDs
        story_ids = {s.get("id") for s in stories if s.get("id")}

        # Build dependency graph
        graph: Dict[str, List[str]] = {}
        for story in stories:
            story_id = story.get("id")
            if story_id:
                deps = story.get("dependencies", [])
                graph[story_id] = deps if isinstance(deps, list) else []

        # Check for missing dependencies
        for story in stories:
            story_id = story.get("id")
            deps = story.get("dependencies", [])

            if not isinstance(deps, list):
                continue

            for dep_id in deps:
                if dep_id not in story_ids:
                    errors.append(ValidationError(
                        path=f"$.userStories[id={story_id}].dependencies",
                        code="MISSING_DEPENDENCY",
                        message=f"Story '{story_id}' depends on '{dep_id}' which does not exist",
                        severity="error"
                    ))

        # Check for circular dependencies
        cycles = self._find_circular_dependencies(graph)
        for cycle in cycles:
            errors.append(ValidationError(
                path="$.userStories.dependencies",
                code="CIRCULAR_DEPENDENCY",
                message=f"Circular dependency detected: {' -> '.join(cycle)}",
                severity="error"
            ))

        # Warn about deep dependency chains
        max_depth = self._calculate_max_depth(graph)
        if max_depth > 5:
            warnings.append(ValidationError(
                path="$.userStories.dependencies",
                code="DEEP_DEPENDENCY_CHAIN",
                message=f"Dependency chain depth is {max_depth}. Consider flattening dependencies.",
                severity="warning"
            ))

        return errors, warnings

    def _find_circular_dependencies(self, graph: Dict[str, List[str]]) -> List[List[str]]:
        """Detect circular dependencies using DFS"""
        cycles = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor) if neighbor in path else -1
                    if cycle_start >= 0:
                        cycle = path[cycle_start:] + [neighbor]
                        cycles.append(cycle)

            path.pop()
            rec_stack.remove(node)

        for node in graph:
            if node not in visited:
                dfs(node, [])

        return cycles

    def _calculate_max_depth(self, graph: Dict[str, List[str]]) -> int:
        """Calculate maximum dependency chain depth"""
        memo: Dict[str, int] = {}

        def depth(node: str, visited: Set[str]) -> int:
            if node in memo:
                return memo[node]
            if node in visited:
                return 0  # Cycle detected, handled elsewhere
            if node not in graph or not graph[node]:
                return 0

            visited.add(node)
            max_dep_depth = 0
            for dep in graph[node]:
                max_dep_depth = max(max_dep_depth, depth(dep, visited))
            visited.remove(node)

            memo[node] = max_dep_depth + 1
            return memo[node]

        max_depth = 0
        for node in graph:
            max_depth = max(max_depth, depth(node, set()))

        return max_depth


# Module-level validator instance
validator = PRDValidator()
