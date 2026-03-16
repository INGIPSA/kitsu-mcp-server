"""
Kitsu MCP Server
Connects Claude (or any MCP client) to Kitsu production management via the Gazu API.
"""

import os
import json
import logging
from contextlib import asynccontextmanager

import gazu
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, stream=__import__("sys").stderr)
logger = logging.getLogger("kitsu-mcp")

# --- Lifespan: authenticate on startup, logout on shutdown ---


@asynccontextmanager
async def kitsu_lifespan(server: FastMCP):
    host = os.environ.get("KITSU_HOST", "https://kitsu.tatostudio.pl/api")
    email = os.environ.get("KITSU_USER", "")
    password = os.environ.get("KITSU_PASSWORD", "")

    gazu.set_host(host)

    if email and password:
        try:
            result = gazu.log_in(email, password)
            logger.info(f"Logged in to Kitsu as {result['user']['full_name']}")
        except Exception as e:
            logger.error(f"Failed to log in to Kitsu: {e}")
            raise
    else:
        raise RuntimeError(
            "KITSU_USER and KITSU_PASSWORD environment variables are required"
        )

    try:
        yield {}
    finally:
        try:
            gazu.log_out()
        except Exception:
            pass


mcp = FastMCP(
    "kitsu",
    instructions="Kitsu production management — manage projects, assets, shots, tasks, and team via the Kitsu/Zou API.",
    lifespan=kitsu_lifespan,
)

# ============================================================
# Helper
# ============================================================


def _slim_entity(entity, keys=None):
    """Return a smaller dict with only the most useful keys."""
    if entity is None:
        return None
    if keys is None:
        keys = [
            "id",
            "name",
            "full_name",
            "description",
            "code",
            "email",
            "role",
            "active",
            "status",
            "task_status_name",
            "task_type_name",
            "priority",
            "estimation",
            "duration",
            "start_date",
            "due_date",
            "real_start_date",
            "end_date",
            "last_comment_date",
            "nb_frames",
            "fps",
            "frame_in",
            "frame_out",
            "project_name",
            "entity_name",
            "entity_type_name",
            "assignees",
            "type",
            "data",
        ]
    return {k: v for k, v in entity.items() if k in keys and v is not None}


def _slim_list(entities, keys=None):
    return [_slim_entity(e, keys) for e in entities]


# ============================================================
# PROJECTS
# ============================================================


@mcp.tool()
def list_projects() -> list[dict]:
    """List all open productions/projects in Kitsu."""
    projects = gazu.project.all_open_projects()
    return _slim_list(projects)


@mcp.tool()
def get_project_overview(project_name: str) -> dict:
    """Get an overview of a project: team, task types, asset types, and task status summary.

    Args:
        project_name: The name of the project
    """
    project = gazu.project.get_project_by_name(project_name)
    if not project:
        return {"error": f"Project '{project_name}' not found"}

    team = gazu.project.get_team(project)
    task_types = gazu.task.all_task_types_for_project(project)
    asset_types = gazu.asset.all_asset_types_for_project(project)

    return {
        "project": _slim_entity(project),
        "team_size": len(team),
        "team": _slim_list(team, ["id", "full_name", "email", "role", "active"]),
        "task_types": _slim_list(task_types, ["id", "name", "color", "priority"]),
        "asset_types": _slim_list(asset_types, ["id", "name"]),
    }


# ============================================================
# ASSETS
# ============================================================


@mcp.tool()
def list_assets(project_name: str, asset_type_name: str | None = None) -> list[dict]:
    """List assets in a project, optionally filtered by asset type.

    Args:
        project_name: The name of the project
        asset_type_name: Optional asset type filter (e.g. 'Character', 'Prop', 'Environment')
    """
    project = gazu.project.get_project_by_name(project_name)
    if not project:
        return [{"error": f"Project '{project_name}' not found"}]

    assets = gazu.asset.all_assets_for_project(project)

    if asset_type_name:
        asset_type = gazu.asset.get_asset_type_by_name(asset_type_name)
        if asset_type:
            assets = [a for a in assets if a.get("asset_type_id") == asset_type["id"]]

    return _slim_list(assets)


