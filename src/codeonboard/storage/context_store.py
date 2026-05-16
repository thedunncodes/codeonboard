"""
Context storage module for caching repository data using SQLite.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from ..config import STORAGE_DIR
from ..github.models import RepoTree


class ContextStore:
    """SQLite-based storage for repository context and analysis results."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the context store with SQLite database.
        
        Args:
            db_path: Path to SQLite database file. Defaults to STORAGE_DIR/context.db
        """
        self.db_path = db_path or (STORAGE_DIR / "context.db")
        self._init_database()
    
    def _init_database(self) -> None:
        """Create the database table if it doesn't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS repository_context (
                        repo_key TEXT PRIMARY KEY,
                        repo_url TEXT NOT NULL,
                        context TEXT NOT NULL,
                        tech_stack TEXT NOT NULL,
                        fetched_at TEXT NOT NULL,
                        expires_at TEXT NOT NULL
                    )
                """)
                conn.commit()
        except sqlite3.Error as e:
            raise ValueError(f"Failed to initialize database: {e}") from e
    
    def save(self, repo_key: str, repo_url: str, repo_tree: RepoTree, tech_stack: dict) -> None:
        """
        Save repository context to storage.
        
        Args:
            repo_key: Repository identifier (e.g., "owner/repo")
            repo_url: Original GitHub URL
            repo_tree: RepoTree object with repository data
            tech_stack: Tech stack analysis dictionary
        """
        try:
            # Serialize repo_tree to dict with datetime serialization
            context_dict = repo_tree.model_dump(mode='json')
            context_json = json.dumps(context_dict)
            tech_stack_json = json.dumps(tech_stack)
            
            # Calculate timestamps
            fetched_at = datetime.now().isoformat()
            expires_at = (datetime.now() + timedelta(hours=24)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO repository_context 
                    (repo_key, repo_url, context, tech_stack, fetched_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (repo_key, repo_url, context_json, tech_stack_json, fetched_at, expires_at))
                conn.commit()
        except (sqlite3.Error, json.JSONDecodeError) as e:
            raise ValueError(f"Failed to save repository context: {e}") from e
    
    def get(self, repo_key: str) -> Optional[dict]:
        """
        Retrieve repository context from storage.
        
        Args:
            repo_key: Repository identifier (e.g., "owner/repo")
        
        Returns:
            Dictionary with context and tech_stack, or None if not found or expired
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT context, tech_stack, expires_at
                    FROM repository_context
                    WHERE repo_key = ?
                """, (repo_key,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                # Check if expired
                expires_at = datetime.fromisoformat(row["expires_at"])
                if datetime.now() > expires_at:
                    self.delete(repo_key)
                    return None
                
                return {
                    "context": json.loads(row["context"]),
                    "tech_stack": json.loads(row["tech_stack"])
                }
        except (sqlite3.Error, json.JSONDecodeError) as e:
            raise ValueError(f"Failed to retrieve repository context: {e}") from e
    
    def get_context_string(self, repo_key: str) -> Optional[str]:
        """
        Get repository context as a formatted string for LLM prompts.
        
        Args:
            repo_key: Repository identifier (e.g., "owner/repo")
        
        Returns:
            Formatted string with all file contents, or None if not found
        """
        data = self.get(repo_key)
        if not data:
            return None
        
        context = data["context"]
        files = context.get("files", [])
        
        MAX_CHARS = 80000
        result = []
        total_chars = 0
        
        for file in files:
            if file.get("content") and not file.get("is_binary"):
                file_header = f"=== FILE: {file['path']} ==="
                file_content = file["content"]
                file_separator = ""
                
                # Calculate size of this file block
                block_size = len(file_header) + len(file_content) + len(file_separator) + 2  # +2 for newlines
                
                # Check if adding this file would exceed the limit
                if total_chars + block_size > MAX_CHARS:
                    result.append("[Context truncated — repository too large]")
                    break
                
                result.append(file_header)
                result.append(file_content)
                result.append(file_separator)
                total_chars += block_size
        
        return "\n".join(result)
    
    def delete(self, repo_key: str) -> None:
        """
        Delete repository context from storage.
        
        Args:
            repo_key: Repository identifier (e.g., "owner/repo")
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM repository_context WHERE repo_key = ?", (repo_key,))
                conn.commit()
        except sqlite3.Error as e:
            raise ValueError(f"Failed to delete repository context: {e}") from e
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from storage.
        
        Returns:
            Number of deleted rows
        """
        try:
            now = datetime.now().isoformat()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM repository_context WHERE expires_at < ?", 
                    (now,)
                )
                conn.commit()
                return cursor.rowcount
        except sqlite3.Error as e:
            raise ValueError(f"Failed to cleanup expired entries: {e}") from e

# Made with Bob
