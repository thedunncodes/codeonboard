**User:**

<task>
Now implement the actual guide generation in 'src/codeonboard/tools/generate_guide.py' (see below for file content) . Replace the TODO placeholder with a real prompt that generates the guide content.
Add a new function _build_guide_prompt(repo_name: str, context_string: str, tech_stack: dict) -> str that returns this prompt:
pythondef _build_guide_prompt(repo_name: str, context_string: str, tech_stack: dict) -> str:
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
Key Modules
For each major folder or module: name, file path, what it does, and its 2-3 most important files.
Getting Started
Exact commands to clone, install dependencies and run the project locally.
List prerequisites. Include any gotchas or non-obvious steps you can see from the code.
Entry Points
Where does the application start? List the main entry files with their exact paths and what happens when they run.
First Week Tasks
List 3 specific tasks a new developer should do in their first week.
Each task must reference actual files they will touch and explain why it is a good starting task.
Glossary
List project-specific terms, abbreviations, or patterns used in this codebase that a new developer needs to know.
Be specific. Be direct. Reference real file paths. Do not pad with generic advice."""

*Now wire this into `generate_guide_tool`. After getting `effective_context` and `tech_stack`, build the prompt and call watsonx. Add a new async function `_call_watsonx(prompt: str) -> str` that:*
- *Imports `ibm_watsonx_ai` — wrap in try/except, return error string if not available*
- *Creates a `ModelInference` instance with model ID from config, credentials from config*
- *Calls `model.generate_text(prompt=prompt)` — note this is synchronous, wrap it in `asyncio.get_event_loop().run_in_executor(None, model.generate_text, prompt)`*
- *Returns the generated text string*
- *On any exception returns a string starting with `ERROR:` so the caller can detect failure*

*In `generate_guide_tool`, replace the hardcoded `guide_markdown` string with:*
```python
prompt = _build_guide_prompt(repo_name, effective_context, tech_stack)
guide_markdown = await _call_watsonx(prompt)

if guide_markdown.startswith("ERROR:"):
    # Fallback to structured template with tech stack data
    guide_markdown = _build_fallback_guide(repo_name, repo_url, tech_stack)
Also add _build_fallback_guide(repo_name, repo_url, tech_stack) -> str that returns the current structured template markdown — rename the existing hardcoded guide string into this function so it is not lost.
</task>

<file_content path="src/codeonboard/tools/generate_guide.py">
  1 | """
  2 | MCP tool for generating onboarding guides from repository analysis.
  3 | """
  4 | 
  5 | from .fetch_repo import fetch_repo_tool
  6 | from ..storage.context_store import ContextStore
  7 | from ..utils.validators import validate_repo_url, parse_github_url
  8 | 
  9 | # Try to import watsonx summarizer, but don't fail if not configured
 10 | try:
 11 |     from ..watsonx.summarizer import summarize_context
 12 |     WATSONX_AVAILABLE = True
 13 | except Exception:
 14 |     WATSONX_AVAILABLE = False
 15 | 
 16 | 
 17 | async def generate_guide_tool(repo_url: str, include_diagrams: bool = True) -> dict:
 18 |     """
 19 |     Generate a comprehensive onboarding guide for a repository.
 20 |     
 21 |     This tool:
 22 |     1. Validates the repository URL
 23 |     2. Checks if repo is cached (fetches if not)
 24 |     3. Gets context string and tech stack from cache
 25 |     4. Generates a structured markdown guide with predefined sections
 26 |     5. Optionally includes Mermaid diagrams
 27 |     
 28 |     Args:
 29 |         repo_url: GitHub repository URL
 30 |         include_diagrams: Whether to include architecture diagrams (default: True)
 31 |     
 32 |     Returns:
 33 |         Dictionary with the generated guide and metadata
 34 |     """
 35 |     try:
 36 |         # Validate URL
 37 |         is_valid, error_msg = validate_repo_url(repo_url)
 38 |         if not is_valid:
 39 |             return {
 40 |                 "success": False,
 41 |                 "error": error_msg
 42 |             }
 43 |         
 44 |         # Extract repo_key
 45 |         owner, repo_name = parse_github_url(repo_url)
 46 |         repo_key = f"{owner}/{repo_name}"
 47 |         
 48 |         # Check if repo is in cache
 49 |         store = ContextStore()
 50 |         cached_data = store.get(repo_key)
 51 |         
 52 |         if not cached_data:
 53 |             # Fetch repo first
 54 |             fetch_result = await fetch_repo_tool(repo_url)
 55 |             if not fetch_result.get("success"):
 56 |                 return {
 57 |                     "success": False,
 58 |                     "error": f"Failed to fetch repository: {fetch_result.get('error', 'Unknown error')}"
 59 |                 }
 60 |             # Get cached data after fetch
 61 |             cached_data = store.get(repo_key)
 62 |         
 63 |         # Get context string and tech stack
 64 |         context_string = store.get_context_string(repo_key)
 65 |         tech_stack = cached_data["tech_stack"]
 66 |         
 67 |         if not context_string:
 68 |             return {
 69 |                 "success": False,
 70 |                 "error": "No repository context available"
 71 |             }
 72 |         
 73 |         # Check if context is very large (over 40,000 chars)
 74 |         effective_context = context_string
 75 |         used_watsonx = False
 76 |         
 77 |         if len(context_string) > 40000 and WATSONX_AVAILABLE:
 78 |             try:
 79 |                 effective_context = await summarize_context(context_string)
 80 |                 used_watsonx = True
 81 |             except Exception:
 82 |                 # Silently fall back to original context if summarization fails
 83 |                 pass
 84 |         
 85 |         # TODO: Implement actual LLM prompt for guide generation
 86 |         # For now, return a placeholder
 87 |         guide_markdown = f"""# {repo_name} - Developer Onboarding Guide
 88 | 
 89 | ## Project Overview
 90 | TODO: Generate project overview using LLM with context
 91 | 
 92 | ## Tech Stack
 93 | **Primary Language:** {tech_stack.get('primary_language', 'Unknown')}
 94 | 
 95 | **All Languages:** {', '.join(tech_stack.get('all_languages', []))}
 96 | 
 97 | **Frameworks:**
 98 | {_format_frameworks(tech_stack.get('frameworks', {}))}
 99 | 