@mcp.tool()
def get_asset_details(project_name: str, asset_name: str) -> dict:
    """Get full details of an asset including its tasks and statuses.

    Args:
        project_name: The name of the project
        asset_name: The name of the asset
    """
    project = gazu.project.get_project_by_name(project_name)
    if not project:
        return {"error": f"Project '{project_name}' not found"}

    asset = gazu.asset.get_asset_by_name(project, asset_name)
    if not asset:
        return {"error": f"Asset '{asset_name}' not found"}

    tasks = gazu.task.all_tasks_for_asset(asset)
    task_list = []
    for t in tasks:
        task_info = _slim_entity(t)
        task_info["assignees_names"] = [
            gazu.person.get_person(pid).get("full_name", "")
            for pid in (t.get("assignees") or [])
        ]
        task_list.append(task_info)

    return {
        "asset": _slim_entity(asset),
        "tasks": task_list,
    }


# ============================================================
# SHOTS & SEQUENCES
# ============================================================


@mcp.tool()
def list_sequences(project_name: str) -> list[dict]:
    """List all sequences in a project.

    Args:
        project_name: The name of the project
    """
    project = gazu.project.get_project_by_name(project_name)
    if not project:
        return [{"error": f"Project '{project_name}' not found"}]

    sequences = gazu.shot.all_sequences_for_project(project)
    return _slim_list(sequences)


@mcp.tool()
def list_shots(
    project_name: str, sequence_name: str | None = None
) -> list[dict]:
    """List shots in a project, optionally filtered by sequence.

    Args:
        project_name: The name of the project
        sequence_name: Optional sequence name to filter by
    """
    project = gazu.project.get_project_by_name(project_name)
    if not project:
        return [{"error": f"Project '{project_name}' not found"}]

    if sequence_name:
        sequence = gazu.shot.get_sequence_by_name(project, sequence_name)
        if not sequence:
            return [{"error": f"Sequence '{sequence_name}' not found"}]
        shots = gazu.shot.all_shots_for_sequence(sequence)
    else:
        shots = gazu.shot.all_shots_for_project(project)

    return _slim_list(shots)


@mcp.tool()
def get_shot_details(project_name: str, sequence_name: str, shot_name: str) -> dict:
    """Get full details of a shot including tasks, casting, and breakdown.

    Args:
        project_name: The name of the project
        sequence_name: The name of the sequence
        shot_name: The name of the shot
    """
    project = gazu.project.get_project_by_name(project_name)
    if not project:
        return {"error": f"Project '{project_name}' not found"}

    sequence = gazu.shot.get_sequence_by_name(project, sequence_name)
    if not sequence:
        return {"error": f"Sequence '{sequence_name}' not found"}

    shot = gazu.shot.get_shot_by_name(sequence, shot_name)
    if not shot:
        return {"error": f"Shot '{shot_name}' not found"}

    tasks = gazu.task.all_tasks_for_shot(shot)
    casting = gazu.casting.get_shot_casting(shot)

    return {
        "shot": _slim_entity(shot),
        "tasks": _slim_list(tasks),
        "casting": [
            {
                "asset_name": c.get("asset_name"),
                "asset_type_name": c.get("asset_type_name"),
                "nb_occurences": c.get("nb_occurences"),
            }
            for c in casting
        ],
    }


# ============================================================
# TASKS
# ============================================================


@mcp.tool()
def list_my_tasks(project_name: str | None = None) -> list[dict]:
    """List tasks assigned to the logged-in user, optionally filtered by project.

    Args:
        project_name: Optional project name to filter by
    """
    tasks = gazu.user.all_tasks_to_do()
    if project_name:
        project = gazu.project.get_project_by_name(project_name)
        if project:
            tasks = [t for t in tasks if t.get("project_id") == project["id"]]
    return _slim_list(tasks)


