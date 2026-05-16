"""
Configuration module for loading environment variables and application settings.
"""

import os
import warnings
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# GitHub Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
if not GITHUB_TOKEN:
    raise ValueError(
        "GITHUB_TOKEN environment variable is required. "
        "Please set it in your .env file or environment."
    )

# IBM WatsonX Configuration
WATSONX_API_KEY = os.getenv("WATSONX_API_KEY", "")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "")
WATSONX_URL = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

# Validate WatsonX credentials
if not WATSONX_API_KEY or not WATSONX_PROJECT_ID:
    warnings.warn(
        "WATSONX_API_KEY and WATSONX_PROJECT_ID environment variables are not set. "
        "WatsonX features will not be available. "
        "Please set them in your .env file or environment.",
        RuntimeWarning
    )

# Storage Configuration
STORAGE_DIR = PROJECT_ROOT / "data" / "context"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# GitHub API Configuration
GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"

# File Processing Limits
MAX_FILE_SIZE = 4000  # Maximum characters per file
MAX_FILES_TO_FETCH = 40  # Maximum number of files to fetch from a repository

# Folders to skip during repository analysis
SKIP_FOLDERS = {
    "node_modules",
    ".git",
    "dist",
    "build",
    "__pycache__",
    ".next",
    "vendor",
    "coverage",
}

# Binary file extensions to skip
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".pdf", ".zip", ".tar", ".gz", ".rar", ".7z",
    ".exe", ".dll", ".so", ".dylib",
    ".mp3", ".mp4", ".avi", ".mov", ".wav",
}

# WatsonX Model Configuration
WATSONX_MODEL_ID = os.getenv("WATSONX_MODEL_ID", "ibm/granite-3-8b-instruct")
WATSONX_MAX_TOKENS = int(os.getenv("WATSONX_MAX_TOKENS", "2048"))
WATSONX_TEMPERATURE = float(os.getenv("WATSONX_TEMPERATURE", "0.7"))
WATSONX_TOP_P = float(os.getenv("WATSONX_TOP_P", "1.0"))
WATSONX_TOP_K = int(os.getenv("WATSONX_TOP_K", "50"))

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# MCP Server Configuration
MCP_SERVER_NAME = "codeonboard"
MCP_SERVER_VERSION = "0.1.0"

# Export all configuration constants
__all__ = [
    "PROJECT_ROOT",
    "GITHUB_TOKEN",
    "WATSONX_API_KEY",
    "WATSONX_PROJECT_ID",
    "WATSONX_URL",
    "STORAGE_DIR",
    "GITHUB_API_BASE_URL",
    "GITHUB_API_VERSION",
    "MAX_FILE_SIZE",
    "MAX_FILES_TO_FETCH",
    "SKIP_FOLDERS",
    "BINARY_EXTENSIONS",
    "WATSONX_MODEL_ID",
    "WATSONX_MAX_TOKENS",
    "WATSONX_TEMPERATURE",
    "WATSONX_TOP_P",
    "WATSONX_TOP_K",
    "LOG_LEVEL",
    "MCP_SERVER_NAME",
    "MCP_SERVER_VERSION",
]

# Made with Bob
