"""
Input validation utilities.
"""

import re
from urllib.parse import urlparse


def validate_github_url(url: str) -> bool:
    """
    Validate if a URL is a valid GitHub repository URL.
    
    Args:
        url: URL string to validate
    
    Returns:
        True if valid GitHub URL, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    try:
        parsed = urlparse(url)
        
        # Check if it's a github.com URL
        if parsed.netloc not in ("github.com", "www.github.com"):
            return False
        
        # Check if path has at least owner/repo format
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) < 2:
            return False
        
        # Basic validation of owner and repo names
        owner = path_parts[0]
        repo = path_parts[1].removesuffix(".git")
        
        # GitHub username/org and repo name pattern
        pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$"
        
        if not re.match(pattern, owner) or not re.match(pattern, repo):
            return False
        
        return True
    except Exception:
        return False


def validate_repo_url(url: str) -> tuple[bool, str]:
    """
    Validate repository URL and return validation result with message.
    
    Args:
        url: URL string to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "Repository URL is required"
    
    if not isinstance(url, str):
        return False, "Repository URL must be a string"
    
    if not validate_github_url(url):
        return False, f"Invalid GitHub repository URL: {url}. Expected format: https://github.com/owner/repo"
    
    return True, ""


def parse_github_url(url: str) -> tuple[str, str]:
    """
    Parse a GitHub URL to extract owner and repo name.
    
    Args:
        url: GitHub repository URL (e.g., https://github.com/owner/repo)
    
    Returns:
        Tuple of (owner, repo_name)
    
    Raises:
        ValueError: If URL is not a valid GitHub repository URL
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")
    
    try:
        parsed = urlparse(url)
        
        # Check if it's a github.com URL
        if parsed.netloc not in ("github.com", "www.github.com"):
            raise ValueError(
                f"Invalid GitHub URL: {url}. "
                "Expected format: https://github.com/owner/repo"
            )
        
        # Extract owner and repo from path
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) < 2:
            raise ValueError(
                f"Invalid GitHub URL: {url}. "
                "Expected format: https://github.com/owner/repo"
            )
        
        owner = path_parts[0]
        repo_name = path_parts[1].removesuffix(".git")
        
        # Validate owner and repo names
        pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$"
        
        if not re.match(pattern, owner):
            raise ValueError(f"Invalid GitHub owner name: {owner}")
        
        if not re.match(pattern, repo_name):
            raise ValueError(f"Invalid GitHub repository name: {repo_name}")
        
        return owner, repo_name
    
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to parse GitHub URL: {url}. Error: {str(e)}") from e

# Made with Bob