@mcp.tool()
def list_tasks_for_entity(
    project_name: str, entity_name: str, entity_type: str = "asset"
) -> list[dict]:
    """List all tasks for a specific asset or shot.

    Args:
        project_name: The name of the project
        entity_name: The name of the asset or shot
        entity_type: Either 'asset' or 'shot'
    """
    project = gazu.project.get_project_by_name(project_name)
    if not project:
        return [{"error": f"Project '{project_name}' not found"}]

    if entity_type == "shot":
        # Try finding shot across all sequences
        sequences = gazu.shot.all_sequences_for_project(project)
        entity = None
        for seq in sequences:
            entity = gazu.shot.get_shot_by_name(seq, entity_name)
            if entity:
                break
        if not entity:
            return [{"error": f"Shot '{entity_name}' not found"}]
        tasks = gazu.task.all_tasks_for_shot(entity)
    else:
        entity = gazu.asset.get_asset_by_name(project, entity_name)
        if not entity:
            return [{"error": f"Asset '{entity_name}' not found"}]
        tasks = gazu.task.all_tasks_for_asset(entity)

    return _slim_list(tasks)


@mcp.tool()
def get_task_details(task_id: str) -> dict:
    """Get detailed information about a task including comments history.

    Args:
        task_id: The UUID of the task
    """
    task = gazu.task.get_task(task_id)
    if not task:
        return {"error": f"Task '{task_id}' not found"}

    comments = gazu.task.all_comments_for_task(task)
    comment_list = [
        {
            "author": c.get("person", {}).get("full_name", "Unknown"),
            "text": c.get("text", ""),
            "task_status_name": c.get("task_status", {}).get("name", ""),
            "created_at": c.get("created_at", ""),
        }
        for c in comments[:20]
    ]

    return {
        "task": _slim_entity(task),
        "comments": comment_list,
    }


@mcp.tool()
def update_task_status(
    task_id: str, status_name: str, comment: str = ""
) -> dict:
    """Change the status of a task and optionally add a comment.

    Args:
        task_id: The UUID of the task
        status_name: New status name (e.g. 'wip', 'wfa', 'retake', 'done', 'ready')
        comment: Optional comment text
    """
    task = gazu.task.get_task(task_id)
    if not task:
        return {"error": f"Task '{task_id}' not found"}

    status = gazu.task.get_task_status_by_short_name(status_name.lower())
    if not status:
        # Try full name
        status = gazu.task.get_task_status_by_name(status_name)
    if not status:
        all_statuses = gazu.task.all_task_statuses()
        return {
            "error": f"Status '{status_name}' not found",
            "available_statuses": [
                {"name": s["name"], "short_name": s.get("short_name")}
                for s in all_statuses
            ],
        }

    result = gazu.task.add_comment(task, status, comment=comment)
    return {
        "success": True,
        "task_id": task_id,
        "new_status": status_name,
        "comment_id": result.get("id"),
    }


@mcp.tool()
def assign_task(task_id: str, person_email: str) -> dict:
    """Assign a person to a task.

    Args:
        task_id: The UUID of the task
        person_email: Email address of the person to assign
    """
    task = gazu.task.get_task(task_id)
    if not task:
        return {"error": f"Task '{task_id}' not found"}

    person = gazu.person.get_person_by_email(person_email)
    if not person:
        return {"error": f"Person with email '{person_email}' not found"}

    gazu.task.assign_task(task, person)
    return {
        "success": True,
        "task_id": task_id,
        "assigned_to": person["full_name"],
    }


@mcp.tool()
def set_task_estimate(task_id: str, days: float) -> dict:
    """Set the time estimate for a task in days.

    Args:
        task_id: The UUID of the task
        days: Estimated duration in days
    """
    task = gazu.task.get_task(task_id)
    if not task:
        return {"error": f"Task '{task_id}' not found"}

    gazu.task.update_task(task, {"estimation": days})
    return {"success": True, "task_id": task_id, "estimation_days": days}


# ============================================================
# COMMENTS
# ============================================================


@mcp.tool()
def add_comment(task_id: str, text: str, status_name: str | None = None) -> dict:
    """Add a comment to a task, optionally changing its status.

    Args:
        task_id: The UUID of the task
        text: Comment text
        status_name: Optional new status (e.g. 'wip', 'wfa', 'retake')
    """
    task = gazu.task.get_task(task_id)
    if not task:
        return {"error": f"Task '{task_id}' not found"}

    if status_name:
        status = gazu.task.get_task_status_by_short_name(status_name.lower())
        if not status:
            status = gazu.task.get_task_status_by_name(status_name)
    else:
        # Keep current status
        status = gazu.task.get_task_status(task["task_status_id"])

    result = gazu.task.add_comment(task, status, comment=text)
    return {"success": True, "comment_id": result.get("id")}


