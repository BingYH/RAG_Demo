"""Send one small Claude request and verify its LangSmith trace."""

import os
import time
from uuid import uuid4


def load_environment() -> None:
    # An already-open Windows terminal may not inherit newly added user variables.
    names = (
        "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "LANGSMITH_API_KEY",
        "LANGSMITH_ENDPOINT", "LANGSMITH_TRACING", "LANGSMITH_PROJECT",
        "LANGSMITH_AGENT_ID", "LANGSMITH_AGENT_ENVIRONMENT",
    )
    if os.name == "nt":
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            for name in names:
                if not os.environ.get(name):
                    try:
                        os.environ[name] = winreg.QueryValueEx(key, name)[0]
                    except FileNotFoundError:
                        pass
    missing = [name for name in ("ANTHROPIC_API_KEY", "LANGSMITH_API_KEY")
               if not os.environ.get(name)]
    if missing:
        raise SystemExit("Missing environment variables: " + ", ".join(missing))
    os.environ.setdefault("LANGSMITH_ENDPOINT", "https://eu.api.smith.langchain.com")
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    if os.environ["LANGSMITH_TRACING"].lower() != "true":
        raise SystemExit("Set LANGSMITH_TRACING=true for this smoke check.")
    if not os.environ.get("LANGSMITH_AGENT_ID"):
        os.environ.setdefault("LANGSMITH_PROJECT", "rag-demo-smoke")


def main() -> None:
    load_environment()
    from anthropic import Anthropic
    from langsmith import Client, trace, tracing_context
    from langsmith.wrappers import wrap_anthropic

    model = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-5-5")
    run_id = uuid4()
    client = Client()
    claude = wrap_anthropic(Anthropic(max_retries=0, timeout=30.0))
    prompt = "Reply with exactly: TRACE_OK"
    print("Model:", model)
    with tracing_context(enabled=True, client=client):
        with trace("claude-smoke-test", run_type="chain", run_id=run_id,
                   inputs={"prompt": prompt}, tags=["smoke-test", "synthetic-data"]) as run:
            response = claude.messages.create(
                model=model, max_tokens=32,
                messages=[{"role": "user", "content": prompt}],
            )
            answer = "".join(block.text for block in response.content if block.type == "text")
            run.end(outputs={"answer": answer})
    client.flush()
    print("Response:", answer)
    print("Tokens: input=", response.usage.input_tokens,
          "output=", response.usage.output_tokens)
    # Read-back verifies ingestion rather than assuming a background upload succeeded.
    for attempt in range(5):
        try:
            saved = client.read_run(run_id, load_child_runs=True)
            if saved.end_time and saved.child_runs:
                break
        except Exception:
            if attempt == 4:
                raise
        time.sleep(1)
    else:
        raise RuntimeError("Trace or nested Claude call not visible yet; check LangSmith.")
    if answer.strip() != "TRACE_OK":
        raise RuntimeError("Claude returned unexpected output; inspect the uploaded trace.")
    print("TRACE_VERIFIED:", saved.id)
    print("Trace URL:", client.get_run_url(run=saved))


if __name__ == "__main__":
    main()
