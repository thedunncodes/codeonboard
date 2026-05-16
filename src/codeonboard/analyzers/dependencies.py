"""
Dependency detection module for analyzing project dependencies.
"""

import json
import re
from typing import Dict, List

from ..github.models import RepoFile


def detect_dependencies(files: List[RepoFile]) -> Dict[str, List[str]]:
    """
    Detect dependencies from common dependency files.
    
    Args:
        files: List of RepoFile objects from the repository
    
    Returns:
        Dictionary mapping dependency file names to lists of dependency names
    """
    dependency_files = {
        "package.json": _parse_package_json,
        "requirements.txt": _parse_requirements_txt,
        "Pipfile": _parse_pipfile,
        "go.mod": _parse_go_mod,
        "Cargo.toml": _parse_cargo_toml,
        "pom.xml": _parse_pom_xml,
        "build.gradle": _parse_build_gradle,
        "composer.json": _parse_composer_json,
        "Gemfile": _parse_gemfile,
    }
    
    result = {}
    
    for file in files:
        if file.name in dependency_files and file.content:
            try:
                parser = dependency_files[file.name]
                deps = parser(file.content)
                if deps:
                    result[file.name] = deps
            except Exception:
                # Skip files that fail to parse
                continue
    
    return result


def _parse_package_json(content: str) -> List[str]:
    """Parse package.json for dependencies."""
    data = json.loads(content)
    deps = []
    
    if "dependencies" in data:
        deps.extend(data["dependencies"].keys())
    if "devDependencies" in data:
        deps.extend(data["devDependencies"].keys())
    
    return deps


def _parse_requirements_txt(content: str) -> List[str]:
    """Parse requirements.txt for dependencies."""
    deps = []
    for line in content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            # Extract package name before version specifier
            match = re.match(r"^([a-zA-Z0-9_-]+)", line)
            if match:
                deps.append(match.group(1))
    return deps


def _parse_pipfile(content: str) -> List[str]:
    """Parse Pipfile for dependencies."""
    deps = []
    in_packages = False
    
    for line in content.split("\n"):
        line = line.strip()
        if line == "[packages]" or line == "[dev-packages]":
            in_packages = True
            continue
        if line.startswith("[") and in_packages:
            in_packages = False
        if in_packages and "=" in line:
            pkg = line.split("=")[0].strip().strip('"')
            if pkg:
                deps.append(pkg)
    
    return deps


def _parse_go_mod(content: str) -> List[str]:
    """Parse go.mod for dependencies."""
    deps = []
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("require"):
            continue
        # Match lines like: github.com/pkg/name v1.2.3
        match = re.match(r"^\s*([a-zA-Z0-9._/-]+)\s+v", line)
        if match:
            deps.append(match.group(1))
    return deps


def _parse_cargo_toml(content: str) -> List[str]:
    """Parse Cargo.toml for dependencies."""
    deps = []
    in_dependencies = False
    
    for line in content.split("\n"):
        line = line.strip()
        if line == "[dependencies]" or line == "[dev-dependencies]":
            in_dependencies = True
            continue
        if line.startswith("[") and in_dependencies:
            in_dependencies = False
        if in_dependencies and "=" in line:
            pkg = line.split("=")[0].strip()
            if pkg:
                deps.append(pkg)
    
    return deps


def _parse_pom_xml(content: str) -> List[str]:
    """Parse pom.xml for dependencies."""
    deps = []
    # Simple regex to extract artifactId from dependency tags
    matches = re.findall(r"<artifactId>([^<]+)</artifactId>", content)
    return matches


def _parse_build_gradle(content: str) -> List[str]:
    """Parse build.gradle for dependencies."""
    deps = []
    # Match lines like: implementation 'group:artifact:version'
    matches = re.findall(r"(?:implementation|api|compile)\s+['\"]([^:'\"]+:[^:'\"]+)", content)
    for match in matches:
        # Extract artifact name from group:artifact
        parts = match.split(":")
        if len(parts) >= 2:
            deps.append(parts[1])
    return deps


def _parse_composer_json(content: str) -> List[str]:
    """Parse composer.json for dependencies."""
    data = json.loads(content)
    deps = []
    
    if "require" in data:
        deps.extend(data["require"].keys())
    if "require-dev" in data:
        deps.extend(data["require-dev"].keys())
    
    return deps


def _parse_gemfile(content: str) -> List[str]:
    """Parse Gemfile for dependencies."""
    deps = []
    for line in content.split("\n"):
        line = line.strip()
        # Match lines like: gem 'rails', '~> 6.0'
        match = re.match(r"gem\s+['\"]([^'\"]+)['\"]", line)
        if match:
            deps.append(match.group(1))
    return deps

# Made with Bob