@mcp.tool()
def list_comments(task_id: str) -> list[dict]:
    """List all comments for a task.

    Args:
        task_id: The UUID of the task
    """
    task = gazu.task.get_task(task_id)
    if not task:
        return [{"error": f"Task '{task_id}' not found"}]

    comments = gazu.task.all_comments_for_task(task)
    return [
        {
            "author": c.get("person", {}).get("full_name", "Unknown"),
            "text": c.get("text", ""),
            "status": c.get("task_status", {}).get("name", ""),
            "created_at": c.get("created_at", ""),
        }
        for c in comments
    ]


# ============================================================
# CASTING / BREAKDOWN
# ============================================================


@mcp.tool()
def get_shot_casting(
    project_name: str, sequence_name: str, shot_name: str
) -> list[dict]:
    """Get the asset breakdown/casting for a shot.

    Args:
        project_name: The name of the project
        sequence_name: The name of the sequence
        shot_name: The name of the shot
    """
    project = gazu.project.get_project_by_name(project_name)
    if not project:
        return [{"error": f"Project '{project_name}' not found"}]

    sequence = gazu.shot.get_sequence_by_name(project, sequence_name)
    if not sequence:
        return [{"error": f"Sequence '{sequence_name}' not found"}]

    shot = gazu.shot.get_shot_by_name(sequence, shot_name)
    if not shot:
        return [{"error": f"Shot '{shot_name}' not found"}]

    casting = gazu.casting.get_shot_casting(shot)
    return [
        {
            "asset_name": c.get("asset_name"),
            "asset_type_name": c.get("asset_type_name"),
            "nb_occurences": c.get("nb_occurences"),
        }
        for c in casting
    ]


# ============================================================
# PEOPLE & TEAM
# ============================================================


@mcp.tool()
def list_team_members(project_name: str) -> list[dict]:
    """List all team members in a project.

    Args:
        project_name: The name of the project
    """
    project = gazu.project.get_project_by_name(project_name)
    if not project:
        return [{"error": f"Project '{project_name}' not found"}]

    team = gazu.project.get_team(project)
    return _slim_list(team, ["id", "full_name", "email", "role", "active"])


@mcp.tool()
def get_person_tasks(person_email: str, project_name: str | None = None) -> list[dict]:
    """Get all tasks assigned to a specific person.

    Args:
        person_email: Email address of the person
        project_name: Optional project name to filter by
    """
    person = gazu.person.get_person_by_email(person_email)
    if not person:
        return [{"error": f"Person '{person_email}' not found"}]

    tasks = gazu.task.all_tasks_for_person(person)

    if project_name:
        project = gazu.project.get_project_by_name(project_name)
        if project:
            tasks = [t for t in tasks if t.get("project_id") == project["id"]]

    return _slim_list(tasks)


# ============================================================
# PLAYLISTS
# ============================================================


@mcp.tool()
def list_playlists(project_name: str) -> list[dict]:
    """List all playlists in a project.

    Args:
        project_name: The name of the project
    """
    project = gazu.project.get_project_by_name(project_name)
    if not project:
        return [{"error": f"Project '{project_name}' not found"}]

    playlists = gazu.playlist.all_playlists_for_project(project)
    return _slim_list(playlists, ["id", "name", "created_at", "updated_at"])


# ============================================================
# SEARCH
# ============================================================


@mcp.tool()
def search(query: str, project_name: str | None = None) -> list[dict]:
    """Search for assets, shots, or other entities by name.

    Args:
        query: Search term
        project_name: Optional project name to scope the search
    """
    project = None
    if project_name:
        project = gazu.project.get_project_by_name(project_name)

    results = gazu.search.search_entities(query, project=project)
    return _slim_list(results)


# ============================================================
# TASK STATUSES (reference)
# ============================================================


@mcp.tool()
def list_task_statuses() -> list[dict]:
    """List all available task statuses with their short names."""
    statuses = gazu.task.all_task_statuses()
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "short_name": s.get("short_name"),
            "color": s.get("color"),
            "is_done": s.get("is_done"),
        }
        for s in statuses
    ]


