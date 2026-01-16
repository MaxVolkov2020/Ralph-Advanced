"""
Git Manager - Handles git operations for repositories
Supports authenticated operations and agent attribution
"""
import os
import re
import json
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urlunparse
from git import Repo, GitCommandError, Actor


class GitManager:
    """Manages git operations for code repositories with authentication and attribution"""

    def __init__(self, base_path: str = "/app/repos"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def _build_authenticated_url(
        self,
        repo_url: str,
        username: Optional[str] = None,
        token: Optional[str] = None
    ) -> str:
        """
        Build an authenticated git URL.

        Args:
            repo_url: Original repository URL
            username: Git username (optional, defaults to 'oauth2' for tokens)
            token: Personal access token

        Returns:
            URL with embedded credentials
        """
        if not token:
            return repo_url

        parsed = urlparse(repo_url)

        # Handle HTTPS URLs
        if parsed.scheme in ('http', 'https'):
            # Use oauth2 as default username for token auth
            auth_username = username or 'oauth2'
            # Build authenticated URL: https://username:token@host/path
            netloc = f"{auth_username}:{token}@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            return urlunparse((
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))

        # For SSH URLs, credentials are handled via SSH keys
        return repo_url

    def clone_repo(self, repo_url: str, repo_name: str) -> str:
        """
        Clone a repository (no authentication).

        Args:
            repo_url: Git repository URL
            repo_name: Local directory name

        Returns:
            Path to cloned repository
        """
        return self.clone_repo_with_auth(repo_url, repo_name)

    def clone_repo_with_auth(
        self,
        repo_url: str,
        repo_name: str,
        username: Optional[str] = None,
        token: Optional[str] = None
    ) -> str:
        """
        Clone a repository with authentication.

        Args:
            repo_url: Git repository URL
            repo_name: Local directory name
            username: Git username (optional)
            token: Personal access token (optional)

        Returns:
            Path to cloned repository
        """
        repo_path = os.path.join(self.base_path, repo_name)
        auth_url = self._build_authenticated_url(repo_url, username, token)

        if os.path.exists(repo_path):
            # Repository already exists, update remote URL and pull
            repo = Repo(repo_path)
            # Update origin URL (in case credentials changed)
            if 'origin' in [r.name for r in repo.remotes]:
                repo.remotes.origin.set_url(auth_url)
            try:
                repo.remotes.origin.pull()
            except GitCommandError:
                # Ignore pull errors on existing repos
                pass
            return repo_path

        # Clone repository with authenticated URL
        Repo.clone_from(auth_url, repo_path)
        return repo_path

    def create_branch(self, repo_name: str, branch_name: str, base_branch: str = "main") -> bool:
        """
        Create a new branch.

        Args:
            repo_name: Repository name
            branch_name: New branch name
            base_branch: Base branch to create from

        Returns:
            True if successful
        """
        repo_path = os.path.join(self.base_path, repo_name)
        repo = Repo(repo_path)

        # Checkout base branch
        try:
            repo.git.checkout(base_branch)
        except GitCommandError:
            # Try 'master' if 'main' doesn't exist
            try:
                repo.git.checkout("master")
            except GitCommandError:
                pass  # Stay on current branch

        # Pull latest
        try:
            repo.remotes.origin.pull()
        except GitCommandError:
            pass  # Ignore pull errors

        # Create and checkout new branch
        try:
            repo.git.checkout("-b", branch_name)
            return True
        except GitCommandError:
            # Branch already exists, just checkout
            try:
                repo.git.checkout(branch_name)
                return True
            except GitCommandError:
                return False

    def apply_changes(self, repo_name: str, file_changes: List[Dict[str, Any]]) -> List[str]:
        """
        Apply file changes to repository.

        Args:
            repo_name: Repository name
            file_changes: List of file change dicts with 'path', 'action', 'content'

        Returns:
            List of modified file paths
        """
        repo_path = os.path.join(self.base_path, repo_name)
        modified_files = []

        for change in file_changes:
            file_path = os.path.join(repo_path, change["path"])
            action = change["action"]
            content = change.get("content", "")

            if action == "create" or action == "update":
                # Create parent directories if needed
                parent_dir = os.path.dirname(file_path)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)

                # Write file content
                with open(file_path, "w") as f:
                    f.write(content)

                modified_files.append(change["path"])

            elif action == "delete":
                if os.path.exists(file_path):
                    os.remove(file_path)
                    modified_files.append(change["path"])

        return modified_files

    def commit(
        self,
        repo_name: str,
        message: str,
        files: Optional[List[str]] = None
    ) -> str:
        """
        Commit changes (legacy method without attribution).

        Args:
            repo_name: Repository name
            message: Commit message
            files: List of file paths to commit (None = commit all)

        Returns:
            Commit hash
        """
        repo_path = os.path.join(self.base_path, repo_name)
        repo = Repo(repo_path)

        if files:
            # Add specific files
            for file_path in files:
                repo.index.add([file_path])
        else:
            # Add all changes
            repo.git.add(A=True)

        # Commit
        commit = repo.index.commit(message)

        return commit.hexsha

    def commit_with_attribution(
        self,
        repo_name: str,
        message: str,
        agent_name: str,
        story_id: str,
        execution_id: str,
        action_summary: str,
        action_reason: str,
        files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Commit changes with full agent attribution.

        Args:
            repo_name: Repository name
            message: Brief commit message
            agent_name: Name of the agent making the commit
            story_id: Story ID being implemented
            execution_id: Execution UUID for traceability
            action_summary: What was done
            action_reason: Why it was done
            files: List of file paths to commit (None = commit all)

        Returns:
            Dict with commit details:
            - commit_hash: str
            - agent_name: str
            - agent_email: str
            - commit_message: str
            - files_changed: List[str]
        """
        repo_path = os.path.join(self.base_path, repo_name)
        repo = Repo(repo_path)

        # Create agent author identity
        agent_display_name = f"Ralph {agent_name.replace('_', ' ').title()} Agent"
        agent_email = f"{agent_name}@ralph-advanced.local"

        # Build structured commit message
        full_message = f"""[{story_id}] {message}

Agent: {agent_name}
Execution: {execution_id}

What: {action_summary}

Why: {action_reason}

Co-authored-by: {agent_display_name} <{agent_email}>"""

        # Create author/committer
        author = Actor(agent_display_name, agent_email)

        # Stage files
        if files:
            for file_path in files:
                repo.index.add([file_path])
        else:
            repo.git.add(A=True)

        # Get list of staged files before commit
        staged_files = [item.a_path for item in repo.index.diff("HEAD")]
        if not staged_files:
            # If no diff against HEAD, get untracked + modified
            staged_files = list(repo.untracked_files) + [item.a_path for item in repo.index.diff(None)]

        # Commit with author attribution
        commit = repo.index.commit(
            full_message,
            author=author,
            committer=author
        )

        return {
            "commit_hash": commit.hexsha,
            "agent_name": agent_name,
            "agent_email": agent_email,
            "commit_message": full_message,
            "files_changed": staged_files
        }

    def push(self, repo_name: str, branch_name: Optional[str] = None) -> bool:
        """
        Push commits to remote.

        Args:
            repo_name: Repository name
            branch_name: Branch to push (None = current branch)

        Returns:
            True if successful
        """
        repo_path = os.path.join(self.base_path, repo_name)
        repo = Repo(repo_path)

        origin = repo.remotes.origin

        try:
            if branch_name:
                origin.push(branch_name)
            else:
                origin.push()
            return True
        except GitCommandError as e:
            raise GitCommandError(f"Push failed: {str(e)}", status=1)

    def push_with_auth(
        self,
        repo_name: str,
        branch_name: Optional[str] = None,
        username: Optional[str] = None,
        token: Optional[str] = None
    ) -> bool:
        """
        Push commits to remote with authentication.

        Args:
            repo_name: Repository name
            branch_name: Branch to push (None = current branch)
            username: Git username
            token: Personal access token

        Returns:
            True if successful
        """
        repo_path = os.path.join(self.base_path, repo_name)
        repo = Repo(repo_path)

        # Update remote URL with credentials if provided
        if token:
            current_url = repo.remotes.origin.url
            auth_url = self._build_authenticated_url(current_url, username, token)
            repo.remotes.origin.set_url(auth_url)

        return self.push(repo_name, branch_name)

    def get_diff(self, repo_name: str, commit_hash: str) -> str:
        """
        Get diff for a commit.

        Args:
            repo_name: Repository name
            commit_hash: Commit hash

        Returns:
            Diff text
        """
        repo_path = os.path.join(self.base_path, repo_name)
        repo = Repo(repo_path)

        commit = repo.commit(commit_hash)
        parent = commit.parents[0] if commit.parents else None
        diffs = commit.diff(parent, create_patch=True)

        diff_text = ""
        for diff in diffs:
            diff_text += f"--- {diff.a_path}\n+++ {diff.b_path}\n"
            if diff.diff:
                diff_text += diff.diff.decode('utf-8', errors='replace')
            diff_text += "\n"

        return diff_text

    def get_changed_files(self, repo_name: str, commit_hash: str) -> List[str]:
        """
        Get list of changed files in a commit.

        Args:
            repo_name: Repository name
            commit_hash: Commit hash

        Returns:
            List of file paths
        """
        repo_path = os.path.join(self.base_path, repo_name)
        repo = Repo(repo_path)

        commit = repo.commit(commit_hash)

        if commit.parents:
            diffs = commit.diff(commit.parents[0])
        else:
            diffs = commit.diff(None)

        return [diff.a_path or diff.b_path for diff in diffs]

    def get_commit_info(self, repo_name: str, commit_hash: str) -> Dict[str, Any]:
        """
        Get detailed information about a commit.

        Args:
            repo_name: Repository name
            commit_hash: Commit hash

        Returns:
            Dict with commit details
        """
        repo_path = os.path.join(self.base_path, repo_name)
        repo = Repo(repo_path)

        commit = repo.commit(commit_hash)

        return {
            "hash": commit.hexsha,
            "short_hash": commit.hexsha[:8],
            "message": commit.message,
            "author_name": commit.author.name,
            "author_email": commit.author.email,
            "timestamp": commit.committed_datetime.isoformat(),
            "files_changed": self.get_changed_files(repo_name, commit_hash)
        }

    def test_connection(
        self,
        repo_url: str,
        username: Optional[str] = None,
        token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Test connection to a repository.

        Args:
            repo_url: Repository URL
            username: Git username
            token: Personal access token

        Returns:
            Dict with connection test results
        """
        import tempfile
        import shutil

        auth_url = self._build_authenticated_url(repo_url, username, token)

        # Create temporary directory for test clone
        temp_dir = tempfile.mkdtemp()

        try:
            # Attempt to clone with depth=1 (shallow clone for speed)
            repo = Repo.clone_from(auth_url, temp_dir, depth=1)

            # Get branch info
            branches = [ref.name.replace('origin/', '') for ref in repo.remotes.origin.refs]
            default_branch = repo.active_branch.name if repo.head.is_valid() else None

            return {
                "success": True,
                "message": "Successfully connected to repository",
                "branch_count": len(branches),
                "default_branch": default_branch
            }

        except GitCommandError as e:
            error_msg = str(e)
            if "Authentication failed" in error_msg or "401" in error_msg:
                return {
                    "success": False,
                    "message": "Authentication failed. Check your credentials.",
                    "branch_count": None,
                    "default_branch": None
                }
            elif "not found" in error_msg.lower() or "404" in error_msg:
                return {
                    "success": False,
                    "message": "Repository not found. Check the URL.",
                    "branch_count": None,
                    "default_branch": None
                }
            else:
                return {
                    "success": False,
                    "message": f"Connection failed: {error_msg}",
                    "branch_count": None,
                    "default_branch": None
                }

        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)
