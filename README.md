# Kitsu MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server that connects AI assistants like Claude to [Kitsu](https://www.cg-wire.com/kitsu) — the open-source production management tool for animation, VFX, and game studios.

Built with [FastMCP](https://github.com/jlowin/fastmcp) and the [Gazu](https://gazu.cg-wire.com/) Python client.

## Features

**30 tools** covering the full Kitsu production pipeline:

| Category | Tools |
|----------|-------|
| **Projects** | List projects, get overview, create project |
| **Assets** | List, get details, create assets & asset types |
| **Shots & Sequences** | List, get details, create episodes, sequences, shots |
| **Tasks** | List, get details, create, assign, update status, set estimates |
| **Comments** | Add comments, list comment history |
| **Casting** | Get and set shot casting (asset breakdown) |
| **Team** | List team members, get person's tasks |
| **Other** | Search, playlists, notifications, task statuses |

## Requirements

- Python 3.10+
- A running [Kitsu](https://www.cg-wire.com/kitsu) instance (self-hosted or cloud)
- A Kitsu user account with appropriate permissions

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/kitsu-mcp-server.git
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
- "Create a new project called 'Commercial X'"
- "Show me all shots in sequence SQ01"
- "Create 5 shots (SH010-SH050) in sequence SQ01"
- "Assign the lighting task on SH020 to anna@studio.com"
- "What tasks are assigned to me?"
- "Set the status of this task to Work In Progress"
- "Add a comment to the animation task on SH030"

## Available tools

### Read
- `list_projects` — List all open projects
- `get_project_overview` — Project overview with team, task types, asset types
- `list_assets` — List assets (optionally filtered by type)
- `get_asset_details` — Asset details with tasks
- `list_sequences` — List sequences
- `list_shots` — List shots (optionally filtered by sequence)
- `get_shot_details` — Shot details with tasks and casting
- `list_my_tasks` — Tasks assigned to logged-in user
- `list_tasks_for_entity` — Tasks for a specific asset or shot
- `get_task_details` — Task details with comment history
- `list_comments` — Comments on a task
- `get_shot_casting` — Asset breakdown for a shot
- `list_team_members` — Team members in a project
- `get_person_tasks` — Tasks for a specific person
- `list_playlists` — Playlists in a project
- `list_task_statuses` — Available task statuses
- `list_notifications` — Recent notifications
- `search` — Search entities by name

### Create
- `create_project` — Create a new project
- `create_asset_type` — Create an asset type
- `create_asset` — Create an asset
- `create_episode` — Create an episode
- `create_sequence` — Create a sequence
- `create_shot` — Create a shot
- `create_task` — Create a task with optional assignees

### Update
- `update_task_status` — Change task status with optional comment
- `assign_task` — Assign a person to a task
- `set_task_estimate` — Set time estimate for a task
- `add_comment` — Add a comment to a task
- `set_shot_casting` — Set which assets appear in a shot

## License

MIT License — see [LICENSE](LICENSE).

## Credits

- [Kitsu](https://www.cg-wire.com/kitsu) by CGWire
- [Gazu](https://gazu.cg-wire.com/) Python client by CGWire
- [MCP](https://modelcontextprotocol.io/) by Anthropic
