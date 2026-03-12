import os
import sys
import logging
from typing import Any, Dict, List, Optional
import gitlab
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("gitlab-mcp-server")

SERVER_VERSION = "0.1.0"

app = Server("gitlab-mcp-server")

# Try to initialize gitlab client
GITLAB_URL = os.environ.get("GITLAB_URL", "https://gitlab.com")
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN")

if not GITLAB_TOKEN:
    logger.warning("GITLAB_TOKEN environment variable is not set. API calls will fail if not provided.")

def get_gitlab_client():
    token = os.environ.get("GITLAB_TOKEN")
    if not token:
        raise ValueError("GITLAB_TOKEN is required")
    url = os.environ.get("GITLAB_URL", "https://gitlab.com")
    return gitlab.Gitlab(url, private_token=token)

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_mcp_server_version",
            description="Get the version of the GitLab MCP server",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="create_issue",
            description="Create a new issue in a GitLab project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "The ID of the project"},
                    "title": {"type": "string", "description": "The title of the issue"},
                    "description": {"type": "string", "description": "The description of the issue"},
                    "labels": {"type": "string", "description": "Comma-separated list of labels"}
                },
                "required": ["project_id", "title"]
            }
        ),
        types.Tool(
            name="get_issue",
            description="Get details of a specific issue",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "The ID of the project"},
                    "issue_iid": {"type": "integer", "description": "The internal ID of the issue"}
                },
                "required": ["project_id", "issue_iid"]
            }
        ),
        types.Tool(
            name="create_merge_request",
            description="Create a new merge request",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "The ID of the project"},
                    "source_branch": {"type": "string", "description": "The source branch"},
                    "target_branch": {"type": "string", "description": "The target branch"},
                    "title": {"type": "string", "description": "The title of the merge request"},
                    "description": {"type": "string", "description": "The description of the merge request"}
                },
                "required": ["project_id", "source_branch", "target_branch", "title"]
            }
        ),
        types.Tool(
            name="get_merge_request",
            description="Get details of a merge request",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "The ID of the project"},
                    "mr_iid": {"type": "integer", "description": "The internal ID of the merge request"}
                },
                "required": ["project_id", "mr_iid"]
            }
        ),
        types.Tool(
            name="get_merge_request_commits",
            description="Get commits of a merge request",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "The ID of the project"},
                    "mr_iid": {"type": "integer", "description": "The internal ID of the merge request"}
                },
                "required": ["project_id", "mr_iid"]
            }
        ),
        types.Tool(
            name="get_merge_request_diffs",
            description="Get diffs of a merge request",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "The ID of the project"},
                    "mr_iid": {"type": "integer", "description": "The internal ID of the merge request"}
                },
                "required": ["project_id", "mr_iid"]
            }
        ),
        types.Tool(
            name="get_merge_request_pipelines",
            description="Get pipelines attached to a merge request",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "The ID of the project"},
                    "mr_iid": {"type": "integer", "description": "The internal ID of the merge request"}
                },
                "required": ["project_id", "mr_iid"]
            }
        ),
        types.Tool(
            name="get_pipeline_jobs",
            description="Get jobs of a pipeline",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "The ID of the project"},
                    "pipeline_id": {"type": "integer", "description": "The ID of the pipeline"}
                },
                "required": ["project_id", "pipeline_id"]
            }
        ),
        types.Tool(
            name="manage_pipeline",
            description="Retry or cancel a pipeline",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "The ID of the project"},
                    "pipeline_id": {"type": "integer", "description": "The ID of the pipeline"},
                    "action": {"type": "string", "enum": ["retry", "cancel"], "description": "Action to perform"}
                },
                "required": ["project_id", "pipeline_id", "action"]
            }
        ),
        types.Tool(
            name="create_merge_request_note",
            description="Create a note (comment) on a merge request",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "The ID of the project"},
                    "mr_iid": {"type": "integer", "description": "The internal ID of the merge request"},
                    "body": {"type": "string", "description": "The content of the note"}
                },
                "required": ["project_id", "mr_iid", "body"]
            }
        ),
        types.Tool(
            name="create_merge_request_discussion",
            description="Create a discussion (review comment) on a specific line of code in a merge request",
            inputSchema={
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
                    "new_line": {"type": "integer", "description": "The new line number (use null if deleted line)"},
                    "old_line": {"type": "integer", "description": "The old line number (use null if added line)"}
                },
                "required": ["project_id", "mr_iid", "body", "base_sha", "start_sha", "head_sha", "new_path", "old_path"]
            }
        ),
        types.Tool(
            name="create_workitem_note",
            description="Create a note (comment) on an issue or merge request",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "The ID of the project"},
                    "item_type": {"type": "string", "enum": ["issue", "merge_request"], "description": "Type of item"},
                    "item_iid": {"type": "integer", "description": "The internal ID of the issue or MR"},
                    "body": {"type": "string", "description": "The content of the note"}
                },
                "required": ["project_id", "item_type", "item_iid", "body"]
            }
        ),
        types.Tool(
            name="get_workitem_notes",
            description="Get notes (comments) of an issue or merge request",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "The ID of the project"},
                    "item_type": {"type": "string", "enum": ["issue", "merge_request"], "description": "Type of item"},
                    "item_iid": {"type": "integer", "description": "The internal ID of the issue or MR"}
                },
                "required": ["project_id", "item_type", "item_iid"]
            }
        ),
        types.Tool(
            name="search",
            description="Search in GitLab scope (projects)",
            inputSchema={
                "type": "object",
                "properties": {
                    "scope": {"type": "string", "enum": ["projects", "issues", "merge_requests"], "description": "Scope to search in"},
                    "query": {"type": "string", "description": "Search query text"}
                },
                "required": ["scope", "query"]
            }
        ),
        types.Tool(
            name="search_labels",
            description="Search labels in a project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "The ID of the project"},
                    "query": {"type": "string", "description": "Search query text"}
                },
                "required": ["project_id"]
            }
        ),
        types.Tool(
            name="semantic_code_search",
            description="Search code in a project using keywords",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "The ID of the project"},
                    "query": {"type": "string", "description": "The search query text"}
                },
                "required": ["project_id", "query"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    gl = get_gitlab_client()
    try:
        if name == "get_mcp_server_version":
            return [types.TextContent(type="text", text=f"GitLab MCP Server version {SERVER_VERSION}")]
        
        # Tools requiring project
        if "project_id" in arguments and name != "search":
            project = gl.projects.get(arguments["project_id"])

        if name == "create_issue":
            issue_data = {"title": arguments["title"]}
            if "description" in arguments:
                issue_data["description"] = arguments["description"]
            if "labels" in arguments:
                issue_data["labels"] = arguments["labels"]
            issue = project.issues.create(issue_data)
            return [types.TextContent(type="text", text=f"Created issue {issue.iid}: {issue.web_url}")]

        elif name == "get_issue":
            issue = project.issues.get(arguments["issue_iid"])
            return [types.TextContent(type="text", text=f"Issue {issue.iid}: {issue.title}\nState: {issue.state}\nURL: {issue.web_url}\n\n{issue.description}")]

        elif name == "create_merge_request":
            mr_data = {
                "source_branch": arguments["source_branch"],
                "target_branch": arguments["target_branch"],
                "title": arguments["title"]
            }
            if "description" in arguments:
                mr_data["description"] = arguments["description"]
            mr = project.mergerequests.create(mr_data)
            return [types.TextContent(type="text", text=f"Created merge request {mr.iid}: {mr.web_url}")]
        
        elif name == "get_merge_request":
            mr = project.mergerequests.get(arguments["mr_iid"])
            return [types.TextContent(type="text", text=f"MR {mr.iid}: {mr.title}\nState: {mr.state}\nURL: {mr.web_url}\n\n{mr.description}")]

        elif name == "get_merge_request_commits":
            mr = project.mergerequests.get(arguments["mr_iid"])
            commits = mr.commits()
            commits_text = "\n".join([f"- {c.short_id}: {c.title}" for c in commits])
            return [types.TextContent(type="text", text=commits_text if commits_text else "No commits found")]

        elif name == "get_merge_request_diffs":
            mr = project.mergerequests.get(arguments["mr_iid"])
            changes = mr.changes()
            diffs = []
            for change in changes.get('changes', []):
                diffs.append(f"File: {change.get('new_path')}\n{change.get('diff')}")
            return [types.TextContent(type="text", text="\n".join(diffs) if diffs else "No diffs found")]

        elif name == "get_merge_request_pipelines":
            mr = project.mergerequests.get(arguments["mr_iid"])
            pipelines = mr.pipelines()
            pipes_text = "\n".join([f"- Pipeline {p['id']} ({p['status']}): {p['web_url']}" for p in pipelines])
            return [types.TextContent(type="text", text=pipes_text if pipes_text else "No pipelines found")]

        elif name == "get_pipeline_jobs":
            pipeline = project.pipelines.get(arguments["pipeline_id"])
            jobs = pipeline.jobs.list()
            jobs_text = "\n".join([f"- Job {j.id} ({j.name}): {j.status}" for j in jobs])
            return [types.TextContent(type="text", text=jobs_text if jobs_text else "No jobs found")]

        elif name == "manage_pipeline":
            pipeline = project.pipelines.get(arguments["pipeline_id"])
            if arguments["action"] == "retry":
                pipeline.retry()
                return [types.TextContent(type="text", text=f"Retried pipeline {pipeline.id}")]
            elif arguments["action"] == "cancel":
                pipeline.cancel()
                return [types.TextContent(type="text", text=f"Canceled pipeline {pipeline.id}")]

        elif name == "create_merge_request_note":
            body = arguments["body"]
            mr = project.mergerequests.get(arguments["mr_iid"])
            note = mr.notes.create({'body': body})
            return [types.TextContent(type="text", text=f"Created note with ID {note.id} on merge request {mr.iid}")]

        elif name == "create_merge_request_discussion":
            mr = project.mergerequests.get(arguments["mr_iid"])
            discussion_data = {
                'body': arguments["body"],
                'position': {
                    'position_type': 'text',
                    'base_sha': arguments["base_sha"],
                    'start_sha': arguments["start_sha"],
                    'head_sha': arguments["head_sha"],
                    'new_path': arguments["new_path"],
                    'old_path': arguments["old_path"]
                }
            }
            if arguments.get("new_line"):
                discussion_data['position']['new_line'] = arguments["new_line"]
            if arguments.get("old_line"):
                discussion_data['position']['old_line'] = arguments["old_line"]
                
            discussion = mr.discussions.create(discussion_data)
            return [types.TextContent(type="text", text=f"Created discussion with ID {discussion.id} on merge request {mr.iid}")]

        elif name == "create_workitem_note":
            body = arguments["body"]
            if arguments["item_type"] == "issue":
                item = project.issues.get(arguments["item_iid"])
            else:
                item = project.mergerequests.get(arguments["item_iid"])
            note = item.notes.create({'body': body})
            return [types.TextContent(type="text", text=f"Created note with ID {note.id}")]

        elif name == "get_workitem_notes":
            if arguments["item_type"] == "issue":
                item = project.issues.get(arguments["item_iid"])
            else:
                item = project.mergerequests.get(arguments["item_iid"])
            notes = item.notes.list(get_all=False)
            notes_text = "\n\n".join([f"Note {n.id} by {n.author['username']}:\n{n.body}" for n in notes])
            return [types.TextContent(type="text", text=notes_text if notes_text else "No notes found")]

        elif name == "search":
            scope = arguments["scope"]
            query = arguments["query"]
            results = gl.search(scope, query)
            if not results:
                return [types.TextContent(type="text", text=f"No results found in {scope} for '{query}'")]
            
            res_texts = []
            for r in results[:10]: # Limit to 10
                if scope == "projects":
                    res_texts.append(f"- Project {r['id']}: {r['name_with_namespace']} ({r['web_url']})")
                elif scope == "issues":
                    res_texts.append(f"- Issue {r.get('iid')} in project {r.get('project_id')}: {r.get('title')}")
                elif scope == "merge_requests":
                    res_texts.append(f"- MR {r.get('iid')} in project {r.get('project_id')}: {r.get('title')}")
            return [types.TextContent(type="text", text="\n".join(res_texts))]

        elif name == "search_labels":
            query = arguments.get("query", "")
            labels = project.labels.list(search=query if query else None)
            labels_text = "\n".join([f"- {l.name} ({l.color}): {l.description or 'No desc'}" for l in labels])
            return [types.TextContent(type="text", text=labels_text if labels_text else "No labels found")]

        elif name == "semantic_code_search":
            query = arguments["query"]
            results = project.search("blobs", query)
            res_texts = []
            for r in results[:10]:
                res_texts.append(f"File: {r['path']}\n```{r.get('data', 'No content snippet (code search returned meta)')}```")
            return [types.TextContent(type="text", text="\n---\n".join(res_texts) if res_texts else "No code search results found")]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Error executing {name}: {str(e)}")
        return [types.TextContent(type="text", text=f"Error executing {name}: {str(e)}")]

async def main():
    logger.info("Starting GitLab MCP server")
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