# ============================================================
# NOTIFICATIONS
# ============================================================


@mcp.tool()
def list_notifications() -> list[dict]:
    """List recent notifications for the logged-in user."""
    notifications = gazu.user.all_notifications()
    return [
        {
            "id": n.get("id"),
            "type": n.get("notification_type"),
            "task_type_name": n.get("task_type_name"),
            "task_status_name": n.get("task_status_name"),
            "author_name": n.get("author_full_name"),
            "comment_text": n.get("comment_text"),
            "entity_name": n.get("full_entity_name"),
            "created_at": n.get("created_at"),
            "read": n.get("read"),
        }
        for n in notifications[:30]
    ]


# ============================================================
# CREATE: PROJECTS
# ============================================================


@mcp.tool()
def create_project(
    name: str,
    production_type: str = "short",
    production_style: str = "2d3d",
) -> dict:
    """Create a new production project in Kitsu.

    Args:
        name: The name of the project
        production_type: Type of production — 'short', 'featurefilm', or 'tvshow'
        production_style: Visual style — '2d3d', '2d', '3d', 'ar', 'vr', 'stop-motion'
    """
    project = gazu.project.new_project(
        name=name,
        production_type=production_type,
        production_style=production_style,
    )
    return _slim_entity(project)


# ============================================================
# CREATE: ASSETS
# ============================================================


@mcp.tool()
def create_asset_type(name: str) -> dict:
    """Create a new asset type (e.g. Character, Prop, Environment). Returns existing one if it already exists.

    Args:
        name: The name of the asset type
    """
    asset_type = gazu.asset.new_asset_type(name)
    return _slim_entity(asset_type)


@mcp.tool()
def create_asset(
    project_name: str,
    asset_type_name: str,
    name: str,
    description: str = "",
) -> dict:
    """Create a new asset in a project.

    Args:
        project_name: The name of the project
        asset_type_name: The asset type (e.g. 'Character', 'Prop', 'Environment')
        name: The name of the asset
        description: Optional description
    """
    project = gazu.project.get_project_by_name(project_name)
    if not project:
        return {"error": f"Project '{project_name}' not found"}

    asset_type = gazu.asset.get_asset_type_by_name(asset_type_name)
    if not asset_type:
        return {"error": f"Asset type '{asset_type_name}' not found. Create it first with create_asset_type."}

    asset = gazu.asset.new_asset(
        project=project,
        asset_type=asset_type,
        name=name,
        description=description or None,
    )
    return _slim_entity(asset)


# ============================================================
# CREATE: SHOTS & SEQUENCES
# ============================================================


@mcp.tool()
def create_episode(project_name: str, name: str) -> dict:
    """Create a new episode in a project (for TV show productions).

    Args:
        project_name: The name of the project
        name: The name of the episode (e.g. 'E01')
    """
    project = gazu.project.get_project_by_name(project_name)
    if not project:
        return {"error": f"Project '{project_name}' not found"}

    episode = gazu.shot.new_episode(project=project, name=name)
    return _slim_entity(episode)


@mcp.tool()
def create_sequence(
    project_name: str,
    name: str,
    episode_name: str | None = None,
) -> dict:
    """Create a new sequence in a project.

    Args:
        project_name: The name of the project
        name: The name of the sequence (e.g. 'SQ01')
        episode_name: Optional episode name (for TV show productions)
    """
    project = gazu.project.get_project_by_name(project_name)
    if not project:
        return {"error": f"Project '{project_name}' not found"}

    episode = None
    if episode_name:
        episode = gazu.shot.get_episode_by_name(project, episode_name)
        if not episode:
            return {"error": f"Episode '{episode_name}' not found"}

    sequence = gazu.shot.new_sequence(project=project, name=name, episode=episode)
    return _slim_entity(sequence)


