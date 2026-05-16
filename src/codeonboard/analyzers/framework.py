"""
Framework detection module for identifying project frameworks and tools.
"""

from typing import Dict, List

from ..github.models import RepoFile


def detect_frameworks(files: List[RepoFile], dependencies: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Detect frameworks and tools used in the project.
    
    Args:
        files: List of RepoFile objects from the repository
        dependencies: Dictionary of dependencies from detect_dependencies()
    
    Returns:
        Dictionary with categories: frontend, backend, database, testing, build_tools
    """
    result = {
        "frontend": [],
        "backend": [],
        "database": [],
        "testing": [],
        "build_tools": [],
    }
    
    # Collect all dependency names for easier checking
    all_deps = []
    for deps_list in dependencies.values():
        all_deps.extend([dep.lower() for dep in deps_list])
    
    # Collect all file names for config file detection
    file_names = {file.name.lower() for file in files}
    
    # Frontend frameworks
    if "react" in all_deps or "react-dom" in all_deps:
        result["frontend"].append("React")
    if "vue" in all_deps or "@vue/cli" in all_deps:
        result["frontend"].append("Vue")
    if "@angular/core" in all_deps or "angular" in all_deps:
        result["frontend"].append("Angular")
    if "svelte" in all_deps:
        result["frontend"].append("Svelte")
    if ("next.config.js" in file_names or "next.config.ts" in file_names) or ("next" in all_deps and "react" in all_deps):
        result["frontend"].append("Next.js")
    
    # Backend frameworks
    if "fastapi" in all_deps:
        result["backend"].append("FastAPI")
    if "django" in all_deps:
        result["backend"].append("Django")
    if "flask" in all_deps:
        result["backend"].append("Flask")
    if "express" in all_deps:
        result["backend"].append("Express")
    if "spring-boot" in all_deps or "org.springframework" in all_deps:
        result["backend"].append("Spring")
    if "rails" in all_deps:
        result["backend"].append("Rails")
    if "laravel" in all_deps or "laravel/framework" in all_deps:
        result["backend"].append("Laravel")
    
    # Databases
    if any(dep in all_deps for dep in ["psycopg2", "pg", "postgresql", "postgres"]):
        result["database"].append("PostgreSQL")
    if any(dep in all_deps for dep in ["mongodb", "mongoose", "pymongo"]):
        result["database"].append("MongoDB")
    if any(dep in all_deps for dep in ["redis", "redis-py", "ioredis"]):
        result["database"].append("Redis")
    if any(dep in all_deps for dep in ["mysql", "mysql2", "pymysql", "mysqlclient"]):
        result["database"].append("MySQL")
    
    # Testing frameworks
    if "jest" in all_deps or "jest.config.js" in file_names:
        result["testing"].append("Jest")
    if "pytest" in all_deps:
        result["testing"].append("Pytest")
    if "junit" in all_deps:
        result["testing"].append("JUnit")
    if "vitest" in all_deps or "vitest.config.js" in file_names:
        result["testing"].append("Vitest")
    
    # Build tools
    if "webpack" in all_deps or "webpack.config.js" in file_names:
        result["build_tools"].append("Webpack")
    if "vite" in all_deps or "vite.config.js" in file_names or "vite.config.ts" in file_names:
        result["build_tools"].append("Vite")
    if "dockerfile" in file_names or "docker-compose.yml" in file_names:
        result["build_tools"].append("Docker")
    
    # Remove empty categories
    return {k: v for k, v in result.items() if v}

# Made with Bob
