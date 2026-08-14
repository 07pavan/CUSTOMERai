"""
app/agents/llm.py
-----------------
Groq LLM Client Wrapper.

Provides callables for interacting with Groq models:
  - Gemma 2 9B IT (`call_gemma` / `acall_gemma`) — fast, lightweight extraction
  - Llama 3.3 70B Versatile (`call_llama` / `acall_llama`) — complex reasoning, risk assessment, root cause & CAPA

Features
--------
* Reads `GROQ_API_KEY` from `app.core.config.settings`.
* Includes both synchronous and asynchronous callables (FastAPI / LangGraph friendly).
* Robust JSON parser (`call_json` / `acall_json`) with markdown fence stripping and auto-retry on parse failure.
"""

import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Union

from groq import AsyncGroq, Groq

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy Singleton Clients
# ---------------------------------------------------------------------------

_sync_client: Optional[Groq] = None
_async_client: Optional[AsyncGroq] = None


def get_groq_client() -> Groq:
    """Get or initialize the synchronous Groq client."""
    global _sync_client
    if _sync_client is None:
        if not settings.GROQ_API_KEY:
            logger.warning("GROQ_API_KEY is not set in environment or config.")
        _sync_client = Groq(api_key=settings.GROQ_API_KEY)
    return _sync_client


def get_async_groq_client() -> AsyncGroq:
    """Get or initialize the asynchronous Groq client."""
    global _async_client
    if _async_client is None:
        if not settings.GROQ_API_KEY:
            logger.warning("GROQ_API_KEY is not set in environment or config.")
        _async_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    return _async_client


# ---------------------------------------------------------------------------
# Core Execution Callables
# ---------------------------------------------------------------------------

import asyncio
import time

