# clent

Terminal-first LLM chat client built on **LangGraph** with **MCP (Model Context Protocol)** tool calling.

`clent` runs an interactive chat loop, persists sessions locally, and can call tools exposed by built-in MCP servers (e.g. a local shell tool and Gmail tools).

## Features

- Interactive CLI chat with streaming responses (via `langchain-openai`).
- Tool calling via MCP (built-in servers included).
- Local session history with `/new`, `/sessions`, `/resume`, `/rename`, `/compact`, `/clear`.
- First-run configuration wizard (`/config`) that writes a per-user `settings.json`.
- Works with OpenAI-compatible endpoints via an optional `base_url`.

## Requirements

- Python `>=3.12`

## Install

```bash
pip install clent
```

## Quickstart

Run:

```bash
clent
```

On first run, `clent` launches a setup wizard to collect:

- API key
- (Optional) Base URL for your model provider
- Default model name (and optional “thinking” / “code” model names)
- Sessions directory
- Theme

After saving settings, `clent` asks you to restart and then you can chat normally.

## Commands

Inside the app:

- `/?` or `/help` — show commands
- `/new` — start a new session
- `/sessions` — list sessions
- `/resume` — resume a previous session
- `/rename` — rename the current session (LLM-generated)
- `/compact` — summarize and compact session history
- `/clear` — delete current session history
- `/config` — re-run the setup wizard
- `/bye` — exit

## Configuration

`clent` stores user settings under a per-user “clent home” directory.

Override the location with:

```bash
CLENT_HOME=/path/to/dir clent
```

The wizard writes a `settings.json` that looks like:

```json
{
  "env": {
    "CLENT_API_KEY": "…",
    "CLENT_BASE_URL": "",
    "CLENT_MODELS": { "default": "…", "thinking": "", "code": "" }
  },
  "theme": "dark",
  "sessions_dir": "sessions"
}
```

Notes:

- `CLENT_API_KEY` and `CLENT_MODELS.default` are required.
- `CLENT_BASE_URL` is optional (use it for OpenAI-compatible providers).
- `sessions_dir` can be absolute or relative (relative paths resolve inside `CLENT_HOME`).

## Gmail tools (optional)

`clent` includes a built-in Gmail MCP server. To enable it:

1. Create an OAuth “Desktop app” client in Google Cloud Console.
2. Download the credentials JSON file.
3. Save it as `credentials.json` in your `CLENT_HOME` directory.

The first time the agent uses a Gmail tool, it will prompt you to complete OAuth and will attempt to persist a token to `CLENT_HOME/token.json`.

## Tooling / Development

This repo uses `uv` (optional). Typical workflow:

```bash
uv sync
uv run clent
```

## Troubleshooting

- If startup immediately launches the wizard again, re-run `/config` and ensure you set both the API key and default model name.
- If `clent` cannot write to the default config directory, set `CLENT_HOME` to a writable path.

## Safety

`clent` ships with a local “shell” tool (MCP server) that can execute commands on your machine when the model requests it. Only use `clent` with models/providers you trust, and review tool calls in the terminal before relying on their results.
