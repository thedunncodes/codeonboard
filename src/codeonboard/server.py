"""
Main MCP server entry point for CodeOnboard.

This server provides three tools for analyzing GitHub repositories
and generating developer onboarding guides using IBM watsonx AI.
"""

from mcp.server.fastmcp import FastMCP

from .config import MCP_SERVER_NAME, MCP_SERVER_VERSION
from .tools.fetch_repo import fetch_repo_tool
from .tools.generate_guide import generate_guide_tool
from .tools.ask_codebase import ask_codebase_tool


# Create the MCP server instance
mcp = FastMCP(MCP_SERVER_NAME)


@mcp.tool()
async def fetch_repo(repo_url: str) -> dict:
    """
    Fetch and analyze a GitHub repository. Provides file structure, tech stack, 
    frameworks, and dependencies. Run this first before generating a guide or 
    asking questions.
    
    Args:
        repo_url: GitHub repository URL (e.g. https://github.com/owner/repo)
    
    Returns:
        Dictionary with repository metadata, tech stack, and file structure
    """
    return await fetch_repo_tool(repo_url)


@mcp.tool()
async def generate_guide(repo_url: str, include_diagrams: bool = True) -> dict:
    """
    Generate a comprehensive developer onboarding guide for a repository. 
    Automatically fetches the repo if not already loaded. Returns a full 
    markdown guide with architecture, setup steps, key modules and first 
    week tasks.
    
    Args:
        repo_url: GitHub repository URL
        include_diagrams: Include Mermaid architecture diagrams in the guide (default: True)
    
    Returns:
        Dictionary with the generated markdown guide and metadata
    """
    return await generate_guide_tool(repo_url, include_diagrams)


@mcp.tool()
async def ask_codebase(repo_url: str, question: str) -> dict:
    """
    Answer questions about a repository's codebase. Requires fetch_repo to be 
    run first. Returns specific answers with file references.
    
    Args:
        repo_url: GitHub repository URL
        question: Your question about the codebase (e.g. Where is authentication 
                 handled? How do I add a new API endpoint?)
    
    Returns:
        Dictionary with the answer and relevant file references
    """
    return await ask_codebase_tool(repo_url, question)

@mcp.tool()
async def check_config() -> dict:
    """
    Check if all required credentials are configured.
    
    Returns:
        Dictionary showing which credentials are set and their values
    """
    from .config import WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL, GITHUB_TOKEN, WATSONX_MODEL_ID
    return {
        "github_token_set": bool(GITHUB_TOKEN),
        "watsonx_api_key_set": bool(WATSONX_API_KEY),
        "watsonx_project_id_set": bool(WATSONX_PROJECT_ID),
        "watsonx_url": WATSONX_URL,
        "watsonx_model": WATSONX_MODEL_ID
    }


def run():
    """
    Run the MCP server with stdio transport.
    
    This is the entry point that Bob IDE uses to connect to the server.
    """
    mcp.run(transport="stdio")

def run_http(host: str = "0.0.0.0", port: int = 8000):
    """Run the MCP server with SSE transport for remote deployment."""
    import uvicorn
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route, Mount
    from starlette.middleware import Middleware
    from starlette.middleware.cors import CORSMiddleware

    async def health(request):
        return JSONResponse({
            "status": "ok",
            "service": "CodeOnboard MCP Server",
            "version": MCP_SERVER_VERSION,
            "tools": ["fetch_repo", "generate_guide", "ask_codebase"],
            "transport": "sse",
            "mcp_endpoint": "/sse",
            "docs": "https://github.com/thedunncodes/codeonboard"
        })

    mcp_app = mcp.streamable_http_app()

    middleware = [
        Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    ]

    app = Starlette(
        routes=[
            Route("/health", health),
            Mount("/", app=mcp_app),
        ],
        middleware=middleware
    )

    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    import sys
    if "--http" in sys.argv:
        run_http()
    else:
        run() # Default to stdio for local Bob IDE


__all__ = ["mcp", "run"]

# Made with Bob