"""Read back completed traces through LangSmith's v2 API."""

import os
import re
import time


def verify_trace(root, expected_steps: int, expected_names=()) -> str:
    from langsmith import Langsmith

    url = root.get_url()
    match = re.search(r"/projects/p/([^/]+)/", url)
    if not match:
        raise RuntimeError("Cannot determine trace project from returned URL.")
    api = Langsmith(api_key=os.environ["LANGSMITH_API_KEY"],
                    base_url=os.environ["LANGSMITH_ENDPOINT"], timeout=20.0, max_retries=0)
    for attempt in range(5):
        rows = list(api.runs.query_v2(project_ids=[match[1]], trace_id=str(root.id), page_size=100,
                    selects=["ID", "NAME", "RUN_TYPE", "END_TIME", "OUTPUTS"]))
        names = {row.name for row in rows} if expected_names else set()
        if len(rows) >= expected_steps and all(row.end_time for row in rows) and set(expected_names) <= names:
            print("TRACE_VERIFIED:", root.id, "steps=", len(rows), flush=True)
            return url
        if attempt < 4:
            time.sleep(2)
    raise RuntimeError("Trace upload is not fully visible yet; inspect LangSmith before rerunning the model.")
