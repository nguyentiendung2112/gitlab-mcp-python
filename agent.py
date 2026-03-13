"""
GitLab Programmatic Agent
Replaces the MCP server with a direct Anthropic API tool-calling loop.

Usage:
    uv run python agent.py "Review MR #42 in project 123 and summarize it"
    uv run python agent.py  # interactive mode
"""
import os
import sys
import json
import logging
import gitlab
import anthropic
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("gitlab-agent")

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------

def get_gitlab_client() -> gitlab.Gitlab:
    token = os.environ.get("GITLAB_TOKEN")
    if not token:
        raise ValueError("GITLAB_TOKEN environment variable is required")
    url = os.environ.get("GITLAB_URL", "https://gitlab.com")
    return gitlab.Gitlab(url, private_token=token)


def get_anthropic_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is required")
    return anthropic.Anthropic(api_key=api_key)


# ---------------------------------------------------------------------------
# Tool definitions (mirrors server.py tools exactly)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "create_issue",
        "description": "Create a new issue in a GitLab project",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "The ID of the project"},
                "title": {"type": "string", "description": "The title of the issue"},
                "description": {"type": "string", "description": "The description of the issue"},
                "labels": {"type": "string", "description": "Comma-separated list of labels"},
            },
            "required": ["project_id", "title"],
        },
    },
    {
        "name": "get_issue",
        "description": "Get details of a specific issue",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "The ID of the project"},
                "issue_iid": {"type": "integer", "description": "The internal ID of the issue"},
            },
            "required": ["project_id", "issue_iid"],
        },
    },
    {
        "name": "create_merge_request",
        "description": "Create a new merge request",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "The ID of the project"},
                "source_branch": {"type": "string", "description": "The source branch"},
                "target_branch": {"type": "string", "description": "The target branch"},
                "title": {"type": "string", "description": "The title of the merge request"},
                "description": {"type": "string", "description": "The description of the merge request"},
            },
            "required": ["project_id", "source_branch", "target_branch", "title"],
        },
    },
    {
        "name": "get_merge_request",
        "description": "Get details of a merge request",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "The ID of the project"},
                "mr_iid": {"type": "integer", "description": "The internal ID of the merge request"},
            },
            "required": ["project_id", "mr_iid"],
        },
    },
    {
        "name": "get_merge_request_commits",
        "description": "Get commits of a merge request",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "The ID of the project"},
                "mr_iid": {"type": "integer", "description": "The internal ID of the merge request"},
            },
            "required": ["project_id", "mr_iid"],
        },
    },
    {
        "name": "get_merge_request_diffs",
        "description": "Get diffs of a merge request",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "The ID of the project"},
                "mr_iid": {"type": "integer", "description": "The internal ID of the merge request"},
            },
            "required": ["project_id", "mr_iid"],
        },
    },
    {
        "name": "get_merge_request_pipelines",
        "description": "Get pipelines attached to a merge request",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "The ID of the project"},
                "mr_iid": {"type": "integer", "description": "The internal ID of the merge request"},
            },
            "required": ["project_id", "mr_iid"],
        },
    },
    {
        "name": "get_pipeline_jobs",
        "description": "Get jobs of a pipeline",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "The ID of the project"},
                "pipeline_id": {"type": "integer", "description": "The ID of the pipeline"},
            },
            "required": ["project_id", "pipeline_id"],
        },
    },
    {
        "name": "manage_pipeline",
        "description": "Retry or cancel a pipeline",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "The ID of the project"},
                "pipeline_id": {"type": "integer", "description": "The ID of the pipeline"},
                "action": {"type": "string", "enum": ["retry", "cancel"], "description": "Action to perform"},
            },
            "required": ["project_id", "pipeline_id", "action"],
        },
    },
    {
        "name": "create_merge_request_note",
        "description": "Create a note (comment) on a merge request",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "The ID of the project"},
                "mr_iid": {"type": "integer", "description": "The internal ID of the merge request"},
                "body": {"type": "string", "description": "The content of the note"},
            },
            "required": ["project_id", "mr_iid", "body"],
        },
    },
    {
        "name": "get_merge_request_discussions",
        "description": "Get all discussion threads in a merge request",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "The ID of the project"},
                "mr_iid": {"type": "integer", "description": "The internal ID of the merge request"},
            },
            "required": ["project_id", "mr_iid"],
        },
    },
    {
        "name": "reply_to_merge_request_discussion",
        "description": "Reply to an existing discussion thread in a merge request",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "The ID of the project"},
                "mr_iid": {"type": "integer", "description": "The internal ID of the merge request"},
                "discussion_id": {"type": "string", "description": "The ID of the discussion thread to reply to"},
                "body": {"type": "string", "description": "The content of the reply"},
            },
            "required": ["project_id", "mr_iid", "discussion_id", "body"],
        },
    },
    {
        "name": "create_merge_request_discussion",
        "description": "Create a review comment on a specific line of code in a merge request",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "The ID of the project"},
                "mr_iid": {"type": "integer", "description": "The internal ID of the merge request"},
                "body": {"type": "string", "description": "The content of the comment"},
                "base_sha": {"type": "string", "description": "The base SHA of the merge request"},
                "start_sha": {"type": "string", "description": "The start SHA of the merge request"},
                "head_sha": {"type": "string", "description": "The head SHA of the merge request"},
                "new_path": {"type": "string", "description": "The new file path"},
                "old_path": {"type": "string", "description": "The old file path"},
                "new_line": {"type": "integer", "description": "The new line number (null if deleted line)"},
                "old_line": {"type": "integer", "description": "The old line number (null if added line)"},
            },
            "required": ["project_id", "mr_iid", "body", "base_sha", "start_sha", "head_sha", "new_path", "old_path"],
        },
    },
    {
        "name": "create_workitem_note",
        "description": "Create a note (comment) on an issue or merge request",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "The ID of the project"},
                "item_type": {"type": "string", "enum": ["issue", "merge_request"], "description": "Type of item"},
                "item_iid": {"type": "integer", "description": "The internal ID of the issue or MR"},
                "body": {"type": "string", "description": "The content of the note"},
            },
            "required": ["project_id", "item_type", "item_iid", "body"],
        },
    },
    {
        "name": "get_workitem_notes",
        "description": "Get notes (comments) of an issue or merge request",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "The ID of the project"},
                "item_type": {"type": "string", "enum": ["issue", "merge_request"], "description": "Type of item"},
                "item_iid": {"type": "integer", "description": "The internal ID of the issue or MR"},
            },
            "required": ["project_id", "item_type", "item_iid"],
        },
    },
    {
        "name": "search",
        "description": "Search in GitLab (projects, issues, or merge requests)",
        "input_schema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "enum": ["projects", "issues", "merge_requests"],
                    "description": "Scope to search in",
                },
                "query": {"type": "string", "description": "Search query text"},
            },
            "required": ["scope", "query"],
        },
    },
    {
        "name": "search_labels",
        "description": "Search labels in a project",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "The ID of the project"},
                "query": {"type": "string", "description": "Search query text"},
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "semantic_code_search",
        "description": "Search code in a project using keywords",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "The ID of the project"},
                "query": {"type": "string", "description": "The search query text"},
            },
            "required": ["project_id", "query"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool executor
# ---------------------------------------------------------------------------

def execute_tool(gl: gitlab.Gitlab, name: str, inputs: dict) -> str:
    """Execute a GitLab tool and return the result as a string."""
    try:
        project = None
        if "project_id" in inputs and name != "search":
            project = gl.projects.get(inputs["project_id"])

        if name == "create_issue":
            data = {"title": inputs["title"]}
            if "description" in inputs:
                data["description"] = inputs["description"]
            if "labels" in inputs:
                data["labels"] = inputs["labels"]
            issue = project.issues.create(data)
            return f"Created issue #{issue.iid}: {issue.web_url}"

        elif name == "get_issue":
            issue = project.issues.get(inputs["issue_iid"])
            return (
                f"Issue #{issue.iid}: {issue.title}\n"
                f"State: {issue.state}\n"
                f"URL: {issue.web_url}\n\n"
                f"{issue.description}"
            )

        elif name == "create_merge_request":
            data = {
                "source_branch": inputs["source_branch"],
                "target_branch": inputs["target_branch"],
                "title": inputs["title"],
            }
            if "description" in inputs:
                data["description"] = inputs["description"]
            mr = project.mergerequests.create(data)
            return f"Created MR !{mr.iid}: {mr.web_url}"

        elif name == "get_merge_request":
            mr = project.mergerequests.get(inputs["mr_iid"])
            return (
                f"MR !{mr.iid}: {mr.title}\n"
                f"State: {mr.state}\n"
                f"URL: {mr.web_url}\n\n"
                f"{mr.description}"
            )

        elif name == "get_merge_request_commits":
            mr = project.mergerequests.get(inputs["mr_iid"])
            commits = mr.commits()
            lines = [f"- {c.short_id}: {c.title}" for c in commits]
            return "\n".join(lines) if lines else "No commits found"

        elif name == "get_merge_request_diffs":
            mr = project.mergerequests.get(inputs["mr_iid"])
            changes = mr.changes()
            diffs = [
                f"File: {c.get('new_path')}\n{c.get('diff')}"
                for c in changes.get("changes", [])
            ]
            return "\n".join(diffs) if diffs else "No diffs found"

        elif name == "get_merge_request_pipelines":
            mr = project.mergerequests.get(inputs["mr_iid"])
            pipelines = mr.pipelines()
            lines = [f"- Pipeline {p['id']} ({p['status']}): {p['web_url']}" for p in pipelines]
            return "\n".join(lines) if lines else "No pipelines found"

        elif name == "get_pipeline_jobs":
            pipeline = project.pipelines.get(inputs["pipeline_id"])
            jobs = pipeline.jobs.list()
            lines = [f"- Job {j.id} ({j.name}): {j.status}" for j in jobs]
            return "\n".join(lines) if lines else "No jobs found"

        elif name == "manage_pipeline":
            pipeline = project.pipelines.get(inputs["pipeline_id"])
            if inputs["action"] == "retry":
                pipeline.retry()
                return f"Retried pipeline {pipeline.id}"
            elif inputs["action"] == "cancel":
                pipeline.cancel()
                return f"Canceled pipeline {pipeline.id}"

        elif name == "create_merge_request_note":
            mr = project.mergerequests.get(inputs["mr_iid"])
            note = mr.notes.create({"body": inputs["body"]})
            return f"Created note ID {note.id} on MR !{mr.iid}"

        elif name == "get_merge_request_discussions":
            mr = project.mergerequests.get(inputs["mr_iid"])
            discussions = mr.discussions.list(get_all=True)
            parts = []
            for d in discussions:
                notes = d.attributes.get("notes", [])
                first = notes[0] if notes else {}
                position = first.get("position", {})
                location = ""
                if position.get("new_path"):
                    line = position.get("new_line") or position.get("old_line", "?")
                    location = f" [{position['new_path']}:{line}]"
                header = f"Discussion {d.id}{location} ({len(notes)} note{'s' if len(notes) != 1 else ''})"
                note_lines = [f"  [{n['id']}] {n['author']['username']}: {n['body']}" for n in notes]
                parts.append(header + "\n" + "\n".join(note_lines))
            return "\n\n".join(parts) if parts else "No discussions found"

        elif name == "reply_to_merge_request_discussion":
            mr = project.mergerequests.get(inputs["mr_iid"])
            discussion = mr.discussions.get(inputs["discussion_id"])
            note = discussion.notes.create({"body": inputs["body"]})
            return f"Replied with note ID {note['id']} to discussion {inputs['discussion_id']} on MR !{mr.iid}"

        elif name == "create_merge_request_discussion":
            mr = project.mergerequests.get(inputs["mr_iid"])
            data = {
                "body": inputs["body"],
                "position": {
                    "position_type": "text",
                    "base_sha": inputs["base_sha"],
                    "start_sha": inputs["start_sha"],
                    "head_sha": inputs["head_sha"],
                    "new_path": inputs["new_path"],
                    "old_path": inputs["old_path"],
                },
            }
            if inputs.get("new_line"):
                data["position"]["new_line"] = inputs["new_line"]
            if inputs.get("old_line"):
                data["position"]["old_line"] = inputs["old_line"]
            discussion = mr.discussions.create(data)
            return f"Created discussion ID {discussion.id} on MR !{mr.iid}"

        elif name == "create_workitem_note":
            if inputs["item_type"] == "issue":
                item = project.issues.get(inputs["item_iid"])
            else:
                item = project.mergerequests.get(inputs["item_iid"])
            note = item.notes.create({"body": inputs["body"]})
            return f"Created note ID {note.id}"

        elif name == "get_workitem_notes":
            if inputs["item_type"] == "issue":
                item = project.issues.get(inputs["item_iid"])
            else:
                item = project.mergerequests.get(inputs["item_iid"])
            notes = item.notes.list(get_all=False)
            lines = [f"Note {n.id} by {n.author['username']}:\n{n.body}" for n in notes]
            return "\n\n".join(lines) if lines else "No notes found"

        elif name == "search":
            results = gl.search(inputs["scope"], inputs["query"])
            if not results:
                return f"No results for '{inputs['query']}' in {inputs['scope']}"
            lines = []
            for r in results[:10]:
                scope = inputs["scope"]
                if scope == "projects":
                    lines.append(f"- Project {r['id']}: {r['name_with_namespace']} ({r['web_url']})")
                elif scope == "issues":
                    lines.append(f"- Issue {r.get('iid')} in project {r.get('project_id')}: {r.get('title')}")
                elif scope == "merge_requests":
                    lines.append(f"- MR {r.get('iid')} in project {r.get('project_id')}: {r.get('title')}")
            return "\n".join(lines)

        elif name == "search_labels":
            query = inputs.get("query", "")
            labels = project.labels.list(search=query if query else None)
            lines = [f"- {l.name} ({l.color}): {l.description or 'No description'}" for l in labels]
            return "\n".join(lines) if lines else "No labels found"

        elif name == "semantic_code_search":
            results = project.search("blobs", inputs["query"])
            lines = [
                f"File: {r['path']}\n```\n{r.get('data', '')}\n```"
                for r in results[:10]
            ]
            return "\n---\n".join(lines) if lines else "No results found"

        else:
            return f"Unknown tool: {name}"

    except Exception as e:
        logger.error(f"Tool '{name}' failed: {e}")
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Agentic loop
# ---------------------------------------------------------------------------

def run_agent(prompt: str, model: str = "claude-opus-4-5", max_tokens: int = 4096) -> str:
    """Run the agent loop until Claude produces a final answer."""
    gl = get_gitlab_client()
    client = get_anthropic_client()

    messages = [{"role": "user", "content": prompt}]
    print(f"\n🤖 User: {prompt}\n")

    while True:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            tools=TOOLS,
            messages=messages,
        )

        # Collect any text from this response turn
        final_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                final_text += block.text

        if response.stop_reason == "end_turn":
            print(f"✅ Claude: {final_text}")
            return final_text

        if response.stop_reason == "tool_use":
            # Append Claude's response (including tool_use blocks) to history
            messages.append({"role": "assistant", "content": response.content})

            # Execute every requested tool
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  🔧 {block.name}({json.dumps(block.input, ensure_ascii=False)})")
                    result = execute_tool(gl, block.name, block.input)
                    print(f"     → {result[:200]}{'...' if len(result) > 200 else ''}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            # Feed results back to Claude
            messages.append({"role": "user", "content": tool_results})

        else:
            # Unexpected stop reason — return whatever text we have
            print(f"⚠️  Unexpected stop_reason: {response.stop_reason}")
            return final_text


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Single prompt from command line
        user_prompt = " ".join(sys.argv[1:])
        run_agent(user_prompt)
    else:
        # Interactive REPL mode
        print("GitLab Agent (type 'exit' to quit)\n")
        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                print("Goodbye!")
                break
            run_agent(user_input)
            print()
