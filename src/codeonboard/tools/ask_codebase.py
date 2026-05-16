"""
MCP tool for answering questions about a repository's codebase.
"""

import re

from ..storage.context_store import ContextStore
from ..utils.validators import validate_repo_url, parse_github_url
from .generate_guide import _call_watsonx

# Try to import watsonx summarizer, but don't fail if not configured
try:
    from ..watsonx.summarizer import summarize_context
    WATSONX_AVAILABLE = True
except Exception:
    WATSONX_AVAILABLE = False


async def ask_codebase_tool(repo_url: str, question: str) -> dict:
    """
    Answer questions about a repository's codebase using AI.
    
    This tool:
    1. Validates the repository URL and question
    2. Checks if repo is cached (returns error if not)
    3. Gets context string from cache
    4. Builds a focused Q&A prompt with the question and context
    5. Returns the answer with relevant file references
    
    Args:
        repo_url: GitHub repository URL
        question: Question about the codebase
    
    Returns:
        Dictionary with the answer and relevant file references
    """
    try:
        # Validate URL
        is_valid, error_msg = validate_repo_url(repo_url)
        if not is_valid:
            return {
                "success": False,
                "error": error_msg
            }
        
        # Validate question
        if not question or not question.strip():
            return {
                "success": False,
                "error": "Question is required"
            }
        
        if len(question.strip()) < 3:
            return {
                "success": False,
                "error": "Question is too short — please be more specific"
            }
        
        # Extract repo_key
        owner, repo_name = parse_github_url(repo_url)
        repo_key = f"{owner}/{repo_name}"
        
        # Check if repo is in cache
        store = ContextStore()
        cached_data = store.get(repo_key)
        
        if not cached_data:
            return {
                "success": False,
                "error": f"Repository '{repo_key}' not loaded. Please run the fetch_repo tool first with this URL: {repo_url}"
            }
        
        # Get context string
        context_string = store.get_context_string(repo_key)
        
        if not context_string:
            return {
                "success": False,
                "error": "No repository context available"
            }
        
        # Get tech stack for additional context
        tech_stack = cached_data["tech_stack"]
        
        # Build Q&A prompt for watsonx
        qa_prompt = f"""You are an expert software engineer analyzing a codebase.
Answer the following question about the repository based on the code provided.
Be SPECIFIC — reference actual file names, function names, and line numbers from the code.
If you cannot find the answer in the code, say so honestly.

REPOSITORY: {repo_key}
PRIMARY LANGUAGE: {tech_stack.get('primary_language', 'Unknown')}
TOTAL FILES: {tech_stack.get('total_files', 0)}

QUESTION: {question}

CODEBASE:
{context_string}

Provide a clear, concise answer that:
1. Directly answers the question
2. References specific files and code snippets when relevant
3. Explains the reasoning behind your answer
4. Admits if the information is not available in the provided code

ANSWER:"""
        
        # Call watsonx to generate answer
        watsonx_result = await _call_watsonx(qa_prompt)
        
        # Check if watsonx call failed
        if watsonx_result.startswith("ERROR:"):
            answer = f"""⚠️ WatsonX is not configured. Here's the context available for your question:

**Question:** {question}

**Repository:** {repo_key}
**Primary Language:** {tech_stack.get('primary_language', 'Unknown')}
**Total Files:** {tech_stack.get('total_files', 0)}

**Context Available:** {len(context_string)} characters of code context

To get AI-generated answers, please configure WatsonX by setting the following environment variables:
- WATSONX_API_KEY
- WATSONX_PROJECT_ID
- WATSONX_URL

**Raw Context Preview:**
{context_string[:2000]}{'...' if len(context_string) > 2000 else ''}
"""
        else:
            answer = watsonx_result
        
        # Extract file paths mentioned in the answer (placeholder logic)
        # In real implementation, the LLM would identify relevant files
        relevant_files = _extract_file_references(context_string, question)
        
        return {
            "success": True,
            "repo_key": repo_key,
            "question": question,
            "answer": answer,
            "relevant_files": relevant_files[:5],  # Limit to top 5 most relevant
            "context_chars": len(context_string),
            "message": "Answer generated successfully"
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to answer question: {str(e)}"
        }


def _extract_file_references(context_string: str, question: str) -> list[str]:
    """
    Extract file paths from context that might be relevant to the question.
    
    This is a placeholder implementation. In the real version, the LLM
    would identify which files are most relevant to answering the question.
    
    Args:
        context_string: Full repository context
        question: User's question
    
    Returns:
        List of file paths that might be relevant
    """
    # Extract all file paths from context
    file_pattern = r"=== FILE: ([^\s]+) ==="
    all_files = re.findall(file_pattern, context_string)
    
    # Simple heuristic: look for keywords in question and match to file paths
    question_lower = question.lower()
    keywords = question_lower.split()
    
    relevant = []
    for file_path in all_files:
        file_lower = file_path.lower()
        # Check if any keyword appears in the file path
        if any(keyword in file_lower for keyword in keywords if len(keyword) > 3):
            relevant.append(file_path)
    
    # If no matches, return first few files as fallback
    if not relevant:
        relevant = all_files[:5]
    
    return relevant

# Made with Bob
