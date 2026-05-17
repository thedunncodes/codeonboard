# CodeOnboard MCP: Repo Onboarding Guide

CodeOnboard is an MCP server that turns any GitHub repository into into a comprehensive guide in seconds. It integrates with your IDE via the Model Context Protocol (MCP) to provide instant answers about your codebase, generate onboarding guides, and create visual architecture diagrams.

## What It Does

New developers joining a project waste hours reading scattered documentation and exploring unfamiliar codebases. CodeOnboard solves this by automatically analyzing any GitHub repository and generating a structured onboarding guide with architecture diagrams, setup instructions, and first-week tasks. It uses IBM watsonx AI to understand the codebase and answer follow-up questions with specific file references, turning days of exploration into minutes of focused learning.

## How It Works

Short architecture explanation with this flow diagram:

```
Developer types in Bob IDE
        ↓
Bob calls CodeOnboard MCP tools
        ↓
fetch_repo → GitHub API → analyzes tech stack
        ↓
generate_guide → watsonx AI → writes ONBOARDING.md
        ↓
ask_codebase → answers follow-up questions with file references
```

## MCP Tools

| Tool | What it does | When to use it |
|------|-------------|----------------|
| `fetch_repo` | Fetches repository from GitHub, analyzes file structure, detects tech stack, frameworks, and dependencies | First step before generating guides or asking questions about a new repository |
| `generate_guide` | Uses watsonx AI to generate comprehensive onboarding guide with architecture, setup steps, key modules, and first-week tasks | When you need a complete developer onboarding document for a repository |
| `ask_codebase` | Answers specific questions about the codebase using AI with file references and code snippets | When you need to understand specific features, patterns, or implementations in the code |

## Setup

### Prerequisites

- Python 3.11+
- IBM Bob IDE
- GitHub Personal Access Token
- IBM watsonx credentials

### Installation

```bash
git clone https://github.com/thedunncodes/codeonboard
cd codeonboard
pip install -r requirements.txt
cp .env.example .env
# Fill in your credentials in .env
```

### Environment Variables

Create a `.env` file with these values:

```
GITHUB_TOKEN=your_github_personal_access_token
WATSONX_API_KEY=your_ibm_cloud_api_key
WATSONX_PROJECT_ID=your_watsonx_project_id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=meta-llama/llama-3-3-70b-instruct
MCP_HOST=0.0.0.0
MCP_PORT=8000
```

### Connect to Bob IDE

Add this to your Bob IDE MCP settings:

```json
{
  "mcpServers": {
    "codeonboard": {
      "command": "python",
      "args": ["run_server.py"],
      "cwd": "/path/to/codeonboard",
      "env": {
        "GITHUB_TOKEN": "your_github_token",
        "WATSONX_API_KEY": "your_watsonx_api_key",
        "WATSONX_PROJECT_ID": "your_project_id",
        "WATSONX_URL": "https://us-south.ml.cloud.ibm.com"
      }
    }
  }
}
```
#### NOTE
- `command` should be the full path to your Python executable, e.g., `/usr/bin/python3` or `C:\Python311\python.exe` if not in PATH. And `path/to/venv/Scripts/python.exe` if using a virtual environment.

- Make sure to replace the placeholder values with your actual credentials.

### Configure Onboard Mode (Optional but Recommended)

The custom onboard mode makes CodeOnboard seamless — one sentence triggers 
the full pipeline automatically.

In Bob IDE, go to **Settings → Modes → New Mode** and fill in:

**Slug:** `onboard`

**Name:** `Onboard`

**Description:** CodeOnboard specialist mode. Analyzes any GitHub repository using the CodeOnboard MCP tools to generate comprehensive developer onboarding guides. Automatically fetches repository context, generates AI-powered guides with architecture diagrams, setup instructions, and first-week tasks, then answers follow-up questions about the codebase.
**Scope:** Global

**Role definition:** 
```
You are CodeOnboard, an expert developer onboarding specialist. When asked to onboard onto a codebase or understand a repository:
1. Always call fetch_repo first with the GitHub URL
2. Then call generate_guide to produce the full onboarding guide
3. Write the guide content to ONBOARDING.md in the current project
4. Confirm what was generated and offer to answer questions using ask_codebase
```

**When to use:** onboard, understand this repo, explain this codebase, new repo,
generate guide, what does this project do
**Allowed tools:**
- ✅ Read files
- ✅ Edit files  
- ❌ Use browser
- ❌ Execute commands
- ✅ Switch modes
- ✅ Use MCP tools


**Set scope to Global** so the mode is available across all projects.

Once configured, trigger it with:
> *"Onboard me onto https://github.com/owner/repo"*

## Deployment

CodeOnboard supports two transport modes — local stdio for Bob IDE and remote SSE for deployment.

### Local (default)
Bob IDE spawns the server as a subprocess. See Connect to Bob IDE above.

### Remote — Render / Railway

```bash
python run_server.py --http
```

**Bob IDE remote MCP config:**
```json
{
  "mcpServers": {
    "codeonboard-remote": {
      "url": "https://your-app.onrender.com/sse"
    }
  }
}
```

**Endpoints:**
- Health check: `GET /health`
- MCP SSE: `/sse`

## Demo

Trigger CodeOnboard in Bob IDE using the Onboard mode (see setup above) 
or any mode with these prompts:

1. "Onboard me onto https://github.com/owner/repo"
2. "Generate an onboarding guide for this repository"  
3. "Where is authentication handled in this codebase?"
4. "What are the entry points for this application?"

> **Note:** The Onboard mode automates the full pipeline. Without it, 
> you can still call each tool manually — Bob will use them when asked.

## Tech Stack

- Python
- FastMCP
- IBM Bob IDE
- IBM watsonx AI (meta-llama/llama-3-3-70b-instruct)
- GitHub REST API
- SQLite

## Built With IBM Bob 🤖

This entire project was developed in partnership with IBM Bob as the AI coding assistant. Bob handled planning, project scaffolding, code generation, debugging, and code review throughout the development process. Every iteration and refinement is documented in the `bob_sessions/` folder, showcasing Bob's capabilities as a development partner.

## IBM Bob Hackathon 2026

Built for the IBM Bob Hackathon, May 15-17 2026 on lablab.ai