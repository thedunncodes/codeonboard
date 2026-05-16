"""
Pydantic models for GitHub repository data structures.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class RepoFile(BaseModel):
    """Represents a single file in a repository."""
    
    path: str = Field(..., description="Full path to the file in the repository")
    name: str = Field(..., description="File name")
    content: Optional[str] = Field(None, description="File content (None for binary files)")
    size: int = Field(..., description="File size in bytes")
    is_binary: bool = Field(default=False, description="Whether the file is binary")


class RepoTree(BaseModel):
    """Represents the complete file tree of a repository."""
    
    owner: str = Field(..., description="Repository owner username")
    repo_name: str = Field(..., description="Repository name")
    default_branch: str = Field(..., description="Default branch name (e.g., 'main', 'master')")
    files: list[RepoFile] = Field(default_factory=list, description="List of files in the repository")
    total_files: int = Field(..., description="Total number of files fetched")
    fetched_at: datetime = Field(default_factory=datetime.now, description="Timestamp when the tree was fetched")
    metadata: Optional["RepoMetadata"] = Field(None, description="Repository metadata")


class RepoMetadata(BaseModel):
    """Represents repository metadata from GitHub API."""
    
    name: str = Field(..., description="Repository name")
    description: Optional[str] = Field(None, description="Repository description")
    stars: int = Field(default=0, description="Number of stars")
    forks: int = Field(default=0, description="Number of forks")
    language: Optional[str] = Field(None, description="Primary programming language")
    topics: list[str] = Field(default_factory=list, description="Repository topics/tags")
    clone_url: str = Field(..., description="Git clone URL")
    default_branch: str = Field(..., description="Default branch name (e.g., 'main', 'master')")
    created_at: datetime = Field(..., description="Repository creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

# Made with Bob