def _call_with_retry(fn, *args, max_retries: int = 3, initial_delay: float = 1.0, **kwargs):
    """Execute sync function with retry on Groq rate limits (429)."""
    delay = initial_delay
    for attempt in range(max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            is_429 = "429" in str(exc) or getattr(exc, "status_code", None) == 429
            if is_429 and attempt < max_retries:
                logger.warning("Groq 429 Rate Limit encountered. Retrying in %.1fs (attempt %d/%d)...", delay, attempt + 1, max_retries)
                time.sleep(delay)
                delay *= 2.0
            else:
                raise

async def _acall_with_retry(afn, *args, max_retries: int = 3, initial_delay: float = 1.0, **kwargs):
    """Execute async function with retry on Groq rate limits (429)."""
    delay = initial_delay
    for attempt in range(max_retries + 1):
        try:
            return await afn(*args, **kwargs)
        except Exception as exc:
            is_429 = "429" in str(exc) or getattr(exc, "status_code", None) == 429
            if is_429 and attempt < max_retries:
                logger.warning("Groq 429 Rate Limit encountered. Retrying in %.1fs (attempt %d/%d)...", delay, attempt + 1, max_retries)
                await asyncio.sleep(delay)
                delay *= 2.0
            else:
                raise

def call_gemma(
    prompt: str,
    system: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> str:
    """
    Synchronous call to Gemma 2 9B IT (Fast model).
    Best for text extraction, field parsing, and fast classification.
    """
    client = get_groq_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    def _do():
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL_FAST,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    return _call_with_retry(_do)


async def acall_gemma(
    prompt: str,
    system: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> str:
    """
    Asynchronous call to Gemma 2 9B IT (Fast model).
    """
    client = get_async_groq_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    async def _ado():
        response = await client.chat.completions.create(
            model=settings.GROQ_MODEL_FAST,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    return await _acall_with_retry(_ado)


def call_llama(
    prompt: str,
    system: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> str:
    """
    Synchronous call to Llama 3.3 70B Versatile with automatic 8B fallback.
    """
    client = get_groq_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    def _do():
        try:
            response = client.chat.completions.create(
                model=settings.GROQ_MODEL_LARGE,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            if "429" in str(exc) or "rate_limit" in str(exc).lower():
                logger.warning("70B rate limited (%s). Fallback to llama-3.1-8b-instant.", exc)
                fallback_res = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=messages,
                    temperature=temperature,
                    max_tokens=min(max_tokens, 2048),
                )
                return fallback_res.choices[0].message.content or ""
            raise

    return _call_with_retry(_do)


async def acall_llama(
    prompt: str,
    system: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> str:
    """
    Asynchronous call to Llama 3.3 70B Versatile with automatic 8B fallback.
    """
    client = get_async_groq_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    async def _ado():
        try:
            response = await client.chat.completions.create(
                model=settings.GROQ_MODEL_LARGE,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            if "429" in str(exc) or "rate_limit" in str(exc).lower():
                logger.warning("70B rate limited (%s). Fallback to llama-3.1-8b-instant.", exc)
                fallback_res = await client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=messages,
                    temperature=temperature,
                    max_tokens=min(max_tokens, 2048),
                )
                return fallback_res.choices[0].message.content or ""
            raise

    return await _acall_with_retry(_ado)


# ---------------------------------------------------------------------------
# JSON Output Helpers (Strip Markdown Fences + Auto-Retry)
# ---------------------------------------------------------------------------

def clean_json_response(raw_text: str) -> str:
    """
    Strips markdown code fences (e.g. ```json ... ```) and leading/trailing
    whitespace to extract clean JSON string.
    """
    text = raw_text.strip()
    # Match ```json ... ``` or ``` ... ```
    pattern = r"^```(?:json)?\s*\n?(.*?)\n?```$"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Fallback: find first '{' or '[' and last '}' or ']'
    first_brace = min(
        [i for i in [text.find("{"), text.find("[")] if i != -1] or [0]
    )
    last_brace = max(
        [i for i in [text.rfind("}"), text.rfind("]")] if i != -1] or [len(text)]
    )
    if first_brace < last_brace:
        return text[first_brace : last_brace + 1].strip()

    return text


def call_json(
    llm_callable: Callable[..., str],
    prompt: str,
    system: Optional[str] = None,
    max_retries: int = 2,
) -> Union[Dict[str, Any], List[Any]]:
    """
    Synchronously invoke an LLM callable and parse output into JSON (dict/list).

    Parameters
    ----------
    llm_callable : call_gemma or call_llama
    prompt       : User prompt text
    system       : Optional system prompt
    max_retries  : Retries on JSON parsing failure

    Returns
    -------
    Parsed dict or list object.
    """
    json_system = (
        (system or "") + "\n\nCRITICAL: Respond ONLY with valid, unformatted JSON. "
        "Do NOT include any explanatory text, markdown formatting, or code blocks outside the JSON."
    ).strip()

    current_prompt = prompt
    last_raw = ""

    for attempt in range(max_retries + 1):
        raw = llm_callable(current_prompt, system=json_system)
        last_raw = raw
        cleaned = clean_json_response(raw)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as err:
            logger.warning(
                "JSON decode error (attempt %d/%d): %s. Raw: %s",
                attempt + 1,
                max_retries + 1,
                err,
                raw[:200],
            )
            if attempt < max_retries:
                current_prompt = (
                    f"{prompt}\n\n"
                    f"Your previous response failed to parse as valid JSON. "
                    f"JSON Error: {err}.\n"
                    f"Previous Output: {raw}\n"
                    f"Please output ONLY valid JSON without markdown code fences."
                )

    raise ValueError(
        f"Failed to parse valid JSON from LLM after {max_retries + 1} attempts. Last raw output:\n{last_raw}"
    )


async def acall_json(
    async_llm_callable: Callable[..., Any],
    prompt: str,
    system: Optional[str] = None,
    max_retries: int = 2,
) -> Union[Dict[str, Any], List[Any]]:
    """
    Asynchronously invoke an LLM callable and parse output into JSON (dict/list).
    """
    json_system = (
        (system or "") + "\n\nCRITICAL: Respond ONLY with valid, unformatted JSON. "
        "Do NOT include any explanatory text, markdown formatting, or code blocks outside the JSON."
    ).strip()

    current_prompt = prompt
    last_raw = ""

    for attempt in range(max_retries + 1):
        raw = await async_llm_callable(current_prompt, system=json_system)
        last_raw = raw
        cleaned = clean_json_response(raw)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as err:
            logger.warning(
                "JSON decode error (attempt %d/%d): %s. Raw: %s",
                attempt + 1,
                max_retries + 1,
                err,
                raw[:200],
            )
            if attempt < max_retries:
                current_prompt = (
                    f"{prompt}\n\n"
                    f"Your previous response failed to parse as valid JSON. "
                    f"JSON Error: {err}.\n"
                    f"Previous Output: {raw}\n"
                    f"Please output ONLY valid JSON without markdown code fences."
                )

    raise ValueError(
        f"Failed to parse valid JSON from LLM after {max_retries + 1} attempts. Last raw output:\n{last_raw}"
    )