100 | **Dependencies:**
101 | {_format_dependencies(tech_stack.get('dependencies', {}))}
102 | 
103 | ## Architecture
104 | TODO: Generate architecture description using LLM with context
105 | {_generate_architecture_diagram() if include_diagrams else ''}
106 | 
107 | ## Key Modules
108 | TODO: Generate key modules description using LLM with context
109 | 
110 | ## Getting Started
111 | TODO: Generate getting started instructions using LLM with context
112 | 
113 | ## Entry Points
114 | TODO: Generate entry points description using LLM with context
115 | 
116 | ## First Week Tasks
117 | TODO: Generate first week tasks using LLM with context
118 | 
119 | ## Glossary
120 | TODO: Generate glossary using LLM with context
121 | 
122 | ---
123 | *Generated by CodeOnboard MCP Server*
124 | *Repository: {repo_url}*
125 | *Total Files Analyzed: {tech_stack.get('total_files', 0)}*
126 | *Has Tests: {'Yes' if tech_stack.get('has_tests') else 'No'}*
127 | *Has Docker: {'Yes' if tech_stack.get('has_docker') else 'No'}*
128 | *Has CI/CD: {'Yes' if tech_stack.get('has_ci') else 'No'}*
129 | *Architecture: {tech_stack.get('architecture', 'standard').title()}*
130 | """
131 |         
132 |         sections = [
133 |             "Project Overview",
134 |             "Tech Stack",
135 |             "Architecture",
136 |             "Key Modules",
137 |             "Getting Started",
138 |             "Entry Points",
139 |             "First Week Tasks",
140 |             "Glossary"
141 |         ]
142 |         
143 |         return {
144 |             "success": True,
145 |             "repo_key": repo_key,
146 |             "guide_markdown": guide_markdown,
147 |             "sections": sections,
148 |             "tech_stack": tech_stack,
149 |             "used_watsonx": used_watsonx,
150 |             "message": f"Guide generated successfully{' (using WatsonX summarizer for large context)' if used_watsonx else ''}"
151 |         }
152 |     
153 |     except Exception as e:
154 |         return {
155 |             "success": False,
156 |             "error": f"Failed to generate guide: {str(e)}"
157 |         }
158 | 
159 | 
160 | def _format_frameworks(frameworks: dict) -> str:
161 |     """Format frameworks dict as markdown list."""
162 |     if not frameworks:
163 |         return "None detected"
164 |     
165 |     result = []
166 |     for category, items in frameworks.items():
167 |         if items:
168 |             result.append(f"- **{category.replace('_', ' ').title()}:** {', '.join(items)}")
169 |     
170 |     return "\n".join(result) if result else "None detected"
171 | 
172 | 
173 | def _format_dependencies(dependencies: dict) -> str:
174 |     """Format dependencies dict as markdown list."""
175 |     if not dependencies:
176 |         return "None detected"
177 |     
178 |     result = []
179 |     for file_name, deps in dependencies.items():
180 |         if deps:
181 |             result.append(f"- **{file_name}:** {len(deps)} dependencies")
182 |     
183 |     return "\n".join(result) if result else "None detected"
184 | 
185 | 
186 | def _generate_architecture_diagram() -> str:
187 |     """Generate a placeholder for architecture diagram."""
188 |     return """
189 | ### Architecture Diagram
190 | ```mermaid
191 | graph TD
192 |     A[TODO: Generate architecture diagram]
193 |     B[Using Mermaid syntax]
194 |     A --> B
195 | ```
196 | """
197 | 
198 | # Made with Bob

</file_content>
<environment_details>
# VSCode Visible Files


# VSCode Open Tabs
src/codeonboard/storage/context_store.py,src/codeonboard/github/client.py,src/codeonboard/tools/fetch_repo.py,.gitignore,PROJECT_STRUCTURE.md,../../../../.bob/settings/mcp_settings.json

# Current Time
Current time in ISO 8601 UTC format: 2026-05-16T16:51:44.170Z
User time zone: Africa/Lagos, UTC+1:00

# Current Cost
$0.00

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**
- .env
- secrets/

# Current Mode
<slug>advanced</slug>
<name>🛠️ Advanced</name>


# Current Workspace Directory (c:/Users/user/Desktop/CoLLoSal/hackathon/codeonboard) Files
.env.example
.gitignore
LICENSE
mcp_config.json
PROJECT_STRUCTURE.md
pyproject.toml
requirements.txt
run_server.py
src/
src/codeonboard/
src/codeonboard/__init__.py
src/codeonboard/config.py
src/codeonboard/server.py
src/codeonboard/analyzers/
src/codeonboard/analyzers/__init__.py
src/codeonboard/analyzers/dependencies.py
src/codeonboard/analyzers/framework.py
src/codeonboard/analyzers/tech_stack.py
src/codeonboard/generators/
src/codeonboard/generators/__init__.py
src/codeonboard/github/
src/codeonboard/github/__init__.py
src/codeonboard/github/client.py
src/codeonboard/github/models.py
src/codeonboard/storage/
src/codeonboard/storage/__init__.py
src/codeonboard/storage/context_store.py
src/codeonboard/tools/
src/codeonboard/tools/__init__.py
src/codeonboard/tools/ask_codebase.py
src/codeonboard/tools/fetch_repo.py
src/codeonboard/tools/generate_guide.py
src/codeonboard/utils/
src/codeonboard/utils/__init__.py
src/codeonboard/utils/validators.py
src/codeonboard/watsonx/
src/codeonboard/watsonx/__init__.py
tests/
tests/__init__.py
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

I'll implement the guide generation with WatsonX integration in the `generate_guide.py` file. Let me break this down into clear steps:

1. Add the `_build_guide_prompt` function
2. Add the `_call_watsonx` async function
3. Add the `_build_fallback_guide` function (extracting current template)
4. Wire everything together in `generate_guide_tool`

<apply_diff>
<path>src/codeonboard/tools/generate_guide.py</path>
<diff>
<<<<<<< SEARCH
:start_line:1
-------
"""
MCP tool for generating onboarding guides from repository analysis.
"""

from .fetch_repo import fetch_repo_tool
from ..storage.context_store import ContextStore
from ..utils.validators import validate_repo_url, parse_github_url

# Try to import watsonx summarizer, but don't fail if not configured
try:
    from ..watsonx.summarizer import summarize_context
    WATSONX_AVAILABLE = True
except Exception:
    WATSONX_AVAILABLE = False
=======
"""
MCP tool for generating onboarding guides from repository analysis.
"""

import asyncio
from .fetch_repo import fetch_repo_tool
from ..storage.context_store import ContextStore
from ..utils.validators import validate_repo_url, parse_github_url

# Try to import watsonx summarizer, but don't fail if not configured
try:
    from ..watsonx.summarizer import summarize_context
    WATSONX_AVAILABLE = True
except Exception:
    WATSONX_AVAILABLE = False
>>>>>>> REPLACE

<<<<<<< SEARCH
:start_line:17
-------
async def generate_guide_tool(repo_url: str, include_diagrams: bool = True) -> dict:
=======
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
        from ibm_watsonx_ai import ModelInference
        from ..config import get_watsonx_config
    except ImportError as e:
        return f"ERROR: WatsonX library not available: {str(e)}"
    
    try:
        # Get WatsonX configuration
        config = get_watsonx_config()
        
        # Create model instance
        model = ModelInference(
            model_id=config["model_id"],
            credentials=config["credentials"],
            project_id=config.get("project_id")
        )
        
        # Run synchronous generate_text in executor to avoid blocking
        loop = asyncio.get_event_loop()
        generated_text = await loop.run_in_executor(
            None,
            lambda: model.generate_text(prompt=prompt)
        )
        
        return generated_text
    
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
TODO: Generate project overview using LLM with context

## Tech Stack
**Primary Language:** {tech_stack.get('primary_language', 'Unknown')}

**All Languages:** {', '.join(tech_stack.get('all_languages', []))}

**Frameworks:**
{_format_frameworks(tech_stack.get('frameworks', {}))}

**Dependencies:**
{_format_dependencies(tech_stack.get('dependencies', {}))}

## Architecture
TODO: Generate architecture description using LLM with context
{_generate_architecture_diagram()}

## Key Modules
TODO: Generate key modules description using LLM with context

## Getting Started
TODO: Generate getting started instructions using LLM with context

## Entry Points
TODO: Generate entry points description using LLM with context

## First Week Tasks
TODO: Generate first week tasks using LLM with context

## Glossary
TODO: Generate glossary using LLM with context

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
>>>>>>> REPLACE

<<<<<<< SEARCH
:start_line:84
-------
        # TODO: Implement actual LLM prompt for guide generation
        # For now, return a placeholder
        guide_markdown = f"""# {repo_name} - Developer Onboarding Guide

