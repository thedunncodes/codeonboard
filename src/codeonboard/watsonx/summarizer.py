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
        from ibm_watsonx_ai.foundation_models import ModelInference
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
            lambda: model.chat(
                messages=[{"role": "user", "content": prompt}],
                params={"max_new_tokens": WATSONX_MAX_TOKENS}
            )
        )

        return summary["choices"][0]["message"]["content"]
    
    except Exception as e:
        raise RuntimeError(f"Failed to summarize context with WatsonX: {str(e)}")


# Made with Bob