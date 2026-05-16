"""
Async GitHub API client using httpx for repository fetching and analysis.
"""

import asyncio
import base64
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import httpx

from ..config import (
    GITHUB_TOKEN,
    SKIP_FOLDERS,
    BINARY_EXTENSIONS,
    MAX_FILE_SIZE,
    MAX_FILES_TO_FETCH,
)
from .models import RepoFile, RepoMetadata, RepoTree


class GitHubClient:
    """Async GitHub API client for fetching repository data."""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the GitHub client.
        
        Args:
            token: GitHub personal access token. If not provided, uses GITHUB_TOKEN from config.
        """
        self.token = token or GITHUB_TOKEN
        if not self.token:
            raise ValueError(
                "GitHub token is required. Set GITHUB_TOKEN environment variable or pass token parameter."
            )
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.base_url = "https://api.github.com"
        self.client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(
                connect=20.0,
                read=180.0,
                write=50.0,
                pool=50.0
            ),
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10
            )
        )
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, *args):
        """Async context manager exit."""
        await self.close()
    
    def _parse_github_url(self, github_url: str) -> tuple[str, str]:
        """
        Parse a GitHub URL to extract owner and repo name.
        
        Args:
            github_url: GitHub repository URL (e.g., https://github.com/owner/repo)
        
        Returns:
            Tuple of (owner, repo_name)
        
        Raises:
            ValueError: If URL is not a valid GitHub repository URL
        """
        parsed = urlparse(github_url)
        
        # Handle github.com URLs
        if parsed.netloc in ("github.com", "www.github.com"):
            path_parts = parsed.path.strip("/").split("/")
            if len(path_parts) >= 2:
                owner = path_parts[0]
                repo = path_parts[1].removesuffix(".git")
                return owner, repo
        
        raise ValueError(
            f"Invalid GitHub URL: {github_url}. "
            "Expected format: https://github.com/owner/repo"
        )
    
    def _is_binary_file(self, path: str) -> bool:
        """Check if a file is binary based on its extension."""
        return any(path.lower().endswith(ext) for ext in BINARY_EXTENSIONS)
    
    def _should_skip_path(self, path: str) -> bool:
        """Check if a path should be skipped based on folder rules."""
        path_parts = path.split("/")
        return any(part in SKIP_FOLDERS for part in path_parts)
    
    async def get_repo_metadata(self, owner: str, repo: str) -> RepoMetadata:
        """
        Fetch repository metadata from GitHub API.
        
        Args:
            owner: Repository owner username
            repo: Repository name
        
        Returns:
            RepoMetadata object with repository information
        
        Raises:
            httpx.HTTPStatusError: If repository is not found or access is denied
        """
        url = f"{self.base_url}/repos/{owner}/{repo}"
        
        try:
            response = await self.client.get(url, headers=self.headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError(
                    "Invalid GitHub token. Please check your GITHUB_TOKEN."
                ) from e
            elif e.response.status_code == 404:
                raise ValueError(
                    f"Repository not found: {owner}/{repo}. "
                    "Please check the URL or ensure the repository is public."
                ) from e
            elif e.response.status_code in (403, 429):
                reset_time = e.response.headers.get("X-RateLimit-Reset", "unknown")
                raise ValueError(
                    f"GitHub API rate limit exceeded. "
                    f"Rate limit resets at: {reset_time}. "
                    "Please wait before retrying."
                ) from e
            else:
                raise ValueError(
                    f"Failed to fetch repository metadata: {e.response.status_code} - {e.response.text}"
                ) from e
        
        data = response.json()
        
        return RepoMetadata(
            name=data["name"],
            description=data.get("description"),
            stars=data.get("stargazers_count", 0),
            forks=data.get("forks_count", 0),
            language=data.get("language"),
            topics=data.get("topics", []),
            clone_url=data["clone_url"],
            default_branch=data["default_branch"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
        )
    
    async def get_file_tree(self, owner: str, repo: str, branch: str) -> list[dict]:
        """
        Fetch the complete file tree using GitHub's Git Trees API.
        
        Args:
            owner: Repository owner username
            repo: Repository name
            branch: Branch name to fetch tree from
        
        Returns:
            List of file objects from the tree
        
        Raises:
            ValueError: If tree cannot be fetched
        """
        tree_url = f"{self.base_url}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        
        try:
            tree_response = await self.client.get(tree_url, headers=self.headers)
            tree_response.raise_for_status()
            
            tree_data = tree_response.json()
            return tree_data.get("tree", [])
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (403, 429):
                reset_time = e.response.headers.get("X-RateLimit-Reset", "unknown")
                raise ValueError(
                    f"GitHub API rate limit exceeded. Rate limit resets at: {reset_time}"
                ) from e
            else:
                raise ValueError(
                    f"Failed to fetch file tree: {e.response.status_code}"
                ) from e
    
    async def get_file_content(self, owner: str, repo: str, path: str) -> Optional[str]:
        """
        Fetch the content of a single file from the repository.
        
        Args:
            owner: Repository owner username
            repo: Repository name
            path: File path in the repository
        
        Returns:
            File content as string, or None if file is binary or cannot be fetched
        """
        if self._is_binary_file(path):
            return None
        
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        
        try:
            response = await self.client.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Decode base64 content
            if "content" in data and data.get("encoding") == "base64":
                content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
                
                # Truncate if too long
                if len(content) > MAX_FILE_SIZE:
                    content = content[:MAX_FILE_SIZE] + "\n\n[truncated]"
                
                return content
            
            return None
        
        except (httpx.HTTPStatusError, UnicodeDecodeError, KeyError):
            # Skip files that can't be fetched or decoded
            return None
    
    async def fetch_repo(self, github_url: str) -> RepoTree:
        """
        Master method to fetch complete repository data.
        
        This method:
        1. Parses the GitHub URL
        2. Fetches repository metadata
        3. Fetches the file tree
        4. Fetches content for non-binary files concurrently (up to MAX_FILES_TO_FETCH)
        
        Args:
            github_url: GitHub repository URL
        
        Returns:
            RepoTree object with complete repository data
        
        Raises:
            ValueError: If URL is invalid or repository cannot be accessed
        """
        # Parse URL
        owner, repo_name = self._parse_github_url(github_url)
        
        # Fetch metadata
        metadata = await self.get_repo_metadata(owner, repo_name)
        
        # Fetch file tree using the default branch from metadata
        tree = await self.get_file_tree(owner, repo_name, metadata.default_branch)
        
        # Filter files to process
        files_to_process: list[tuple[str, str, int, bool]] = []
        
        for item in tree:
            # Only process blob (file) types, not trees (directories)
            if item.get("type") != "blob":
                continue
            
            path = item.get("path", "")
            
            # Skip based on folder rules
            if self._should_skip_path(path):
                continue
            
            # Check file limit
            if len(files_to_process) >= MAX_FILES_TO_FETCH:
                break
            
            # Extract file info
            name = path.split("/")[-1]
            size = item.get("size", 0)
            is_binary = self._is_binary_file(path)
            
            files_to_process.append((path, name, size, is_binary))
        
        # Fetch file contents concurrently for non-binary files
        async def fetch_file_with_info(path: str, name: str, size: int, is_binary: bool) -> RepoFile:
            content = None
            if not is_binary:
                content = await self.get_file_content(owner, repo_name, path)
            
            return RepoFile(
                path=path,
                name=name,
                content=content,
                size=size,
                is_binary=is_binary,
            )
        
        # Use asyncio.gather to fetch all files concurrently
        files = await asyncio.gather(
            *[fetch_file_with_info(path, name, size, is_binary)
              for path, name, size, is_binary in files_to_process]
        )
        
        return RepoTree(
            owner=owner,
            repo_name=repo_name,
            default_branch=metadata.default_branch,
            files=list(files),
            total_files=len(files),
            fetched_at=datetime.now(),
            metadata=metadata,
        )

# Made with Bob
