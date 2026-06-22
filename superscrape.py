#!/usr/bin/env python3
import argparse
import copy
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import dotenv
import requests
from supabase import create_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("superscrape")
log_path = f"logs/superscrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
fh = logging.FileHandler(log_path, mode="w", encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
log.addHandler(fh)


def resolve_key(env_var: str, ssh_name: str) -> str:
    val = os.getenv(env_var)
    if val:
        return val
    ssh_path = Path.home() / ".ssh" / ssh_name
    if ssh_path.exists():
        log.info("Loaded %s from %s", env_var, ssh_path)
        return ssh_path.read_text(encoding="utf-8").strip()
    return ""


def load_env():
    dotenv.load_dotenv()

    jina_key = resolve_key("JINA_API_KEY", "jina_key")
    supabase_key = resolve_key("SUPABASE_SERVICE_KEY", "supabase_service_key")
    supabase_url = os.getenv("SUPABASE_URL", "")
    groq_key = resolve_key("GROQ_API_KEY", "GROQ_API_KEY")
    nvidia_key = resolve_key("NVIDIA_NIM_API_KEY", "NVIDIA_NIM_API_KEY.txt")

    missing = []
    if not jina_key:
        missing.append("JINA_API_KEY")
    if not supabase_url:
        missing.append("SUPABASE_URL")
    if not supabase_key:
        missing.append("SUPABASE_SERVICE_KEY")
    if missing:
        log.error("Missing required env vars: %s", ", ".join(missing))
        sys.exit(1)

    return {
        "jina_key": jina_key,
        "ollama_url": os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/"),
        "ollama_model": os.getenv("OLLAMA_MODEL"),
        "groq_api_key": groq_key,
        "groq_model": os.getenv("GROQ_MODEL"),
        "nvidia_api_key": nvidia_key,
        "nvidia_model": os.getenv("NVIDIA_NIM_MODEL"),
        "supabase_url": supabase_url,
        "supabase_key": supabase_key,
        "table_fallback": os.getenv("SUPABASE_TABLE", "species"),
    }


def resolve_table_name(args, env, schema_path: Path) -> str:
    if args.table:
        return args.table
    stem = schema_path.stem
    if stem.endswith(".schema"):
        stem = stem[: -len(".schema")]
    return stem or env["table_fallback"]


def resolve_schema_path(args, table: str) -> Path:
    if args.schema:
        p = Path(args.schema)
    else:
        p = Path(f"{table}.schema.json")
    if not p.exists():
        log.error("Schema file not found: %s", p)
        sys.exit(1)
    return p


def get_existing_row(client, table: str, url: str) -> tuple:
    resp = (
        client.table(table)
        .select("*")
        .eq("source_url", url)
        .execute()
    )
    if not resp or not hasattr(resp, "data"):
        return None, None
    rows = resp.data or []
    if rows:
        return rows[0].get("raw_markdown"), rows[0]
    return None, None


def fetch_via_jina(url: str, api_key: str) -> str:
    log.info("Fetching %s via Jina...", url)
    resp = requests.get(
        f"https://r.jina.ai/{url}",
        headers={"Authorization": f"Bearer {api_key}", "Accept": "text/markdown"},
        timeout=60,
    )
    if resp.status_code != 200:
        log.error("Jina fetch failed (%s): %s", resp.status_code, resp.text[:300])
        sys.exit(1)
    return resp.text


def save_raw_markdown(client, table: str, url: str, markdown: str):
    log.info("Saving raw markdown to Supabase...")
    row = {"source_url": url, "raw_markdown": markdown}
    result = client.table(table).upsert(row, on_conflict="source_url").execute()
    if hasattr(result, "error") and result.error:
        log.error("Failed to save raw markdown: %s", result.error)
        sys.exit(1)


def clean_schema_value(value):
    if isinstance(value, dict):
        if "type" in value:
            return value
        props = {k: clean_schema_value(v) for k, v in value.items()}
        return {"type": "object", "properties": props, "additionalProperties": False}
    if isinstance(value, list):
        if not value:
            return {"type": "array", "items": {"type": "string"}}
        item = value[0]
        if isinstance(item, dict):
            props = {k: clean_schema_value(v) for k, v in item.items()}
            return {"type": "array", "items": {"type": "object", "properties": props}}
        return {"type": "array", "items": clean_schema_value(item)}
    if value is None:
        return {"type": "string"}
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, (int, float)):
        return {"type": "number"}
    return {"type": "string"}


