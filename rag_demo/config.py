"""Environment configuration without storing or printing credentials."""

import os


def load_environment(project: str = "rag-demo-diagnosis") -> None:
    names = ("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "LANGSMITH_API_KEY",
             "LANGSMITH_ENDPOINT", "LANGSMITH_TRACING", "LANGSMITH_PROJECT",
             "LANGSMITH_AGENT_ID", "LANGSMITH_AGENT_ENVIRONMENT")
    if os.name == "nt":
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            for name in names:
                if not os.environ.get(name):
                    try:
                        os.environ[name] = winreg.QueryValueEx(key, name)[0]
                    except FileNotFoundError:
                        pass
    missing = [n for n in ("ANTHROPIC_API_KEY", "LANGSMITH_API_KEY") if not os.environ.get(n)]
    if missing:
        raise ValueError("Missing environment variables: " + ", ".join(missing))
    os.environ.setdefault("LANGSMITH_ENDPOINT", "https://eu.api.smith.langchain.com")
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    if os.environ["LANGSMITH_TRACING"].lower() != "true":
        raise ValueError("LANGSMITH_TRACING must be true for this traced demo.")
    if not os.environ.get("LANGSMITH_AGENT_ID"):
        os.environ.setdefault("LANGSMITH_PROJECT", project)