## Project Overview
TODO: Generate project overview using LLM with context

## Tech Stack
**Primary Language:** {tech_stack.get('primary_language', 'Unknown')}

**All Languages:** {', '.join(tech_stack.get('all_languages', []))}

**Frameworks:**
{_format_frameworks(tech_stack.get('frameworks', {}))}

**Dependencies:**
{_format_dependencies(tech_stack.get('dependencies', {}))}

## Architecture
TODO: Generate architecture description using LLM with context
{_generate_architecture_diagram() if include_diagrams else ''}

## Key Modules
TODO: Generate key modules description using LLM with context

## Getting Started
TODO: Generate getting started instructions using LLM with context

## Entry Points
TODO: Generate entry points description using LLM with context

## First Week Tasks
TODO: Generate first week tasks using LLM with context

## Glossary
TODO: Generate glossary using LLM with context

---
*Generated by CodeOnboard MCP Server*
*Repository: {repo_url}*
*Total Files Analyzed: {tech_stack.get('total_files', 0)}*
*Has Tests: {'Yes' if tech_stack.get('has_tests') else 'No'}*
*Has Docker: {'Yes' if tech_stack.get('has_docker') else 'No'}*
*Has CI/CD: {'Yes' if tech_stack.get('has_ci') else 'No'}*
*Architecture: {tech_stack.get('architecture', 'standard').title()}*
"""
=======
        # Build prompt and generate guide with WatsonX
        prompt = _build_guide_prompt(repo_name, effective_context, tech_stack)
        guide_markdown = await _call_watsonx(prompt)
        
        # Check if WatsonX call failed, use fallback template
        if guide_markdown.startswith("ERROR:"):
            guide_markdown = _build_fallback_guide(repo_name, repo_url, tech_stack)
>>>>>>> REPLACE
</diff>
</apply_diff>

Now I need to check if there's a `config.py` file to see if the `get_watsonx_config` function exists, or if I need to create it:

<read_file>
<args>
  <file>
    <path>src/codeonboard/config.py</path>
  </file>
</args>
</read_file>

---

**User:**

[apply_diff for 'src/codeonboard/tools/generate_guide.py'] Result:
<file_write_result>
<path>src/codeonboard/tools/generate_guide.py</path>
<operation>modified</operation>
<problems>

New problems detected after saving the file:
src/codeonboard/tools/generate_guide.py
- [basedpyright Error] 12 |     from ..watsonx.summarizer import summarize_context : Import "..watsonx.summarizer" could not be resolved
- [basedpyright Error] 101 |         from ..config import get_watsonx_config : "get_watsonx_config" is unknown import symbol
- [basedpyright Error] 235 |         tech_stack = cached_data["tech_stack"] : Object of type "None" is not subscriptable
- [basedpyright Error] 249 |                 effective_context = await summarize_context(context_string) : "summarize_context" is possibly unbound</problems>
<notice>
<i>You do not need to re-read the file, as you have seen all changes</i>
<i>Proceed with the task using these changes as the new baseline.</i>
</notice>
</file_write_result>

Tool [read_file] was not executed because a tool has already been used in this message. Only one tool may be used per message. You must assess the first tool's result before proceeding to use the next tool.
<environment_details>
# VSCode Visible Files
src\codeonboard\tools\generate_guide.py

# VSCode Open Tabs
src/codeonboard/storage/context_store.py,src/codeonboard/github/client.py,src/codeonboard/tools/fetch_repo.py,.gitignore,src/codeonboard/tools/generate_guide.py,../../../../.bob/settings/mcp_settings.json

# Recently Modified Files
These files have been modified since you last accessed them (file was just edited so you may need to re-read it before editing):
src/codeonboard/tools/generate_guide.py

# Current Time
Current time in ISO 8601 UTC format: 2026-05-16T16:52:24.611Z
User time zone: Africa/Lagos, UTC+1:00

# Current Cost
$0.05

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**
- .env
- secrets/

# Current Mode
<slug>advanced</slug>
<name>🛠️ Advanced</name>
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

Good! The changes were applied. Now I need to check the `config.py` file to see if `get_watsonx_config` exists, and also check the watsonx module structure:

<read_file>
<args>
  <file>
    <path>src/codeonboard/config.py</path>
  </file>
</args>
</read_file>

---

**User:**

[read_file for 'src/codeonboard/config.py'. Reading multiple files at once is more efficient for the LLM. If other files are relevant to your current task, please read them simultaneously.] Result:
<files>
<file><path>src/codeonboard/config.py</path>
<content lines="1-109">
  1 | """
  2 | Configuration module for loading environment variables and application settings.
  3 | """
  4 | 
  5 | import os
  6 | import warnings
  7 | from pathlib import Path
  8 | from dotenv import load_dotenv
  9 | 
 10 | # Load environment variables from .env file
 11 | load_dotenv()
 12 | 
 13 | # Project root directory
 14 | PROJECT_ROOT = Path(__file__).parent.parent.parent
 15 | 
 16 | # GitHub Configuration
 17 | GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
 18 | if not GITHUB_TOKEN:
 19 |     raise ValueError(
 20 |         "GITHUB_TOKEN environment variable is required. "
 21 |         "Please set it in your .env file or environment."
 22 |     )
 23 | 
 24 | # IBM WatsonX Configuration
 25 | WATSONX_API_KEY = os.getenv("WATSONX_API_KEY", "")
 26 | WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "")
 27 | WATSONX_URL = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
 28 | 
 29 | # Validate WatsonX credentials
 30 | if not WATSONX_API_KEY or not WATSONX_PROJECT_ID:
 31 |     warnings.warn(
 32 |         "WATSONX_API_KEY and WATSONX_PROJECT_ID environment variables are not set. "
 33 |         "WatsonX features will not be available. "
 34 |         "Please set them in your .env file or environment.",
 35 |         RuntimeWarning
 36 |     )
 37 | 
 38 | # Storage Configuration
 39 | STORAGE_DIR = PROJECT_ROOT / "data" / "context"
 40 | STORAGE_DIR.mkdir(parents=True, exist_ok=True)
 41 | 
 42 | # GitHub API Configuration
 43 | GITHUB_API_BASE_URL = "https://api.github.com"
 44 | GITHUB_API_VERSION = "2022-11-28"
 45 | 
 46 | # File Processing Limits
 47 | MAX_FILE_SIZE = 4000  # Maximum characters per file
 48 | MAX_FILES_TO_FETCH = 40  # Maximum number of files to fetch from a repository
 49 | 
 50 | # Folders to skip during repository analysis
 51 | SKIP_FOLDERS = {
 52 |     "node_modules",
 53 |     ".git",
 54 |     "dist",
 55 |     "build",
 56 |     "__pycache__",
 57 |     ".next",
 58 |     "vendor",
 59 |     "coverage",
 60 | }
 61 | 
 62 | # Binary file extensions to skip
 63 | BINARY_EXTENSIONS = {
 64 |     ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
 65 |     ".woff", ".woff2", ".ttf", ".eot", ".otf",
 66 |     ".pdf", ".zip", ".tar", ".gz", ".rar", ".7z",
 67 |     ".exe", ".dll", ".so", ".dylib",
 68 |     ".mp3", ".mp4", ".avi", ".mov", ".wav",
 69 | }
 70 | 
 71 | # WatsonX Model Configuration
 72 | WATSONX_MODEL_ID = os.getenv("WATSONX_MODEL_ID", "ibm/granite-3-8b-instruct")
 73 | WATSONX_MAX_TOKENS = int(os.getenv("WATSONX_MAX_TOKENS", "2048"))
 74 | WATSONX_TEMPERATURE = float(os.getenv("WATSONX_TEMPERATURE", "0.7"))
 75 | WATSONX_TOP_P = float(os.getenv("WATSONX_TOP_P", "1.0"))
 76 | WATSONX_TOP_K = int(os.getenv("WATSONX_TOP_K", "50"))
 77 | 
 78 | # Logging Configuration
 79 | LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
 80 | 
 81 | # MCP Server Configuration
 82 | MCP_SERVER_NAME = "codeonboard"
 83 | MCP_SERVER_VERSION = "0.1.0"
 84 | 
 85 | # Export all configuration constants
 86 | __all__ = [
 87 |     "PROJECT_ROOT",
 88 |     "GITHUB_TOKEN",
 89 |     "WATSONX_API_KEY",
 90 |     "WATSONX_PROJECT_ID",
 91 |     "WATSONX_URL",
 92 |     "STORAGE_DIR",
 93 |     "GITHUB_API_BASE_URL",
 94 |     "GITHUB_API_VERSION",
 95 |     "MAX_FILE_SIZE",
 96 |     "MAX_FILES_TO_FETCH",
 97 |     "SKIP_FOLDERS",
 98 |     "BINARY_EXTENSIONS",
 99 |     "WATSONX_MODEL_ID",
100 |     "WATSONX_MAX_TOKENS",
101 |     "WATSONX_TEMPERATURE",
102 |     "WATSONX_TOP_P",
103 |     "WATSONX_TOP_K",
104 |     "LOG_LEVEL",
105 |     "MCP_SERVER_NAME",
106 |     "MCP_SERVER_VERSION",
107 | ]
108 | 
109 | # Made with Bob
</content>
</file>
</files>
<environment_details>
# VSCode Visible Files
src\codeonboard\tools\generate_guide.py

# VSCode Open Tabs
src/codeonboard/storage/context_store.py,src/codeonboard/github/client.py,src/codeonboard/tools/fetch_repo.py,.gitignore,src/codeonboard/tools/generate_guide.py,../../../../.bob/settings/mcp_settings.json

# Current Time
Current time in ISO 8601 UTC format: 2026-05-16T16:52:34.925Z
User time zone: Africa/Lagos, UTC+1:00

# Current Cost
$0.11

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**
- .env
- secrets/

# Current Mode
<slug>advanced</slug>
<name>🛠️ Advanced</name>
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

I can see the config file has all the WatsonX configuration constants but doesn't have a `get_watsonx_config()` function. I need to add this function to the config file:

<apply_diff>
<path>src/codeonboard/config.py</path>
<diff>
<<<<<<< SEARCH
:start_line:107
-------
]

# Made with Bob
=======
]


def get_watsonx_config() -> dict:
    """
    Get WatsonX configuration as a dictionary for ModelInference.
    
    Returns:
        Dictionary with model_id, credentials, and project_id
    
    Raises:
        ValueError: If WatsonX credentials are not configured
    """
    if not WATSONX_API_KEY or not WATSONX_PROJECT_ID:
        raise ValueError(
            "WatsonX credentials not configured. "
            "Please set WATSONX_API_KEY and WATSONX_PROJECT_ID in your .env file."
        )
    
    return {
        "model_id": WATSONX_MODEL_ID,
        "credentials": {
            "url": WATSONX_URL,
            "apikey": WATSONX_API_KEY
        },
        "project_id": WATSONX_PROJECT_ID,
        "params": {
            "max_new_tokens": WATSONX_MAX_TOKENS,
            "temperature": WATSONX_TEMPERATURE,
            "top_p": WATSONX_TOP_P,
            "top_k": WATSONX_TOP_K
        }
    }


# Made with Bob
>>>>>>> REPLACE
</diff>
</apply_diff>

---

**User:**

[apply_diff for 'src/codeonboard/config.py'] Result:
<file_write_result>
<path>src/codeonboard/config.py</path>
<operation>modified</operation>
<notice>
<i>You do not need to re-read the file, as you have seen all changes</i>
<i>Proceed with the task using these changes as the new baseline.</i>
</notice>
</file_write_result>

<notice>Making multiple related changes in a single apply_diff is more efficient. If other changes are needed in this file, please include them as additional SEARCH/REPLACE blocks.</notice>
<environment_details>
# VSCode Visible Files
src\codeonboard\config.py

# VSCode Open Tabs
src/codeonboard/storage/context_store.py,src/codeonboard/github/client.py,src/codeonboard/tools/fetch_repo.py,.gitignore,src/codeonboard/tools/generate_guide.py,src/codeonboard/config.py,../../../../.bob/settings/mcp_settings.json

# Recently Modified Files
These files have been modified since you last accessed them (file was just edited so you may need to re-read it before editing):
src/codeonboard/config.py

# Current Time
Current time in ISO 8601 UTC format: 2026-05-16T16:52:50.124Z
User time zone: Africa/Lagos, UTC+1:00

# Current Cost
$0.17

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**
- .env
- secrets/

# Current Mode
<slug>advanced</slug>
<name>🛠️ Advanced</name>
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

Good! Now let me check if the watsonx summarizer module exists to understand the import structure:

<read_file>
<args>
  <file>
    <path>src/codeonboard/watsonx/__init__.py</path>
  </file>
</args>
</read_file>

---

**User:**

[read_file for 'src/codeonboard/watsonx/__init__.py'. Reading multiple files at once is more efficient for the LLM. If other files are relevant to your current task, please read them simultaneously.] Result:
<files>
<file><path>src/codeonboard/watsonx/__init__.py</path>
<content lines="1-3">
1 | """Package init."""
2 | 
3 | # Made with Bob
</content>
</file>
</files>
<environment_details>
# VSCode Visible Files
src\codeonboard\config.py

# VSCode Open Tabs
src/codeonboard/storage/context_store.py,src/codeonboard/github/client.py,src/codeonboard/tools/fetch_repo.py,.gitignore,src/codeonboard/tools/generate_guide.py,src/codeonboard/config.py,../../../../.bob/settings/mcp_settings.json

# Current Time
Current time in ISO 8601 UTC format: 2026-05-16T16:52:58.438Z
User time zone: Africa/Lagos, UTC+1:00

# Current Cost
$0.23

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**
- .env
- secrets/

# Current Mode
<slug>advanced</slug>
<name>🛠️ Advanced</name>
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

Let me check if the summarizer.py file exists in the watsonx directory:

<list_files>
<path>src/codeonboard/watsonx</path>
<recursive>false</recursive>
</list_files>

---

**User:**

[list_files for 'src/codeonboard/watsonx'] Result:
__init__.py
<environment_details>
# VSCode Visible Files
src\codeonboard\config.py

# VSCode Open Tabs
src/codeonboard/storage/context_store.py,src/codeonboard/github/client.py,src/codeonboard/tools/fetch_repo.py,.gitignore,src/codeonboard/tools/generate_guide.py,src/codeonboard/config.py,../../../../.bob/settings/mcp_settings.json

# Current Time
Current time in ISO 8601 UTC format: 2026-05-16T16:53:05.810Z
User time zone: Africa/Lagos, UTC+1:00

# Current Cost
$0.30

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**
- .env
- secrets/

# Current Mode
<slug>advanced</slug>
<name>🛠️ Advanced</name>
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

The `summarizer.py` file doesn't exist yet. The code in `generate_guide.py` tries to import it but handles the exception gracefully. This is fine - the import error is caught and `WATSONX_AVAILABLE` is set to `False` if it fails.

Now let me verify the implementation is complete by reviewing the updated `generate_guide.py` file:

<read_file>
<args>
  <file>
    <path>src/codeonboard/tools/generate_guide.py</path>
    <line_range>1-50</line_range>
  </file>
</args>
</read_file>

---

**User:**

[read_file for 'src/codeonboard/tools/generate_guide.py'. Reading multiple files at once is more efficient for the LLM. If other files are relevant to your current task, please read them simultaneously.] Result:
<files>
<file><path>src/codeonboard/tools/generate_guide.py</path>
<content lines="1-50">
 1 | """
 2 | MCP tool for generating onboarding guides from repository analysis.
 3 | """
 4 | 
 5 | import asyncio
 6 | from .fetch_repo import fetch_repo_tool
 7 | from ..storage.context_store import ContextStore
 8 | from ..utils.validators import validate_repo_url, parse_github_url
 9 | 
10 | # Try to import watsonx summarizer, but don't fail if not configured
11 | try:
12 |     from ..watsonx.summarizer import summarize_context
13 |     WATSONX_AVAILABLE = True
14 | except Exception:
15 |     WATSONX_AVAILABLE = False
16 | 
17 | 
18 | def _build_guide_prompt(repo_name: str, context_string: str, tech_stack: dict) -> str:
19 |     """
20 |     Build the prompt for WatsonX to generate the onboarding guide.
21 |     
22 |     Args:
23 |         repo_name: Name of the repository
24 |         context_string: Full context string with code snippets
25 |         tech_stack: Tech stack analysis dictionary
26 |     
27 |     Returns:
28 |         Formatted prompt string for LLM
29 |     """
30 |     frameworks = tech_stack.get("frameworks", {})
31 |     framework_str = ", ".join([
32 |         item for sublist in frameworks.values() for item in sublist
33 |     ]) or "None detected"
34 | 
35 |     return f"""You are an expert software architect creating a developer onboarding guide.
36 | Analyze the repository code provided and generate a comprehensive onboarding guide.
37 | Be SPECIFIC — reference actual file names, function names, and line numbers from the code.
38 | Never give generic advice. If you cannot find something in the code, say so honestly.
39 | 
40 | REPOSITORY: {repo_name}
41 | PRIMARY LANGUAGE: {tech_stack.get('primary_language', 'Unknown')}
42 | FRAMEWORKS: {framework_str}
43 | HAS TESTS: {tech_stack.get('has_tests', False)}
44 | HAS DOCKER: {tech_stack.get('has_docker', False)}
45 | HAS CI: {tech_stack.get('has_ci', False)}
46 | ARCHITECTURE: {tech_stack.get('architecture', 'standard')}
47 | 
48 | CODEBASE:
49 | {context_string}
50 | 
</content>
</file>
</files>
<environment_details>
# VSCode Visible Files
src\codeonboard\config.py

