"""
MCP tool for generating onboarding guides from repository analysis.
"""

import asyncio
from pathlib import Path
from .fetch_repo import fetch_repo_tool
from ..storage.context_store import ContextStore
from ..utils.validators import validate_repo_url, parse_github_url

# Try to import watsonx summarizer, but don't fail if not configured
try:
    from ..watsonx.summarizer import summarize_context
    WATSONX_AVAILABLE = True
except Exception:
    WATSONX_AVAILABLE = False


def _build_guide_prompt(repo_name: str, context_string: str, tech_stack: dict) -> str:
    """
    Build the prompt for WatsonX to generate the onboarding guide.
    
    Args:
        repo_name: Name of the repository
        context_string: Full context string with code snippets
        tech_stack: Tech stack analysis dictionary
    
    Returns:
        Formatted prompt string for LLM
    """
    frameworks = tech_stack.get("frameworks", {})
    framework_str = ", ".join([
        item for sublist in frameworks.values() for item in sublist
    ]) or "None detected"

    return f"""You are an expert software architect creating a developer onboarding guide.
Analyze the repository code provided and generate a comprehensive onboarding guide.
Be SPECIFIC — reference actual file names, function names, and line numbers from the code.
Never give generic advice. If you cannot find something in the code, say so honestly.

REPOSITORY: {repo_name}
PRIMARY LANGUAGE: {tech_stack.get('primary_language', 'Unknown')}
FRAMEWORKS: {framework_str}
HAS TESTS: {tech_stack.get('has_tests', False)}
HAS DOCKER: {tech_stack.get('has_docker', False)}
HAS CI: {tech_stack.get('has_ci', False)}
ARCHITECTURE: {tech_stack.get('architecture', 'standard')}

CODEBASE:
{context_string}

Generate a developer onboarding guide with EXACTLY these sections in this order.
Use the actual code above — do not make anything up:

## Project Overview
What this project does in 2-3 sentences. What problem it solves. Who uses it.

## Tech Stack
List every technology detected with a one-line explanation of its role in THIS project.

## Architecture
Explain how the system is structured in 3-4 sentences referencing actual folders and files.
Then provide a Mermaid diagram showing the main components and how they connect.
Format the diagram as:
```mermaid
graph TD
    ...
```

## Key Modules
For each major folder or module: name, file path, what it does, and its 2-3 most important files.

## Getting Started
Exact commands to clone, install dependencies and run the project locally.
List prerequisites. Include any gotchas or non-obvious steps you can see from the code.

## Entry Points
Where does the application start? List the main entry files with their exact paths and what happens when they run.

## First Week Tasks
List 3 specific tasks a new developer should do in their first week.
Each task must reference actual files they will touch and explain why it is a good starting task.

## Glossary
List project-specific terms, abbreviations, or patterns used in this codebase that a new developer needs to know.

Be specific. Be direct. Reference real file paths. Do not pad with generic advice."""


async def _call_watsonx(prompt: str) -> str:
    """
    Call WatsonX to generate guide content.
    
    Args:
        prompt: The formatted prompt for guide generation
    
    Returns:
        Generated guide markdown string, or error string starting with "ERROR:"
    """
    try:
        from ibm_watsonx_ai.foundation_models import ModelInference
        from ..config import (
            WATSONX_API_KEY,
            WATSONX_PROJECT_ID,
            WATSONX_URL,
            WATSONX_MODEL_ID,
            WATSONX_MAX_TOKENS
        )
    except ImportError as e:
        return f"ERROR: WatsonX library not available: {str(e)}"
    
    try:
        # Create model instance
        model = ModelInference(
            model_id=WATSONX_MODEL_ID,
            credentials={"apikey": WATSONX_API_KEY, "url": WATSONX_URL},
            project_id=WATSONX_PROJECT_ID
        )
        
        # Run synchronous generate_text in executor to avoid blocking
        loop = asyncio.get_event_loop()
        generated_text = await loop.run_in_executor(
            None,
            lambda: model.chat(
                messages=[{"role": "user", "content": prompt}],
                params={"max_new_tokens": WATSONX_MAX_TOKENS}
            )
        )

        return generated_text["choices"][0]["message"]["content"]
    
    except Exception as e:
        return f"ERROR: Failed to generate guide with WatsonX: {str(e)}"


def _build_fallback_guide(repo_name: str, repo_url: str, tech_stack: dict) -> str:
    """
    Build a fallback guide using structured template when WatsonX is unavailable.
    
    Args:
        repo_name: Name of the repository
        repo_url: Full repository URL
        tech_stack: Tech stack analysis dictionary
    
    Returns:
        Structured markdown guide template
    """
    return f"""# {repo_name} - Developer Onboarding Guide

## Project Overview
*AI generation unavailable — configure WATSONX_API_KEY for full AI-generated content.*

## Tech Stack
**Primary Language:** {tech_stack.get('primary_language', 'Unknown')}

**All Languages:** {', '.join(tech_stack.get('all_languages', []))}

**Frameworks:**
{_format_frameworks(tech_stack.get('frameworks', {}))}

**Dependencies:**
{_format_dependencies(tech_stack.get('dependencies', {}))}

## Architecture
*AI generation unavailable — configure WATSONX_API_KEY for full AI-generated content.*

{_generate_architecture_diagram()}

## Key Modules
*AI generation unavailable — configure WATSONX_API_KEY for full AI-generated content.*

## Getting Started
*AI generation unavailable — configure WATSONX_API_KEY for full AI-generated content.*

## Entry Points
*AI generation unavailable — configure WATSONX_API_KEY for full AI-generated content.*

## First Week Tasks
*AI generation unavailable — configure WATSONX_API_KEY for full AI-generated content.*

## Glossary
*AI generation unavailable — configure WATSONX_API_KEY for full AI-generated content.*

---
*Generated by CodeOnboard MCP Server*
*Repository: {repo_url}*
*Total Files Analyzed: {tech_stack.get('total_files', 0)}*
*Has Tests: {'Yes' if tech_stack.get('has_tests') else 'No'}*
*Has Docker: {'Yes' if tech_stack.get('has_docker') else 'No'}*
*Has CI/CD: {'Yes' if tech_stack.get('has_ci') else 'No'}*
*Architecture: {tech_stack.get('architecture', 'standard').title()}*
"""


