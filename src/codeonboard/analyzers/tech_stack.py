"""
Tech stack builder module for creating comprehensive project summaries.
"""

from typing import Dict, List, Optional

from ..github.models import RepoFile, RepoMetadata


def build_tech_stack(
    metadata: RepoMetadata,
    files: List[RepoFile],
    dependencies: Dict[str, List[str]],
    frameworks: Dict[str, List[str]]
) -> Dict:
    """
    Build a comprehensive tech stack summary from all analysis data.
    
    Args:
        metadata: Repository metadata from GitHub
        files: List of RepoFile objects
        dependencies: Dependencies dictionary from detect_dependencies()
        frameworks: Frameworks dictionary from detect_frameworks()
    
    Returns:
        Dictionary with complete tech stack information
    """
    return {
        "primary_language": metadata.language or "Unknown",
        "all_languages": _detect_languages(files),
        "frameworks": frameworks,
        "dependencies": dependencies,
        "has_tests": _has_tests(files),
        "has_docker": _has_docker(files),
        "has_ci": _has_ci(files),
        "total_files": len(files),
        "architecture": _detect_architecture(files),
    }


def _detect_languages(files: List[RepoFile]) -> List[str]:
    """Detect all programming languages from file extensions."""
    extension_map = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".jsx": "JavaScript",
        ".tsx": "TypeScript",
        ".java": "Java",
        ".go": "Go",
        ".rs": "Rust",
        ".rb": "Ruby",
        ".php": "PHP",
        ".c": "C",
        ".cpp": "C++",
        ".cs": "C#",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".scala": "Scala",
        ".r": "R",
        ".sql": "SQL",
        ".sh": "Shell",
        ".html": "HTML",
        ".css": "CSS",
        ".scss": "SCSS",
        ".vue": "Vue",
        ".svelte": "Svelte",
    }
    
    languages = set()
    for file in files:
        for ext, lang in extension_map.items():
            if file.path.lower().endswith(ext):
                languages.add(lang)
                break
    
    return sorted(list(languages))


def _has_tests(files: List[RepoFile]) -> bool:
    """Check if the repository has test files."""
    test_indicators = ["/test", "/tests", "/spec", "__tests__", "test_", "_test.", ".test.", ".spec."]
    
    for file in files:
        path_lower = file.path.lower()
        if any(indicator in path_lower for indicator in test_indicators):
            return True
    
    return False


def _has_docker(files: List[RepoFile]) -> bool:
    """Check if the repository uses Docker."""
    docker_files = ["dockerfile", "docker-compose.yml", "docker-compose.yaml", ".dockerignore"]
    
    for file in files:
        if file.name.lower() in docker_files:
            return True
    
    return False


def _has_ci(files: List[RepoFile]) -> bool:
    """Check if the repository has CI/CD configuration."""
    ci_indicators = [
        ".github/workflows",
        ".gitlab-ci.yml",
        ".circleci",
        "jenkinsfile",
        ".travis.yml",
        "azure-pipelines.yml",
    ]
    
    for file in files:
        path_lower = file.path.lower()
        if any(indicator in path_lower for indicator in ci_indicators):
            return True
    
    return False


def _detect_architecture(files: List[RepoFile]) -> str:
    """Detect project architecture type."""
    # Check for monorepo by looking for multiple package.json files at different depths
    package_json_files = [f for f in files if f.name == "package.json"]
    
    if len(package_json_files) > 1:
        # Check if they're at different directory levels
        depths = set()
        for file in package_json_files:
            depth = file.path.count("/")
            depths.add(depth)
        
        if len(depths) > 1:
            return "monorepo"
    
    return "standard"

# Made with Bob