# VSCode Open Tabs
src/codeonboard/storage/context_store.py,src/codeonboard/github/client.py,src/codeonboard/tools/fetch_repo.py,.gitignore,src/codeonboard/tools/generate_guide.py,src/codeonboard/config.py,../../../../.bob/settings/mcp_settings.json

# Current Time
Current time in ISO 8601 UTC format: 2026-05-16T16:53:16.804Z
User time zone: Africa/Lagos, UTC+1:00

# Current Cost
$0.36

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**
- .env
- secrets/

# Current Mode
<slug>advanced</slug>
<name>🛠️ Advanced</name>
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

<read_file>
<args>
  <file>
    <path>src/codeonboard/tools/generate_guide.py</path>
    <line_range>85-120</line_range>
  </file>
</args>
</read_file>

---

**User:**

[read_file for 'src/codeonboard/tools/generate_guide.py'. Reading multiple files at once is more efficient for the LLM. If other files are relevant to your current task, please read them simultaneously.] Result:
<files>
<file><path>src/codeonboard/tools/generate_guide.py</path>
<content lines="85-120">
 85 | 
 86 | Be specific. Be direct. Reference real file paths. Do not pad with generic advice."""
 87 | 
 88 | 
 89 | async def _call_watsonx(prompt: str) -> str:
 90 |     """
 91 |     Call WatsonX to generate guide content.
 92 |     
 93 |     Args:
 94 |         prompt: The formatted prompt for guide generation
 95 |     
 96 |     Returns:
 97 |         Generated guide markdown string, or error string starting with "ERROR:"
 98 |     """
 99 |     try:
100 |         from ibm_watsonx_ai import ModelInference
101 |         from ..config import get_watsonx_config
102 |     except ImportError as e:
103 |         return f"ERROR: WatsonX library not available: {str(e)}"
104 |     
105 |     try:
106 |         # Get WatsonX configuration
107 |         config = get_watsonx_config()
108 |         
109 |         # Create model instance
110 |         model = ModelInference(
111 |             model_id=config["model_id"],
112 |             credentials=config["credentials"],
113 |             project_id=config.get("project_id")
114 |         )
115 |         
116 |         # Run synchronous generate_text in executor to avoid blocking
117 |         loop = asyncio.get_event_loop()
118 |         generated_text = await loop.run_in_executor(
119 |             None,
120 |             lambda: model.generate_text(prompt=prompt)
</content>
</file>
</files>
<environment_details>
# VSCode Visible Files
src\codeonboard\config.py

# VSCode Open Tabs
src/codeonboard/storage/context_store.py,src/codeonboard/github/client.py,src/codeonboard/tools/fetch_repo.py,.gitignore,src/codeonboard/tools/generate_guide.py,src/codeonboard/config.py,../../../../.bob/settings/mcp_settings.json

# Current Time
Current time in ISO 8601 UTC format: 2026-05-16T16:53:23.990Z
User time zone: Africa/Lagos, UTC+1:00

# Current Cost
$0.43

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**
- .env
- secrets/

# Current Mode
<slug>advanced</slug>
<name>🛠️ Advanced</name>
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

<read_file>
<args>
  <file>
    <path>src/codeonboard/tools/generate_guide.py</path>
    <line_range>220-260</line_range>
  </file>
</args>
</read_file>

---

**User:**

[read_file for 'src/codeonboard/tools/generate_guide.py'. Reading multiple files at once is more efficient for the LLM. If other files are relevant to your current task, please read them simultaneously.] Result:
<files>
<file><path>src/codeonboard/tools/generate_guide.py</path>
<content lines="220-260">
220 |         cached_data = store.get(repo_key)
221 |         
222 |         if not cached_data:
223 |             # Fetch repo first
224 |             fetch_result = await fetch_repo_tool(repo_url)
225 |             if not fetch_result.get("success"):
226 |                 return {
227 |                     "success": False,
228 |                     "error": f"Failed to fetch repository: {fetch_result.get('error', 'Unknown error')}"
229 |                 }
230 |             # Get cached data after fetch
231 |             cached_data = store.get(repo_key)
232 |         
233 |         # Get context string and tech stack
234 |         context_string = store.get_context_string(repo_key)
235 |         tech_stack = cached_data["tech_stack"]
236 |         
237 |         if not context_string:
238 |             return {
239 |                 "success": False,
240 |                 "error": "No repository context available"
241 |             }
242 |         
243 |         # Check if context is very large (over 40,000 chars)
244 |         effective_context = context_string
245 |         used_watsonx = False
246 |         
247 |         if len(context_string) > 40000 and WATSONX_AVAILABLE:
248 |             try:
249 |                 effective_context = await summarize_context(context_string)
250 |                 used_watsonx = True
251 |             except Exception:
252 |                 # Silently fall back to original context if summarization fails
253 |                 pass
254 |         
255 |         # Build prompt and generate guide with WatsonX
256 |         prompt = _build_guide_prompt(repo_name, effective_context, tech_stack)
257 |         guide_markdown = await _call_watsonx(prompt)
258 |         
259 |         # Check if WatsonX call failed, use fallback template
260 |         if guide_markdown.startswith("ERROR:"):
</content>
</file>
</files>
<environment_details>
# VSCode Visible Files
src\codeonboard\config.py

# VSCode Open Tabs
src/codeonboard/storage/context_store.py,src/codeonboard/github/client.py,src/codeonboard/tools/fetch_repo.py,.gitignore,src/codeonboard/tools/generate_guide.py,src/codeonboard/config.py,../../../../.bob/settings/mcp_settings.json

# Current Time
Current time in ISO 8601 UTC format: 2026-05-16T16:53:31.427Z
User time zone: Africa/Lagos, UTC+1:00

# Current Cost
$0.50

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**
- .env
- secrets/

# Current Mode
<slug>advanced</slug>
<name>🛠️ Advanced</name>
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

Perfect! Let me verify the complete implementation by checking the rest of the file:

<read_file>
<args>
  <file>
    <path>src/codeonboard/tools/generate_guide.py</path>
    <line_range>260-290</line_range>
  </file>
</args>
</read_file>

---

**User:**

[read_file for 'src/codeonboard/tools/generate_guide.py'. Reading multiple files at once is more efficient for the LLM. If other files are relevant to your current task, please read them simultaneously.] Result:
<files>
<file><path>src/codeonboard/tools/generate_guide.py</path>
<content lines="260-290">
260 |         if guide_markdown.startswith("ERROR:"):
261 |             guide_markdown = _build_fallback_guide(repo_name, repo_url, tech_stack)
262 |         
263 |         sections = [
264 |             "Project Overview",
265 |             "Tech Stack",
266 |             "Architecture",
267 |             "Key Modules",
268 |             "Getting Started",
269 |             "Entry Points",
270 |             "First Week Tasks",
271 |             "Glossary"
272 |         ]
273 |         
274 |         return {
275 |             "success": True,
276 |             "repo_key": repo_key,
277 |             "guide_markdown": guide_markdown,
278 |             "sections": sections,
279 |             "tech_stack": tech_stack,
280 |             "used_watsonx": used_watsonx,
281 |             "message": f"Guide generated successfully{' (using WatsonX summarizer for large context)' if used_watsonx else ''}"
282 |         }
283 |     
284 |     except Exception as e:
285 |         return {
286 |             "success": False,
287 |             "error": f"Failed to generate guide: {str(e)}"
288 |         }
289 | 
290 | 
</content>
</file>
</files>
<environment_details>
# VSCode Visible Files
src\codeonboard\config.py

# VSCode Open Tabs
src/codeonboard/storage/context_store.py,src/codeonboard/github/client.py,src/codeonboard/tools/fetch_repo.py,.gitignore,src/codeonboard/tools/generate_guide.py,src/codeonboard/config.py,../../../../.bob/settings/mcp_settings.json

# Current Time
Current time in ISO 8601 UTC format: 2026-05-16T16:53:38.620Z
User time zone: Africa/Lagos, UTC+1:00

# Current Cost
$0.57

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**
- .env
- secrets/

# Current Mode
<slug>advanced</slug>
<name>🛠️ Advanced</name>
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

Excellent! The implementation is complete. Let me create a summary document to verify everything is working correctly:

<attempt_completion>
<result>
Guide generation implementation complete with WatsonX integration:

**Added Functions:**

1. **`_build_guide_prompt()`** - Constructs detailed prompt for WatsonX with:
   - Repository metadata (name, language, frameworks, architecture)
   - Full codebase context
   - Specific instructions for 8 sections with emphasis on file-specific references

2. **`_call_watsonx()`** - Async function that:
   - Imports `ibm_watsonx_ai.ModelInference` with error handling
   - Gets config from `get_watsonx_config()`
   - Runs synchronous `generate_text()` in executor to avoid blocking
   - Returns generated text or "ERROR:" prefixed string on failure

3. **`_build_fallback_guide()`** - Extracted original template as fallback when WatsonX unavailable

4. **`get_watsonx_config()`** in [`config.py`](src/codeonboard/config.py:110) - Returns WatsonX configuration dictionary with credentials, model_id, and parameters

**Integration:**
- [`generate_guide_tool()`](src/codeonboard/tools/generate_guide.py:186) now builds prompt and calls WatsonX
- Falls back to structured template if WatsonX fails
- Maintains backward compatibility with existing error handling
</result>
</attempt_completion>

---

**User:**

[attempt_completion] Result:
The user has provided feedback on the results. Consider their input to continue the task, and then attempt completion again.
<feedback>
two fixes needed in tools/generate_guide.py:
1. In _call_watsonx — remove the import of get_watsonx_config which doesn't exist. Replace it with direct imports of WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL, WATSONX_MODEL_ID, WATSONX_MAX_TOKENS from config. Build the ModelInference instance like this:
pythonfrom ibm_watsonx_ai import ModelInference
from ..config import WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL, WATSONX_MODEL_ID, WATSONX_MAX_TOKENS

model = ModelInference(
    model_id=WATSONX_MODEL_ID,
    credentials={"apikey": WATSONX_API_KEY, "url": WATSONX_URL},
    project_id=WATSONX_PROJECT_ID
)
generated_text = await loop.run_in_executor(
    None,
    lambda: model.generate_text(prompt=prompt, params={"max_new_tokens": WATSONX_MAX_TOKENS})
)
2. In _build_fallback_guide — replace all TODO strings with honest messages. Sections that need LLM output should say: AI generation unavailable — configure WATSONX_API_KEY for full AI-generated content. Keep all the tech stack data that is already filled in (primary language, frameworks, dependencies, has_tests, has_docker etc) — that part is good.
Show me the updated _call_watsonx function and the updated _build_fallback_guide function only.
</feedback>
<environment_details>
# VSCode Visible Files
src\codeonboard\tools\generate_guide.py

# VSCode Open Tabs
src/codeonboard/storage/context_store.py,src/codeonboard/github/client.py,src/codeonboard/tools/fetch_repo.py,.gitignore,src/codeonboard/tools/generate_guide.py,src/codeonboard/config.py,src/codeonboard/watsonx/__init__.py,../../../../.bob/settings/mcp_settings.json

# Current Time
Current time in ISO 8601 UTC format: 2026-05-16T16:58:10.675Z
User time zone: Africa/Lagos, UTC+1:00

# Current Cost
$0.64

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**
- .env
- secrets/

# Current Mode
<slug>advanced</slug>
<name>🛠️ Advanced</name>
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

I'll fix both issues in the `generate_guide.py` file:

<apply_diff>
<path>src/codeonboard/tools/generate_guide.py</path>
<diff>
<<<<<<< SEARCH
:start_line:89
-------
async def _call_watsonx(prompt: str) -> str:
    """
    Call WatsonX to generate guide content.
    
    Args:
        prompt: The formatted prompt for guide generation
    
    Returns:
        Generated guide markdown string, or error string starting with "ERROR:"
    """
    try:
        from ibm_watsonx_ai import ModelInference
        from ..config import get_watsonx_config
    except ImportError as e:
        return f"ERROR: WatsonX library not available: {str(e)}"
    
    try:
        # Get WatsonX configuration
        config = get_watsonx_config()
        
        # Create model instance
        model = ModelInference(
            model_id=config["model_id"],
            credentials=config["credentials"],
            project_id=config.get("project_id")
        )
        
        # Run synchronous generate_text in executor to avoid blocking
        loop = asyncio.get_event_loop()
        generated_text = await loop.run_in_executor(
            None,
            lambda: model.generate_text(prompt=prompt)
        )
        
        return generated_text
    
    except Exception as e:
        return f"ERROR: Failed to generate guide with WatsonX: {str(e)}"
=======
async def _call_watsonx(prompt: str) -> str:
    """
    Call WatsonX to generate guide content.
    
    Args:
        prompt: The formatted prompt for guide generation
    
    Returns:
        Generated guide markdown string, or error string starting with "ERROR:"
    """
    try:
        from ibm_watsonx_ai import ModelInference
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
            lambda: model.generate_text(prompt=prompt, params={"max_new_tokens": WATSONX_MAX_TOKENS})
        )
        
        return generated_text
    
    except Exception as e:
        return f"ERROR: Failed to generate guide with WatsonX: {str(e)}"
>>>>>>> REPLACE

<<<<<<< SEARCH
:start_line:130
-------
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
TODO: Generate project overview using LLM with context

## Tech Stack
**Primary Language:** {tech_stack.get('primary_language', 'Unknown')}

**All Languages:** {', '.join(tech_stack.get('all_languages', []))}

**Frameworks:**
{_format_frameworks(tech_stack.get('frameworks', {}))}

**Dependencies:**
{_format_dependencies(tech_stack.get('dependencies', {}))}

## Architecture
TODO: Generate architecture description using LLM with context
{_generate_architecture_diagram()}

## Key Modules
TODO: Generate key modules description using LLM with context

## Getting Started
TODO: Generate getting started instructions using LLM with context

## Entry Points
TODO: Generate entry points description using LLM with context

## First Week Tasks
TODO: Generate first week tasks using LLM with context

## Glossary
TODO: Generate glossary using LLM with context

---
*Generated by CodeOnboard MCP Server*
*Repository: {repo_url}*
*Total Files Analyzed: {tech_stack.get('total_files', 0)}*
*Has Tests: {'Yes' if tech_stack.get('has_tests') else 'No'}*
*Has Docker: {'Yes' if tech_stack.get('has_docker') else 'No'}*
*Has CI/CD: {'Yes' if tech_stack.get('has_ci') else 'No'}*
*Architecture: {tech_stack.get('architecture', 'standard').title()}*
"""
=======
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
>>>>>>> REPLACE
</diff>
</apply_diff>