async def generate_guide_tool(repo_url: str, include_diagrams: bool = True) -> dict:
    """
    Generate a comprehensive onboarding guide for a repository.
    
    This tool:
    1. Validates the repository URL
    2. Checks if repo is cached (fetches if not)
    3. Gets context string and tech stack from cache
    4. Generates a structured markdown guide with predefined sections
    5. Optionally includes Mermaid diagrams
    
    Args:
        repo_url: GitHub repository URL
        include_diagrams: Whether to include architecture diagrams (default: True)
    
    Returns:
        Dictionary with the generated guide and metadata
    """
    try:
        # Validate URL
        is_valid, error_msg = validate_repo_url(repo_url)
        if not is_valid:
            return {
                "success": False,
                "error": error_msg
            }
        
        # Extract repo_key
        owner, repo_name = parse_github_url(repo_url)
        repo_key = f"{owner}/{repo_name}"
        
        # Check if repo is in cache
        store = ContextStore()
        cached_data = store.get(repo_key)
        
        if not cached_data:
            # Fetch repo first
            fetch_result = await fetch_repo_tool(repo_url)
            if not fetch_result.get("success"):
                return {
                    "success": False,
                    "error": f"Failed to fetch repository: {fetch_result.get('error', 'Unknown error')}"
                }
            # Get cached data after fetch
            cached_data = store.get(repo_key)
        
        # Get context string and tech stack
        context_string = store.get_context_string(repo_key)
        tech_stack = cached_data["tech_stack"]
        
        if not context_string:
            return {
                "success": False,
                "error": "No repository context available"
            }
        
        # Check if context is very large (over 40,000 chars)
        effective_context = context_string
        used_watsonx = False
        
        if len(context_string) > 40000 and WATSONX_AVAILABLE:
            try:
                effective_context = await summarize_context(context_string)
                used_watsonx = True
            except Exception:
                # Silently fall back to original context if summarization fails
                pass
        
        # Build prompt and generate guide with WatsonX
        prompt = _build_guide_prompt(repo_name, effective_context, tech_stack)
        guide_markdown = await _call_watsonx(prompt)
        
        # Check if WatsonX call failed, use fallback template
        watsonx_error = None
        if guide_markdown.startswith("ERROR:"):
            watsonx_error = guide_markdown
            guide_markdown = _build_fallback_guide(repo_name, repo_url, tech_stack)
        
        # Write guide to ONBOARDING.md in current working directory
        output_file = None
        try:
            output_path = Path('ONBOARDING.md')
            output_path.write_text(guide_markdown, encoding='utf-8')
            output_file = str(output_path.absolute())
        except Exception as e:
            # Don't fail the entire operation if file write fails
            output_file = f"Error writing file: {str(e)}"
        
        sections = [
            "Project Overview",
            "Tech Stack",
            "Architecture",
            "Key Modules",
            "Getting Started",
            "Entry Points",
            "First Week Tasks",
            "Glossary"
        ]
        
        result = {
            "success": True,
            "repo_key": repo_key,
            "guide_markdown": guide_markdown,
            "sections": sections,
            "tech_stack": tech_stack,
            "used_watsonx": used_watsonx,
            "output_file": output_file,
            "message": f"Guide generated successfully{' (using WatsonX summarizer for large context)' if used_watsonx else ''}"
        }
        
        # Include error message if WatsonX failed
        if watsonx_error:
            result["watsonx_error"] = watsonx_error
        
        return result
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate guide: {str(e)}"
        }


def _format_frameworks(frameworks: dict) -> str:
    """Format frameworks dict as markdown list."""
    if not frameworks:
        return "None detected"
    
    result = []
    for category, items in frameworks.items():
        if items:
            result.append(f"- **{category.replace('_', ' ').title()}:** {', '.join(items)}")
    
    return "\n".join(result) if result else "None detected"


def _format_dependencies(dependencies: dict) -> str:
    """Format dependencies dict as markdown list."""
    if not dependencies:
        return "None detected"
    
    result = []
    for file_name, deps in dependencies.items():
        if deps:
            result.append(f"- **{file_name}:** {len(deps)} dependencies")
    
    return "\n".join(result) if result else "None detected"


def _generate_architecture_diagram() -> str:
    """Generate a placeholder for architecture diagram."""
    return """
### Architecture Diagram
```mermaid
graph TD
    A[TODO: Generate architecture diagram]
    B[Using Mermaid syntax]
    A --> B
```
"""

# Made with Bob
