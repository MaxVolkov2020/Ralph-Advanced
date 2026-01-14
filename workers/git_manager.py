"""
Git Manager - Handles git operations for repositories
"""
import os
import json
from typing import List, Dict, Any, Optional
from git import Repo, GitCommandError


class GitManager:
    """Manages git operations for code repositories"""
    
    def __init__(self, base_path: str = "/app/repos"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
    
    def clone_repo(self, repo_url: str, repo_name: str) -> str:
        """
        Clone a repository
        
        Args:
            repo_url: Git repository URL
            repo_name: Local directory name
        
        Returns:
            Path to cloned repository
        """
        repo_path = os.path.join(self.base_path, repo_name)
        
        if os.path.exists(repo_path):
            # Repository already exists, pull latest
            repo = Repo(repo_path)
            origin = repo.remotes.origin
            origin.pull()
            return repo_path
        
        # Clone repository
        Repo.clone_from(repo_url, repo_path)
        return repo_path
    
    def create_branch(self, repo_name: str, branch_name: str, base_branch: str = "main") -> bool:
        """
        Create a new branch
        
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
            repo.git.checkout("master")
        
        # Pull latest
        repo.remotes.origin.pull()
        
        # Create and checkout new branch
        try:
            repo.git.checkout("-b", branch_name)
            return True
        except GitCommandError:
            # Branch already exists, just checkout
            repo.git.checkout(branch_name)
            return True
    
    def apply_changes(self, repo_name: str, file_changes: List[Dict[str, Any]]) -> List[str]:
        """
        Apply file changes to repository
        
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
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
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
        Commit changes
        
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
    
    def push(self, repo_name: str, branch_name: Optional[str] = None) -> bool:
        """
        Push commits to remote
        
        Args:
            repo_name: Repository name
            branch_name: Branch to push (None = current branch)
        
        Returns:
            True if successful
        """
        repo_path = os.path.join(self.base_path, repo_name)
        repo = Repo(repo_path)
        
        origin = repo.remotes.origin
        
        if branch_name:
            origin.push(branch_name)
        else:
            origin.push()
        
        return True
    
    def get_diff(self, repo_name: str, commit_hash: str) -> str:
        """
        Get diff for a commit
        
        Args:
            repo_name: Repository name
            commit_hash: Commit hash
        
        Returns:
            Diff text
        """
        repo_path = os.path.join(self.base_path, repo_name)
        repo = Repo(repo_path)
        
        commit = repo.commit(commit_hash)
        return commit.diff(commit.parents[0] if commit.parents else None, create_patch=True)
    
    def get_changed_files(self, repo_name: str, commit_hash: str) -> List[str]:
        """
        Get list of changed files in a commit
        
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
        
        return [diff.a_path for diff in diffs]