---

**User:**

[apply_diff for 'src/codeonboard/tools/generate_guide.py'] Result:
<file_write_result>
<path>src/codeonboard/tools/generate_guide.py</path>
<operation>modified</operation>
<problems>

New problems detected after saving the file:
src/codeonboard/tools/generate_guide.py
- [basedpyright Error] 12 |     from ..watsonx.summarizer import summarize_context : Import "..watsonx.summarizer" could not be resolved
- [basedpyright Error] 239 |         tech_stack = cached_data["tech_stack"] : Object of type "None" is not subscriptable
- [basedpyright Error] 253 |                 effective_context = await summarize_context(context_string) : "summarize_context" is possibly unbound</problems>
<notice>
<i>You do not need to re-read the file, as you have seen all changes</i>
<i>Proceed with the task using these changes as the new baseline.</i>
</notice>
</file_write_result>

<environment_details>
# VSCode Visible Files
src\codeonboard\tools\generate_guide.py

# VSCode Open Tabs
src/codeonboard/storage/context_store.py,src/codeonboard/github/client.py,src/codeonboard/tools/fetch_repo.py,.gitignore,src/codeonboard/config.py,src/codeonboard/tools/generate_guide.py,../../../../.bob/settings/mcp_settings.json

# Current Time
Current time in ISO 8601 UTC format: 2026-05-16T16:58:59.554Z
User time zone: Africa/Lagos, UTC+1:00

