from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI


SYSTEM_PROMPT = """You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply."""


@dataclass(frozen=True)
class AssistantAnswer:
    text: str
    run_status: str
    thread_id: str
    run_id: str
    error_code: str | None
    error_message: str | None


def create_optibot_assistant(
    *,
    api_key: str,
    vector_store_id: str,
    model: str,
) -> str:
    client = OpenAI(api_key=api_key)
    assistant = client.beta.assistants.create(
        name="OptiBot Mini-Clone",
        model=model,
        instructions=SYSTEM_PROMPT,
        tools=[{"type": "file_search"}],
        tool_resources={
            "file_search": {
                "vector_store_ids": [vector_store_id],
            }
        },
    )
    return assistant.id


def ask_optibot(
    *,
    api_key: str,
    assistant_id: str,
    question: str,
) -> AssistantAnswer:
    client = OpenAI(api_key=api_key)
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": question,
            }
        ],
    )
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant_id,
    )

    messages = client.beta.threads.messages.list(thread_id=thread.id, order="desc")
    answer_text = _first_text_message(messages.data)

    last_error = run.last_error

    return AssistantAnswer(
        text=answer_text,
        run_status=run.status,
        thread_id=thread.id,
        run_id=run.id,
        error_code=last_error.code if last_error else None,
        error_message=last_error.message if last_error else None,
    )


def _first_text_message(messages: list) -> str:
    for message in messages:
        if message.role != "assistant":
            continue

        for block in message.content:
            if block.type == "text":
                return block.text.value

    return ""
