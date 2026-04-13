# Kitsu MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server that connects AI assistants like Claude to [Kitsu](https://www.cg-wire.com/kitsu) — the open-source production management tool for animation, VFX, and game studios.

Built with [FastMCP](https://github.com/jlowin/fastmcp) and the [Gazu](https://gazu.cg-wire.com/) Python client.

## Features

**95 tools** covering the full Kitsu production pipeline:

| Category | Tools |
|----------|-------|
| **Projects** | List, overview, stats, create, close, add/remove task types |
| **Assets** | List, details, create, update, delete, **update custom data**, asset types, CSV import/export |
| **Shots & Sequences** | List, details, create, update, delete, **update custom data**, batch create, CSV import/export, OTIO import |
| **Tasks** | List, details, create, batch create, assign, unassign, **start task**, **submit for review**, **update custom data**, update status, set estimates, delete |
| **Time Tracking** | Add, set, get time spent, **get time spent range** |
| **Comments** | Add comments, **reply to comment**, **acknowledge comment**, list comment history |
| **Previews** | Upload, publish, set main, **list per task**, **get URLs**, **download**, **update annotations** |
| **Attachments** | **List attachment files per task** |
| **Casting** | Get/set shot casting, get asset casting |
| **Team & People** | List team, update roles, add/remove members, person tasks, create person, invite, departments |
| **Playlists** | List, create, add entities, **remove entities**, build movie |
| **Budgets** | List, create budgets and budget entries |
| **Concepts** | List, create concepts |
| **Edits** | List, create, details, update, delete, list previews |
| **Scenes** | List, create scenes |
| **Metadata** | List and add custom metadata descriptors |
| **Notifications** | List, **mark all as read**, **subscribe/unsubscribe from tasks** |
| **Other** | Search, task statuses, daily progress report |

### Edit / Montage Review Workflow

Edits are full-length montages or sequences (like animatics, trailers, or final cuts) — the Kitsu equivalent of Frame.io's file-based review. Upload a complete video with audio and review it with annotations, comments, and version tracking.

```
1. create_edit("My Project", "Trailer_v03")
2. create_task("My Project", "Trailer_v03", "Edit", entity_type="edit")
3. upload_preview(task_id, "/path/to/trailer_v03.mp4", comment="v3 with music")
```

The team can then review the full montage in Kitsu's player with drawing/annotation tools and timecoded comments.

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

Add to your Claude Code MCP config (`~/.claude/mcp.json` or project-level `.mcp.json`):

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
- "Remove anna@studio.com from the modeling task on Capsule"
- "Add 4 hours of work on this task for today"
- "Export all shots to CSV"
- "Create a new playlist and add all shots from SQ01"
- "Create an edit called Trailer_v01 and upload the montage for review"
- "Show me the details and previews for edit Animatic_v2"

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
- `list_tasks_for_entity` — Tasks for a specific asset, shot, or edit
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
- `list_preview_files_for_task` — All preview files for a task
- `list_attachment_files_for_task` — All attachment files for a task
- `get_preview_file_url` — Direct image/video URLs for a preview
- `get_time_spents_range` — Time spent by person over a date range
- `search` — Search entities by name
- `daily_progress_report` — Activity summary for last N hours
- `list_concepts` — Concepts in a project
- `list_edits` — Edits in a project
- `get_edit_details` — Edit details with tasks and previews
- `list_previews_for_edit` — All preview files for an edit
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
- `create_task` — Create a task for an asset, shot, or edit
- `create_person` — Create a new user
- `invite_person` — Send invitation email to a user
- `create_department` — Create a department
- `create_playlist` — Create a playlist
- `create_budget` — Create a budget
- `create_budget_entry` — Create a budget entry
- `create_concept` — Create a concept
- `create_edit` — Create an edit (montage/sequence for review)
- `create_scene` — Create a scene
- `add_metadata_descriptor` — Add a custom metadata field

### Update
- `update_task_status` — Change task status with optional comment
- `assign_task` — Assign a person to a task
- `unassign_task` — Remove a person from a task (or clear all assignees)
- `set_task_estimate` — Set time estimate for a task
- `add_comment` — Add a comment to a task
- `set_shot_casting` — Set which assets appear in a shot
- `update_asset` — Update asset description/metadata
- `update_shot` — Update shot description/frames/metadata
- `update_edit` — Update edit name/description
- `update_team_member_role` — Change a team member's role
- `add_time_spent` — Add time spent on a task
- `set_time_spent` — Set time spent on a task
- `add_person_to_department` — Add person to department
- `remove_person_from_department` — Remove person from department
- `add_entity_to_playlist` — Add shot/asset to playlist
- `add_team_member` — Add a person to a project team
- `set_main_preview` — Set a preview as the main thumbnail
- `start_task` — Start a task (set to WIP)
- `submit_for_review` — Submit task for supervisor review (WFA)
- `reply_to_comment` — Threaded reply to a comment
- `acknowledge_comment` — Mark a comment as acknowledged
- `update_asset_data` — Update custom metadata on an asset
- `update_shot_data` — Update custom metadata on a shot
- `update_task_data` — Update custom metadata on a task
- `update_preview_annotations` — Add/edit/remove annotations on a preview
- `mark_all_notifications_as_read` — Clear all notifications
- `subscribe_to_task` — Subscribe to task notifications
- `unsubscribe_from_task` — Unsubscribe from task notifications
- `remove_entity_from_playlist` — Remove entity from a playlist
- `add_task_type_to_project` — Add a task type to a project
- `remove_task_type_from_project` — Remove a task type from a project

### Batch
- `batch_create_shots` — Create multiple shots at once (e.g. SH010-SH200)
- `batch_create_tasks` — Add a task type to all shots/assets in a group

### Preview
- `upload_preview` — Upload a preview file to a task
- `publish_preview` — Status + comment + preview in one step
- `download_preview_file` — Download a preview file to local path

### Import/Export
- `import_assets_csv` — Import assets from CSV
- `import_shots_csv` — Import shots from CSV
- `import_otio` — Import timeline from OpenTimelineIO

### Dangerous (require confirm=True)
- `delete_shot` — Delete a shot
- `delete_asset` — Delete an asset
- `delete_task` — Delete a task
- `delete_edit` — Delete an edit
- `close_project` — Close/archive a project
- `build_playlist_movie` — Build a movie from playlist

## Changelog

### v0.4.0 (2026-04-13)
- **Task workflow**: `start_task` (WIP), `submit_for_review` (WFA), `reply_to_comment`, `acknowledge_comment`
- **Custom data**: `update_asset_data`, `update_shot_data`, `update_task_data` — set custom metadata dicts
- **Preview files**: `get_preview_file_url`, `download_preview_file`, `update_preview_annotations`, `list_preview_files_for_task`
- **Attachments**: `list_attachment_files_for_task`
- **Schedule**: `get_time_spents_range` — query time entries over date ranges
- **Notifications**: `mark_all_notifications_as_read`, `subscribe_to_task`, `unsubscribe_from_task`
- **Playlist**: `remove_entity_from_playlist`
- **Project**: `add_task_type_to_project`, `remove_task_type_from_project`

### v0.3.0 (2026-04-12)
- **Edit entity support**: Full CRUD for Edits — create tasks on edits, get details with previews, update, delete
- **Unassign task**: Remove specific people or clear all assignees from a task
- **Edit review workflow**: Upload full montages/animatics for team review with annotations (Frame.io-like)

### v0.2.0
- Team management: add/remove members, update roles, invite users
- Departments: create, add/remove people
- Metadata descriptors
- Budget management
- Concepts, scenes, edits (basic create/list)

### v0.1.0
- Initial release with 60+ tools covering projects, assets, shots, tasks, previews, playlists

## License

MIT License — see [LICENSE](LICENSE).

## Credits

- [Kitsu](https://www.cg-wire.com/kitsu) by CGWire
- [Gazu](https://gazu.cg-wire.com/) Python client by CGWire
- [MCP](https://modelcontextprotocol.io/) by Anthropic