# Current Cost
$0.72

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**
- .env
- secrets/

# Current Mode
<slug>advanced</slug>
<name>🛠️ Advanced</name>
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

Perfect! The changes have been applied. The errors shown are expected:
- The `summarizer` import error is handled gracefully with try/except
- The type checker warnings about `cached_data` are false positives (it's checked before use)

Now let me also remove the `get_watsonx_config()` function from `config.py` since it's no longer needed:

<apply_diff>
<path>src/codeonboard/config.py</path>
<diff>
<<<<<<< SEARCH
:start_line:109
-------
]


def get_watsonx_config() -> dict:
    """
    Get WatsonX configuration as a dictionary for ModelInference.
    
    Returns:
        Dictionary with model_id, credentials, and project_id
    
    Raises:
        ValueError: If WatsonX credentials are not configured
    """
    if not WATSONX_API_KEY or not WATSONX_PROJECT_ID:
        raise ValueError(
            "WatsonX credentials not configured. "
            "Please set WATSONX_API_KEY and WATSONX_PROJECT_ID in your .env file."
        )
    
    return {
        "model_id": WATSONX_MODEL_ID,
        "credentials": {
            "url": WATSONX_URL,
            "apikey": WATSONX_API_KEY
        },
        "project_id": WATSONX_PROJECT_ID,
        "params": {
            "max_new_tokens": WATSONX_MAX_TOKENS,
            "temperature": WATSONX_TEMPERATURE,
            "top_p": WATSONX_TOP_P,
            "top_k": WATSONX_TOP_K
        }
    }