def extract_one_property(
    markdown: str, key: str, prop_schema: dict, required_keys: list,
    provider: dict
):
    sub = {
        "type": "object",
        "properties": {key: prop_schema},
    }
    if key in required_keys:
        sub["required"] = [key]

    log.info("Extracting '%s' with %s (%s)...", key, provider["label"], provider["model"])

    system_prompt = (
        "You extract structured data from web content. "
        "Return ONLY a single JSON object matching the provided schema. "
        "Do not include explanations, markdown fences, or any text outside the JSON."
    )
    user_content = f"Extract the '{key}' data from this content into JSON matching this schema:\n{sub}\n\nContent:\n{markdown}"

    head = markdown[:200].replace("\n", " ")
    log.info("Schema for '%s':\n%s", key, json.dumps(sub, indent=2))
    log.info("Content head: %s...", head)

    payload = {
        "model": provider["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        **provider["json_mode"],
    }
    if provider["type"] == "ollama":
        payload["options"] = {"temperature": 0}
    else:
        payload["temperature"] = 0

    for attempt in range(2):
        resp = requests.post(
            provider["endpoint"],
            json=payload,
            headers=provider.get("headers", {}),
            timeout=180,
        )
        if resp.status_code != 200:
            log.error("%s error (%s): %s", provider["label"], resp.status_code, resp.text[:300])
            sys.exit(1)

        if provider["type"] == "ollama":
            raw = ""
            for line in resp.text.strip().splitlines():
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                    raw += chunk.get("message", {}).get("content", "")
                except json.JSONDecodeError:
                    pass
            raw = raw.strip()
        else:
            raw = resp.json()["choices"][0]["message"]["content"].strip()

        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            raw = raw.rsplit("```", 1)[0].strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            if attempt == 0:
                log.warning("%s returned invalid JSON for '%s', retrying...", provider["label"], key)
                payload["messages"][1][
                    "content"
                ] += "\n\nPREVIOUS RESPONSE WAS NOT VALID JSON. Return ONLY valid JSON this time."
                continue
            log.error("%s returned invalid JSON for '%s' after retry.", provider["label"], key)
            log.error("Raw: %s", raw[:500])
            sys.exit(1)

        return parsed.get(key)

    return None


def update_column(client, table: str, url: str, column: str, value):
    log.info("Uprowing '%s' to Supabase...", column)
    row = {"source_url": url, column: value}
    result = client.table(table).upsert(row, on_conflict="source_url").execute()
    if hasattr(result, "error") and result.error:
        log.error("Supabase update error for '%s': %s", column, result.error)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Scrape a URL, extract data via LLM JSON mode, store in Supabase."
    )
    parser.add_argument("url", help="HTTPS URL to scrape")
    parser.add_argument(
        "schema",
        nargs="?",
        help="Path to JSON Schema file (default: <table>.schema.json)",
    )
    parser.add_argument("--table", help="Supabase table name")
    parser.add_argument("--skip", help="Comma-separated column names to skip")
    parser.add_argument(
        "--provider", choices=["ollama", "groq", "nvidia"], default="ollama",
        help="LLM provider to use (default: ollama)"
    )
    args = parser.parse_args()

    env = load_env()
    schema_path = resolve_schema_path(args, env["table_fallback"])
    table = resolve_table_name(args, env, schema_path)

    with open(schema_path) as f:
        schema = json.load(f)

    properties = schema.get("properties", {})
    required_keys = schema.get("required", [])
    skip_cols = [s.strip() for s in args.skip.split(",")] if args.skip else []
    columns = []
    for c in properties.keys():
        if c in skip_cols:
            log.info("'%s' skipped via --skip flag", c)
        else:
            columns.append(c)

    client = create_client(env["supabase_url"], env["supabase_key"])

    if args.provider == "groq":
        if not env["groq_api_key"]:
            log.error("GROQ_API_KEY not set in .env or ~/.ssh/groq_key")
            sys.exit(1)
        provider = {
            "type": "groq",
            "label": "Groq",
            "model": env["groq_model"],
            "endpoint": "https://api.groq.com/openai/v1/chat/completions",
            "headers": {"Authorization": f"Bearer {env['groq_api_key']}"},
            "json_mode": {"response_format": {"type": "json_object"}},
        }
    elif args.provider == "nvidia":
        if not env["nvidia_api_key"]:
            log.error("NVIDIA_NIM_API_KEY not set in .env or ~/.ssh/NVIDIA_NIM_API_KEY")
            sys.exit(1)
        provider = {
            "type": "nvidia",
            "label": "NVIDIA NIM",
            "model": env["nvidia_model"],
            "endpoint": "https://integrate.api.nvidia.com/v1/chat/completions",
            "headers": {"Authorization": f"Bearer {env['nvidia_api_key']}"},
            "json_mode": {"response_format": {"type": "json_object"}},
        }
    else:
        provider = {
            "type": "ollama",
            "label": "Ollama",
            "model": env["ollama_model"],
            "endpoint": f"{env['ollama_url']}/api/chat",
            "headers": {},
            "json_mode": {"format": "json"},
        }
    log.info("Using provider: %s (%s)", provider["label"], provider["model"])

    markdown, existing_row = get_existing_row(client, table, args.url)
    if not markdown:
        markdown = fetch_via_jina(args.url, env["jina_key"])
        save_raw_markdown(client, table, args.url, markdown)

    for key in columns:
        if existing_row:
            val = existing_row.get(key)
            if val is not None and val != {} and val != []:
                log.info("'%s' already has data, skipping", key)
                continue
        raw_schema = properties[key]
        prop_schema = clean_schema_value(copy.deepcopy(raw_schema))
        value = extract_one_property(
            markdown, key, prop_schema, required_keys, provider
        )
        if value is not None:
            update_column(client, table, args.url, key, value)

    log.info("Done.")


if __name__ == "__main__":
    main()
