"""Сборка агента: LLM (MiMo, OpenAI-совместимый API) + системный промпт + api_tool."""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from tools.api_tool import api_tool

PROJECT_ROOT = Path(__file__).resolve().parent
SYSTEM_PROMPT_PATH = PROJECT_ROOT / "prompts" / "system.md"

DEFAULT_MODEL = "xiaomi/mimo-v2.6-flash"


def load_system_prompt() -> str:
    """Загрузить системный промпт агента из prompts/system.md."""
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def build_agent():
    """Собрать агента: модель + system prompt + tool api_tool."""
    load_dotenv(PROJECT_ROOT / ".env")
    model = ChatOpenAI(
        base_url=os.environ["MIMO_BASE_URL"],
        api_key=os.environ["MIMO_API_KEY"],
        model=os.environ.get("MIMO_MODEL", DEFAULT_MODEL),
        temperature=0,
    )
    return create_agent(
        model=model,
        tools=[api_tool],
        system_prompt=load_system_prompt(),
    )