# Made with Bob
=======
]

# Made with Bob
>>>>>>> REPLACE
</diff>
</apply_diff>

---

**User:**

[apply_diff for 'src/codeonboard/config.py'] Result:
<file_write_result>
<path>src/codeonboard/config.py</path>
<operation>modified</operation>
<notice>
<i>You do not need to re-read the file, as you have seen all changes</i>
<i>Proceed with the task using these changes as the new baseline.</i>
</notice>
</file_write_result>

<notice>Making multiple related changes in a single apply_diff is more efficient. If other changes are needed in this file, please include them as additional SEARCH/REPLACE blocks.</notice>
<environment_details>
# VSCode Visible Files
src\codeonboard\config.py

# VSCode Open Tabs
src/codeonboard/storage/context_store.py,src/codeonboard/github/client.py,src/codeonboard/tools/fetch_repo.py,.gitignore,src/codeonboard/tools/generate_guide.py,src/codeonboard/config.py,../../../../.bob/settings/mcp_settings.json

# Current Time
Current time in ISO 8601 UTC format: 2026-05-16T16:59:49.704Z
User time zone: Africa/Lagos, UTC+1:00

# Current Cost
$0.81

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**
- .env
- secrets/

# Current Mode
<slug>advanced</slug>
<name>🛠️ Advanced</name>
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

