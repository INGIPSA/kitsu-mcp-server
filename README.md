# Kitsu MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server that connects AI assistants like Claude to [Kitsu](https://www.cg-wire.com/kitsu) — the open-source production management tool for animation, VFX, and game studios.

Built with [FastMCP](https://github.com/jlowin/fastmcp) and the [Gazu](https://gazu.cg-wire.com/) Python client.

## Features

**71 tools** covering the full Kitsu production pipeline:

| Category | Tools |
|----------|-------|
| **Projects** | List, overview, stats, create, close |
| **Assets** | List, details, create, update, delete, asset types, CSV import/export |
| **Shots & Sequences** | List, details, create, update, delete, batch create, CSV import/export, OTIO import |
| **Tasks** | List, details, create, batch create, assign, update status, set estimates, delete |
| **Time Tracking** | Add, set, get time spent |
| **Comments** | Add comments, list comment history |
| **Previews** | Upload preview, publish preview (status + comment + file in one) |
| **Casting** | Get/set shot casting, get asset casting |
| **Team & People** | List team, person tasks, create person, departments |
| **Playlists** | List, create, add entities, build movie |
| **Budgets** | List, create budgets and budget entries |
| **Concepts** | List, create concepts |
| **Edits** | List, create edits |
| **Scenes** | List, create scenes |
| **Metadata** | List and add custom metadata descriptors |
| **Other** | Search, notifications, task statuses, daily progress report |

## Requirements

- Python 3.10+
- A running [Kitsu](https://www.cg-wire.com/kitsu) instance (self-hosted or cloud)
- A Kitsu user account with appropriate permissions

## Installation

```bash
git clone https://github.com/INGIPSA/kitsu-mcp-server.git
cd kitsu-mcp-server
pip install -r requirements.txt
```

## Configuration

The server requires three environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `KITSU_HOST` | Your Kitsu API URL | `https://kitsu.yourstudio.com/api` |
| `KITSU_USER` | Login email | `artist@yourstudio.com` |
| `KITSU_PASSWORD` | Login password | `your-password` |

## Usage

### With Claude Code

Add to your Claude Code MCP config (`~/.claude/claude_desktop_config.json` or project-level `.mcp.json`):

```json
{
  "mcpServers": {
    "kitsu": {
      "command": "python",
      "args": ["path/to/kitsu-mcp-server/server.py"],
      "env": {
        "KITSU_HOST": "https://kitsu.yourstudio.com/api",
        "KITSU_USER": "your-email@example.com",
        "KITSU_PASSWORD": "your-password"
      }
    }
  }
}
```

### With Claude Desktop

Add the same config block to Claude Desktop's settings under MCP servers.

### Standalone

```bash
export KITSU_HOST="https://kitsu.yourstudio.com/api"
export KITSU_USER="your-email@example.com"
export KITSU_PASSWORD="your-password"

python server.py
```

## Example prompts

Once connected, you can ask your AI assistant things like:

- "List all open projects in Kitsu"
- "Create shots SH010 through SH200 in sequence SQ01"
- "Upload this render as a preview for the lighting task on SH020"
- "What happened in the project in the last 24 hours?"
- "Assign the animation task on SH030 to anna@studio.com"
- "Add 4 hours of work on this task for today"
- "Export all shots to CSV"
- "Create a new playlist and add all shots from SQ01"
- "What are the budget entries for this project?"

## Available tools

### Read
- `list_projects` — List all open projects
- `get_project_overview` — Project overview with team, task types, asset types
- `get_project_stats` — Task statistics grouped by status
- `list_assets` — List assets (optionally filtered by type)
- `get_asset_details` — Asset details with tasks
- `list_sequences` — List sequences
- `list_shots` — List shots (optionally filtered by sequence)
- `get_shot_details` — Shot details with tasks and casting
- `list_my_tasks` — Tasks assigned to logged-in user
- `list_tasks_for_entity` — Tasks for a specific asset or shot
- `get_task_details` — Task details with comment history
- `get_time_spent` — Time entries for a task
- `list_comments` — Comments on a task
- `get_shot_casting` — Asset breakdown for a shot
- `get_asset_casting` — Shots an asset appears in
- `list_team_members` — Team members in a project
- `get_person_tasks` — Tasks for a specific person
- `list_departments` — All departments
- `list_playlists` — Playlists in a project
- `list_task_statuses` — Available task statuses
- `list_notifications` — Recent notifications
- `search` — Search entities by name
- `daily_progress_report` — Activity summary for last N hours
- `list_concepts` — Concepts in a project
- `list_edits` — Edits in a project
- `list_scenes` — Scenes in a project
- `list_metadata_descriptors` — Custom metadata fields
- `get_budgets` — Budgets for a project
- `get_budget_entries` — Entries in a budget
- `export_assets_csv` — Export assets to CSV
- `export_shots_csv` — Export shots to CSV

### Create
- `create_project` — Create a new project
- `create_asset_type` — Create an asset type
- `create_asset` — Create an asset
- `create_episode` — Create an episode
- `create_sequence` — Create a sequence
- `create_shot` — Create a shot
- `create_task` — Create a task with optional assignees
- `create_person` — Create a new user
- `create_department` — Create a department
- `create_playlist` — Create a playlist
- `create_budget` — Create a budget
- `create_budget_entry` — Create a budget entry
- `create_concept` — Create a concept
- `create_edit` — Create an edit
- `create_scene` — Create a scene
- `add_metadata_descriptor` — Add a custom metadata field

### Update
- `update_task_status` — Change task status with optional comment
- `assign_task` — Assign a person to a task
- `set_task_estimate` — Set time estimate for a task
- `add_comment` — Add a comment to a task
- `set_shot_casting` — Set which assets appear in a shot
- `update_asset` — Update asset description/metadata
- `update_shot` — Update shot description/frames/metadata
- `add_time_spent` — Add time spent on a task
- `set_time_spent` — Set time spent on a task
- `add_person_to_department` — Add person to department
- `remove_person_from_department` — Remove person from department
- `add_entity_to_playlist` — Add shot/asset to playlist

### Batch
- `batch_create_shots` — Create multiple shots at once (e.g. SH010-SH200)
- `batch_create_tasks` — Add a task type to all shots/assets in a group

### Preview
- `upload_preview` — Upload a preview file to a task
- `publish_preview` — Status + comment + preview in one step

### Import/Export
- `import_assets_csv` — Import assets from CSV
- `import_shots_csv` — Import shots from CSV
- `import_otio` — Import timeline from OpenTimelineIO

### Dangerous (require confirm=True)
- `delete_shot` — Delete a shot
- `delete_asset` — Delete an asset
- `delete_task` — Delete a task
- `close_project` — Close/archive a project
- `build_playlist_movie` — Build a movie from playlist

## License

MIT License — see [LICENSE](LICENSE).

## Credits

- [Kitsu](https://www.cg-wire.com/kitsu) by CGWire
- [Gazu](https://gazu.cg-wire.com/) Python client by CGWire
- [MCP](https://modelcontextprotocol.io/) by Anthropic