@mcp.tool()
def create_shot(
    project_name: str,
    sequence_name: str,
    name: str,
    nb_frames: int | None = None,
    frame_in: int | None = None,
    frame_out: int | None = None,
    description: str = "",
) -> dict:
    """Create a new shot in a sequence.

    Args:
        project_name: The name of the project
        sequence_name: The name of the sequence
        name: The name of the shot (e.g. 'SH001')
        nb_frames: Optional number of frames
        frame_in: Optional start frame
        frame_out: Optional end frame
        description: Optional description
    """
    project = gazu.project.get_project_by_name(project_name)
    if not project:
        return {"error": f"Project '{project_name}' not found"}

    sequence = gazu.shot.get_sequence_by_name(project, sequence_name)
    if not sequence:
        return {"error": f"Sequence '{sequence_name}' not found"}

    shot = gazu.shot.new_shot(
        project=project,
        sequence=sequence,
        name=name,
        nb_frames=nb_frames,
        frame_in=frame_in,
        frame_out=frame_out,
        description=description or None,
    )
    return _slim_entity(shot)


# ============================================================
# CREATE: TASKS
# ============================================================


@mcp.tool()
def create_task(
    project_name: str,
    entity_name: str,
    task_type_name: str,
    entity_type: str = "asset",
    assignee_emails: list[str] | None = None,
) -> dict:
    """Create a new task for an asset or shot.

    Args:
        project_name: The name of the project
        entity_name: The name of the asset or shot
        task_type_name: The task type (e.g. 'Modeling', 'Animation', 'Lighting', 'Layout')
        entity_type: Either 'asset' or 'shot'
        assignee_emails: Optional list of email addresses to assign
    """
    project = gazu.project.get_project_by_name(project_name)
    if not project:
        return {"error": f"Project '{project_name}' not found"}

    # Find entity
    if entity_type == "shot":
        sequences = gazu.shot.all_sequences_for_project(project)
        entity = None
        for seq in sequences:
            entity = gazu.shot.get_shot_by_name(seq, entity_name)
            if entity:
                break
        if not entity:
            return {"error": f"Shot '{entity_name}' not found"}
    else:
        entity = gazu.asset.get_asset_by_name(project, entity_name)
        if not entity:
            return {"error": f"Asset '{entity_name}' not found"}

    # Find task type
    task_types = gazu.task.all_task_types_for_project(project)
    task_type = None
    for tt in task_types:
        if tt["name"].lower() == task_type_name.lower():
            task_type = tt
            break
    if not task_type:
        # Try global task types
        task_type = gazu.task.get_task_type_by_name(task_type_name)
    if not task_type:
        return {
            "error": f"Task type '{task_type_name}' not found",
            "available": [tt["name"] for tt in task_types],
        }

    # Resolve assignees
    assignees = []
    if assignee_emails:
        for email in assignee_emails:
            person = gazu.person.get_person_by_email(email)
            if person:
                assignees.append(person)

    task = gazu.task.new_task(
        entity=entity,
        task_type=task_type,
        assignees=assignees or None,
    )
    return _slim_entity(task)


# ============================================================
# CASTING: link assets to shots
# ============================================================


@mcp.tool()
def set_shot_casting(
    project_name: str,
    sequence_name: str,
    shot_name: str,
    asset_names: list[str],
) -> dict:
    """Set which assets appear in a shot (casting/breakdown).

    Args:
        project_name: The name of the project
        sequence_name: The name of the sequence
        shot_name: The name of the shot
        asset_names: List of asset names to cast in the shot
    """
    project = gazu.project.get_project_by_name(project_name)
    if not project:
        return {"error": f"Project '{project_name}' not found"}

    sequence = gazu.shot.get_sequence_by_name(project, sequence_name)
    if not sequence:
        return {"error": f"Sequence '{sequence_name}' not found"}

    shot = gazu.shot.get_shot_by_name(sequence, shot_name)
    if not shot:
        return {"error": f"Shot '{shot_name}' not found"}

    casting = []
    not_found = []
    for asset_name in asset_names:
        asset = gazu.asset.get_asset_by_name(project, asset_name)
        if asset:
            casting.append({"asset_id": asset["id"], "nb_occurences": 1})
        else:
            not_found.append(asset_name)

    if casting:
        gazu.casting.update_shot_casting(shot, casting)

    result = {"success": True, "cast_count": len(casting)}
    if not_found:
        result["not_found"] = not_found
    return result


# ============================================================

if __name__ == "__main__":
    mcp.run(transport="stdio")