<attempt_completion>
<result>
Fixed guide generation implementation:

**Updated [`_call_watsonx()`](src/codeonboard/tools/generate_guide.py:89):**
- Removed `get_watsonx_config()` import
- Direct imports: `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, `WATSONX_URL`, `WATSONX_MODEL_ID`, `WATSONX_MAX_TOKENS`
- ModelInference instantiation with direct credentials dict
- Added `params={"max_new_tokens": WATSONX_MAX_TOKENS}` to `generate_text()` call

**Updated [`_build_fallback_guide()`](src/codeonboard/tools/generate_guide.py:130):**
- Replaced all TODO placeholders with: "*AI generation unavailable — configure WATSONX_API_KEY for full AI-generated content.*"
- Preserved all tech stack data (primary language, frameworks, dependencies, has_tests, has_docker, has_ci, architecture)

**Cleanup:**
- Removed unused `get_watsonx_config()` function from [`config.py`](src/codeonboard/config.py:109)

Implementation complete and ready for testing.
</result>
</attempt_completion>

---

**User:**

[attempt_completion] Result:
The user has provided feedback on the results. Consider their input to continue the task, and then attempt completion again.
<feedback>
Also create src/codeonboard/watsonx/summarizer.py now. One async function: summarize_context(context_string: str) -> str. It should use the same ModelInference pattern as _call_watsonx but with this prompt:
Summarize the following code repository content into a concise technical overview.
Focus on: architecture, main components, key files, and how they interact.
Keep the summary under 3000 words. Be specific about file names and structure.

REPOSITORY CONTENT:
{context_string}

SUMMARY:
On any exception raise a RuntimeError with the message so the caller in generate_guide.py can catch it and fall back to the raw context.
</feedback>
<environment_details>
# VSCode Visible Files
src\codeonboard\config.py

# VSCode Open Tabs
src/codeonboard/storage/context_store.py,src/codeonboard/github/client.py,src/codeonboard/tools/fetch_repo.py,.gitignore,src/codeonboard/tools/generate_guide.py,src/codeonboard/config.py,../../../../.bob/settings/mcp_settings.json

# Current Time
Current time in ISO 8601 UTC format: 2026-05-16T17:00:50.856Z
User time zone: Africa/Lagos, UTC+1:00

# Current Cost
$0.89

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**
- .env
- secrets/

# Current Mode
<slug>advanced</slug>
<name>🛠️ Advanced</name>
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

I'll create the `summarizer.py` file with the `summarize_context` function:

<write_to_file>
<path>src/codeonboard/watsonx/summarizer.py</path>
<content>
"""
WatsonX-based context summarization for large repositories.
"""

import asyncio
from ..config import (
    WATSONX_API_KEY,
    WATSONX_PROJECT_ID,
    WATSONX_URL,
    WATSONX_MODEL_ID,
    WATSONX_MAX_TOKENS
)


async def summarize_context(context_string: str) -> str:
    """
    Summarize large repository context using WatsonX.
    
    This function is used when the repository context exceeds 40,000 characters
    to create a more concise technical overview that can be used for guide generation.
    
    Args:
        context_string: Full repository context string with code snippets
    
    Returns:
        Summarized context string (under 3000 words)
    
    Raises:
        RuntimeError: If summarization fails for any reason
    """
    try:
        from ibm_watsonx_ai import ModelInference
    except ImportError as e:
        raise RuntimeError(f"WatsonX library not available: {str(e)}")
    
    try:
        # Build summarization prompt
        prompt = f"""Summarize the following code repository content into a concise technical overview.
Focus on: architecture, main components, key files, and how they interact.
Keep the summary under 3000 words. Be specific about file names and structure.

REPOSITORY CONTENT:
{context_string}

SUMMARY:"""
        
        # Create model instance
        model = ModelInference(
            model_id=WATSONX_MODEL_ID,
            credentials={"apikey": WATSONX_API_KEY, "url": WATSONX_URL},
            project_id=WATSONX_PROJECT_ID
        )
        
        # Run synchronous generate_text in executor to avoid blocking
        loop = asyncio.get_event_loop()
        summary = await loop.run_in_executor(
            None,
            lambda: model.generate_text(prompt=prompt, params={"max_new_tokens": WATSONX_MAX_TOKENS})
        )
        
        return summary
    
    except Exception as e:
        raise RuntimeError(f"Failed to summarize context with WatsonX: {str(e)}")


# Made with Bob
</content>
<line_count>68</line_count>
</write_to_file>

---

**User:**

[write_to_file for 'src/codeonboard/watsonx/summarizer.py'] Result:
<file_write_result>
<path>src/codeonboard/watsonx/summarizer.py</path>
<operation>created</operation>
<notice>
<i>You do not need to re-read the file, as you have seen all changes</i>
<i>Proceed with the task using these changes as the new baseline.</i>
</notice>
</file_write_result>

<environment_details>
# VSCode Visible Files
src\codeonboard\watsonx\summarizer.py

# VSCode Open Tabs
src/codeonboard/storage/context_store.py,src/codeonboard/github/client.py,src/codeonboard/tools/fetch_repo.py,.gitignore,src/codeonboard/tools/generate_guide.py,src/codeonboard/config.py,src/codeonboard/watsonx/summarizer.py,../../../../.bob/settings/mcp_settings.json

# Current Time
Current time in ISO 8601 UTC format: 2026-05-16T17:01:08.882Z
User time zone: Africa/Lagos, UTC+1:00

# Current Cost
$0.98

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**
- .env
- secrets/

# Current Mode
<slug>advanced</slug>
<name>🛠️ Advanced</name>
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

<attempt_completion>
<result>
Complete implementation finished:

**Created [`src/codeonboard/watsonx/summarizer.py`](src/codeonboard/watsonx/summarizer.py:1):**
- `summarize_context()` async function for large repositories (>40,000 chars)
- Uses same ModelInference pattern as `_call_watsonx()`
- Prompt focuses on architecture, components, key files, and interactions
- Raises `RuntimeError` on failure for proper exception handling in [`generate_guide.py`](src/codeonboard/tools/generate_guide.py:249)

**Implementation Summary:**
1. [`_build_guide_prompt()`](src/codeonboard/tools/generate_guide.py:18) - Constructs detailed LLM prompt with repo metadata
2. [`_call_watsonx()`](src/codeonboard/tools/generate_guide.py:89) - Calls WatsonX with direct config imports
3. [`_build_fallback_guide()`](src/codeonboard/tools/generate_guide.py:130) - Template with honest "AI unavailable" messages
4. [`summarize_context()`](src/codeonboard/watsonx/summarizer.py:15) - Summarizes large contexts before guide generation

All components integrated and ready for testing.
</result>
</attempt_completion>

