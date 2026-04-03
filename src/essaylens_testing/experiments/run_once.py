from __future__ import annotations

from pathlib import Path

from essaylens_testing.artifacts.writer import RunArtifactsWriter
from essaylens_testing.client.chat_client import ChatClient
from essaylens_testing.client.json_client import JSONChatClient
from essaylens_testing.client.streaming_client import StreamingChatClient
from essaylens_testing.config.schema import ProfileConfig
from essaylens_testing.context.conversation import build_messages


def run_chat(
    *,
    repo_root: Path,
    profile: ProfileConfig,
    input_text: str,
    stream: bool = False,
    schema_path: Path | None = None,
    system_prompt_path: Path | None = None,
    save_run: bool = False,
) -> tuple[str, Path | None]:
    messages = build_messages(
        input_text=input_text,
        context=profile.context,
        repo_root=repo_root,
        system_prompt_override=system_prompt_path,
    )

    writer = RunArtifactsWriter(repo_root)
    run_dir = writer.create_run_dir(profile.name) if save_run else None

    if run_dir is not None:
        writer.write_json(run_dir, "request.json", {"messages": messages, "profile": profile.to_dict()})

    if stream:
        client = StreamingChatClient(profile)
        chunks: list[str] = []
        for event in client.stream(messages):
            if run_dir is not None:
                writer.append_ndjson(run_dir, "stream.ndjson", event)
            delta = event["choices"][0]["delta"].get("content", "")
            if delta:
                chunks.append(delta)
        text = "".join(chunks)
        if run_dir is not None:
            writer.write_text(run_dir, "response.txt", text)
        return text, run_dir

    if schema_path is not None:
        response = JSONChatClient(profile).chat(messages, schema_path)
    else:
        response = ChatClient(profile).chat(messages)

    if run_dir is not None:
        writer.write_json(run_dir, "response.json", response)

    text = response["choices"][0]["message"]["content"]
    return text, run_dir
