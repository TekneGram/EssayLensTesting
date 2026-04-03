from __future__ import annotations

from pathlib import Path

from essaylens_testing.config.schema import ContextConfig
from essaylens_testing.context.file_ingest import read_text_file
from essaylens_testing.context.truncation import truncate_text


def build_messages(
    *,
    input_text: str,
    context: ContextConfig,
    repo_root: Path,
    system_prompt_override: Path | None = None,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []

    system_prompt_path = system_prompt_override
    if system_prompt_path is not None and not system_prompt_path.is_absolute():
        system_prompt_path = (repo_root / system_prompt_path).resolve()
    if system_prompt_path is None and context.system_prompt_path:
        system_prompt_path = Path(context.system_prompt_path)
        if not system_prompt_path.is_absolute():
            system_prompt_path = (repo_root / system_prompt_path).resolve()

    if system_prompt_path is not None:
        messages.append({"role": "system", "content": read_text_file(system_prompt_path)})

    content = truncate_text(input_text, context.max_input_chars, context.strategy)
    messages.append({"role": "user", "content": content})
    return messages
