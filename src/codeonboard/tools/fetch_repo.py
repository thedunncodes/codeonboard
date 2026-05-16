"""
MCP tool for fetching and analyzing GitHub repositories.
"""

from ..analyzers.dependencies import detect_dependencies
from ..analyzers.framework import detect_frameworks
from ..analyzers.tech_stack import build_tech_stack
from ..github.client import GitHubClient
from ..storage.context_store import ContextStore
from ..utils.validators import validate_repo_url, parse_github_url


async def fetch_repo_tool(repo_url: str) -> dict:
    """
    Fetch and analyze a GitHub repository.
    
    This tool:
    1. Validates the repository URL
    2. Checks cache first (returns immediately if cached and not expired)
    3. If not cached: fetches repo, analyzes dependencies/frameworks/tech stack
    4. Saves everything to cache
    5. Returns comprehensive repository information
    
    Args:
        repo_url: GitHub repository URL (e.g., https://github.com/owner/repo)
    
    Returns:
        Dictionary with repository information and analysis results
    """
    try:
        # Validate URL
        is_valid, error_msg = validate_repo_url(repo_url)
        if not is_valid:
            return {
                "success": False,
                "error": error_msg
            }
        
        # Extract repo_key (owner/repo)
        owner, repo_name = parse_github_url(repo_url)
        repo_key = f"{owner}/{repo_name}"
        
        # Check cache first
        store = ContextStore()
        cached_data = store.get(repo_key)
        
        if cached_data:
            context = cached_data["context"]
            tech_stack = cached_data["tech_stack"]
            metadata_dict = tech_stack.get("_metadata", {})
            
            return {
                "success": True,
                "cached": True,
                "repo_key": repo_key,
                "repo_url": repo_url,
                "owner": context["owner"],
                "repo_name": context["repo_name"],
                "metadata": {
                    "stars": metadata_dict.get("stars", 0),
                    "forks": metadata_dict.get("forks", 0),
                    "language": metadata_dict.get("language", tech_stack.get("primary_language", "Unknown")),
                    "description": metadata_dict.get("description"),
                    "topics": metadata_dict.get("topics", [])
                },
                "tech_stack": tech_stack,
                "total_files": context["total_files"],
                "file_list": [f["path"] for f in context.get("files", [])],
                "message": "Repository data retrieved from cache"
            }
        
        # Not cached - fetch from GitHub
        async with GitHubClient() as client:
            # Fetch repository data (metadata is now included in repo_tree)
            repo_tree = await client.fetch_repo(repo_url)
        
        # Get metadata from repo_tree
        metadata = repo_tree.metadata
        if not metadata:
            return {
                "success": False,
                "error": "Failed to fetch repository metadata"
            }
        
        # Run analysis
        dependencies = detect_dependencies(repo_tree.files)
        frameworks = detect_frameworks(repo_tree.files, dependencies)
        tech_stack = build_tech_stack(metadata, repo_tree.files, dependencies, frameworks)
        
        # Add metadata to tech_stack for caching
        tech_stack["_metadata"] = {
            "stars": metadata.stars,
            "forks": metadata.forks,
            "language": metadata.language,
            "description": metadata.description,
            "topics": metadata.topics
        }
        
        # Save to cache
        store.save(repo_key, repo_url, repo_tree, tech_stack)
        
        return {
            "success": True,
            "cached": False,
            "repo_key": repo_key,
            "repo_url": repo_url,
            "owner": repo_tree.owner,
            "repo_name": repo_tree.repo_name,
            "metadata": {
                "stars": metadata.stars,
                "forks": metadata.forks,
                "language": metadata.language,
                "description": metadata.description,
                "topics": metadata.topics
            },
            "tech_stack": tech_stack,
            "total_files": repo_tree.total_files,
            "file_list": [f.path for f in repo_tree.files],
            "message": "Repository fetched and analyzed successfully"
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to fetch repository: {str(e)}"
        }

# Made with Bob
