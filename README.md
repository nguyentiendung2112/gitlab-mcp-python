# GitLab MCP Server (Python)

A Model Context Protocol (MCP) server for interacting with GitLab. This server provides various tools to manage issues, merge requests, pipelines, and perform searches on GitLab.

## Prerequisites

- Python 3.12+
- `uv` package manager (recommended) or `pip`

## Setup

1. Clone this repository (or navigate to this directory).
2. Install dependencies:
   ```bash
   uv sync
   # or
   pip install mcp python-gitlab python-dotenv
   ```
3. Set your environment variables (e.g. in a `.env` file):
   - `GITLAB_TOKEN`: Your GitLab personal access token (required)
   - `GITLAB_URL`: Your GitLab instance URL (defaults to `https://gitlab.com`)

## Running the Server

Run the server using `uv`:

```bash
uv run python server.py
```

Or using standard Python:

```bash
python server.py
```

## Available Tools

- `get_mcp_server_version`: Get the version of the MCP server
- `create_issue`: Create a new issue
- `get_issue`: Get issue details
- `create_merge_request`: Create a new merge request
- `get_merge_request`: Get merge request details
- `get_merge_request_commits`: List commits of a MR
- `get_merge_request_diffs`: Get diffs of a MR
- `get_merge_request_pipelines`: List pipelines attached to a MR
- `get_pipeline_jobs`: List jobs of a pipeline
- `manage_pipeline`: Retry or cancel a pipeline
- `create_merge_request_note`: Add a general note to a merge request
- `create_merge_request_discussion`: Create a review comment on a specific line of code in a MR
- `create_workitem_note`: Add a note to an issue or MR
- `get_workitem_notes`: Get notes of an issue or MR
- `search`: Search projects, issues, or MRs
- `search_labels`: Search project labels
- `semantic_code_search`: Search code within a project
