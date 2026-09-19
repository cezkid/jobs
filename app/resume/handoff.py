import json
from pathlib import Path

STRING = {"type": "string"}
NULLABLE = {"type": ["string", "null"]}
JSON_TYPES = {"string": str, "integer": int, "boolean": bool, "null": type(None), "object": dict, "array": list}

# whichever AI user chats with does the writing => no model CLI, any assistant works
TASK = """# Task for the AI assistant

Do this yourself, in this chat - no other program writes it. Follow Rules, read Input, then write
ONE JSON object matching Answer schema to:

    {answer}

Then run `{then}`. It checks your answer; on failure it lists violations - fix the JSON and
run it again.

## Rules

{system}

## Input

{payload}

## Answer schema

```json
{schema}
```
"""


def obj(**props) -> dict:
    return {"type": "object", "properties": props, "required": list(props)}


def array(items: dict) -> dict:
    return {"type": "array", "items": items}


STRINGS = array(STRING)


def write_task(task: Path, answer: Path, system: str, schema: dict, payload: str, then: str) -> None:
    task.parent.mkdir(parents=True, exist_ok=True)
    # stale answer from earlier task must never pass as this one's
    answer.unlink(missing_ok=True)
    task.write_text(TASK.format(answer=answer, then=then, system=system, payload=payload,
                                schema=json.dumps(schema, indent=1)), encoding="utf-8")
    print(f"AI task written: {task}\nanswer goes to: {answer}\nthen run: {then}")


def read_answer(answer: Path, schema: dict) -> dict:
    if not answer.exists():
        raise SystemExit(f"{answer} missing - AI step not done yet (task file sits beside it)")
    try:
        value = json.loads(answer.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{answer}: not valid JSON ({e})") from e
    errors = violations(value, schema, "answer")
    if errors:
        raise SystemExit(f"{answer} does not match schema:\n" + "\n".join(f"  {e}" for e in errors))
    return value


def violations(value, schema: dict, where: str) -> list[str]:
    types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
    # bool subclasses int in Python, never in JSON
    if not any(isinstance(value, JSON_TYPES[t]) and not (t == "integer" and isinstance(value, bool)) for t in types):
        return [f"{where}: expected {' or '.join(types)}, got {type(value).__name__}"]
    out: list[str] = []
    if isinstance(value, dict) and "properties" in schema:
        props = schema["properties"]
        out += [f"{where}: missing {k!r}" for k in schema.get("required", []) if k not in value]
        out += [f"{where}: unknown key {k!r}" for k in value if k not in props]
        for k, sub in props.items():
            if k in value:
                out += violations(value[k], sub, f"{where}.{k}")
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            out += violations(item, schema["items"], f"{where}[{i}]")
    return out
