"""
Kitsu MCP Server
Connects Claude (or any MCP client) to Kitsu production management via the Gazu API.
"""

import os
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

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
    instructions="Kitsu production management — manage projects, assets, shots, tasks, team, previews, budgets, playlists, and more via the Kitsu/Zou API.",
    lifespan=kitsu_lifespan,
)

# ============================================================
# Helpers
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


def _resolve_project(name):
    """Resolve project by name. Returns (project, error_dict|None)."""
    project = gazu.project.get_project_by_name(name)
    if not project:
        return None, {"error": f"Project '{name}' not found"}
    return project, None


def _resolve_sequence(project, name):
    """Resolve sequence by name within a project. Returns (sequence, error_dict|None)."""
    sequence = gazu.shot.get_sequence_by_name(project, name)
    if not sequence:
        return None, {"error": f"Sequence '{name}' not found"}
    return sequence, None


def _resolve_shot(project, sequence_name, shot_name):
    """Resolve shot by sequence and shot name. Returns (shot, sequence, error_dict|None)."""
    sequence, err = _resolve_sequence(project, sequence_name)
    if err:
        return None, None, err
    shot = gazu.shot.get_shot_by_name(sequence, shot_name)
    if not shot:
        return None, sequence, {"error": f"Shot '{shot_name}' not found"}
    return shot, sequence, None


def _resolve_entity(project, name, entity_type="asset"):
    """Resolve an entity (asset or shot) by name. Returns (entity, error_dict|None)."""
    if entity_type == "shot":
        sequences = gazu.shot.all_sequences_for_project(project)
        for seq in sequences:
            entity = gazu.shot.get_shot_by_name(seq, name)
            if entity:
                return entity, None
        return None, {"error": f"Shot '{name}' not found"}
    else:
        entity = gazu.asset.get_asset_by_name(project, name)
        if not entity:
            return None, {"error": f"Asset '{name}' not found"}
        return entity, None


def _resolve_task_type(project, name):
    """Resolve task type by name within a project. Returns (task_type, error_dict|None)."""
    task_types = gazu.task.all_task_types_for_project(project)
    for tt in task_types:
        if tt["name"].lower() == name.lower():
            return tt, None
    # Try global
    task_type = gazu.task.get_task_type_by_name(name)
    if task_type:
        return task_type, None
    return None, {
        "error": f"Task type '{name}' not found",
        "available": [tt["name"] for tt in task_types],
    }


def _resolve_person(email):
    """Resolve person by email. Returns (person, error_dict|None)."""
    person = gazu.person.get_person_by_email(email)
    if not person:
        return None, {"error": f"Person with email '{email}' not found"}
    return person, None


def _resolve_task(task_id):
    """Resolve task by ID. Returns (task, error_dict|None)."""
    task = gazu.task.get_task(task_id)
    if not task:
        return None, {"error": f"Task '{task_id}' not found"}
    return task, None


def _resolve_status(status_name):
    """Resolve task status by short name or full name. Returns (status, error_dict|None)."""
    status = gazu.task.get_task_status_by_short_name(status_name.lower())
    if not status:
        status = gazu.task.get_task_status_by_name(status_name)
    if not status:
        all_statuses = gazu.task.all_task_statuses()
        return None, {
            "error": f"Status '{status_name}' not found",
            "available_statuses": [
                {"name": s["name"], "short_name": s.get("short_name")}
                for s in all_statuses
            ],
        }
    return status, None


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
    project, err = _resolve_project(project_name)
    if err:
        return err

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


@mcp.tool()
def get_project_stats(project_name: str) -> dict:
    """Get task statistics for a project grouped by status.

    Args:
        project_name: The name of the project
    """
    project, err = _resolve_project(project_name)
    if err:
        return err

    tasks = gazu.task.all_tasks_for_project(project)
    stats = {}
    for t in tasks:
        status = t.get("task_status_name", "Unknown")
        stats[status] = stats.get(status, 0) + 1

    return {
        "project": project_name,
        "total_tasks": len(tasks),
        "by_status": stats,
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
    project, err = _resolve_project(project_name)
    if err:
        return [err]

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
    project, err = _resolve_project(project_name)
    if err:
        return err

    asset, err = _resolve_entity(project, asset_name, "asset")
    if err:
        return err

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


@mcp.tool()
def update_asset(
    project_name: str,
    asset_name: str,
    description: str | None = None,
    data: dict | None = None,
) -> dict:
    """Update an asset's description or custom metadata.

    Args:
        project_name: The name of the project
        asset_name: The name of the asset
        description: New description (optional)
        data: Custom metadata dict to merge (optional)
    """
    project, err = _resolve_project(project_name)
    if err:
        return err

    asset, err = _resolve_entity(project, asset_name, "asset")
    if err:
        return err

    updates = {}
    if description is not None:
        updates["description"] = description
    if data is not None:
        existing_data = asset.get("data") or {}
        existing_data.update(data)
        updates["data"] = existing_data

    if not updates:
        return {"error": "No updates provided"}

    asset.update(updates)
    gazu.asset.update_asset(asset)
    return {"success": True, "asset": asset_name, "updated_fields": list(updates.keys())}


@mcp.tool()
def delete_asset(project_name: str, asset_name: str, confirm: bool = False) -> dict:
    """Delete an asset. Requires confirm=True as safety check.

    Args:
        project_name: The name of the project
        asset_name: The name of the asset
        confirm: Must be True to proceed with deletion
    """
    if not confirm:
        return {"error": "Set confirm=True to delete. This action is irreversible."}

    project, err = _resolve_project(project_name)
    if err:
        return err

    asset, err = _resolve_entity(project, asset_name, "asset")
    if err:
        return err

    gazu.asset.remove_asset(asset)
    return {"success": True, "deleted": asset_name}


# ============================================================
# SHOTS & SEQUENCES
# ============================================================


@mcp.tool()
def list_sequences(project_name: str) -> list[dict]:
    """List all sequences in a project.

    Args:
        project_name: The name of the project
    """
    project, err = _resolve_project(project_name)
    if err:
        return [err]

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
    project, err = _resolve_project(project_name)
    if err:
        return [err]

    if sequence_name:
        sequence, err = _resolve_sequence(project, sequence_name)
        if err:
            return [err]
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
    project, err = _resolve_project(project_name)
    if err:
        return err

    shot, sequence, err = _resolve_shot(project, sequence_name, shot_name)
    if err:
        return err

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


@mcp.tool()
def update_shot(
    project_name: str,
    sequence_name: str,
    shot_name: str,
    description: str | None = None,
    nb_frames: int | None = None,
    frame_in: int | None = None,
    frame_out: int | None = None,
    data: dict | None = None,
) -> dict:
    """Update a shot's description, frame range, or custom metadata.

    Args:
        project_name: The name of the project
        sequence_name: The name of the sequence
        shot_name: The name of the shot
        description: New description (optional)
        nb_frames: New frame count (optional)
        frame_in: New start frame (optional)
        frame_out: New end frame (optional)
        data: Custom metadata dict to merge (optional)
    """
    project, err = _resolve_project(project_name)
    if err:
        return err

    shot, _, err = _resolve_shot(project, sequence_name, shot_name)
    if err:
        return err

    updates = {}
    if description is not None:
        updates["description"] = description
    if nb_frames is not None:
        updates["nb_frames"] = nb_frames
    if frame_in is not None:
        updates["frame_in"] = frame_in
    if frame_out is not None:
        updates["frame_out"] = frame_out
    if data is not None:
        existing_data = shot.get("data") or {}
        existing_data.update(data)
        updates["data"] = existing_data

    if not updates:
        return {"error": "No updates provided"}

    shot.update(updates)
    gazu.shot.update_shot(shot)
    return {"success": True, "shot": shot_name, "updated_fields": list(updates.keys())}


@mcp.tool()
def delete_shot(
    project_name: str, sequence_name: str, shot_name: str, confirm: bool = False
) -> dict:
    """Delete a shot. Requires confirm=True as safety check.

    Args:
        project_name: The name of the project
        sequence_name: The name of the sequence
        shot_name: The name of the shot
        confirm: Must be True to proceed with deletion
    """
    if not confirm:
        return {"error": "Set confirm=True to delete. This action is irreversible."}

    project, err = _resolve_project(project_name)
    if err:
        return err

    shot, _, err = _resolve_shot(project, sequence_name, shot_name)
    if err:
        return err

    gazu.shot.remove_shot(shot)
    return {"success": True, "deleted": shot_name}


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
        project, _ = _resolve_project(project_name)
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
    project, err = _resolve_project(project_name)
    if err:
        return [err]

    entity, err = _resolve_entity(project, entity_name, entity_type)
    if err:
        return [err]

    if entity_type == "shot":
        tasks = gazu.task.all_tasks_for_shot(entity)
    else:
        tasks = gazu.task.all_tasks_for_asset(entity)

    return _slim_list(tasks)


@mcp.tool()
def get_task_details(task_id: str) -> dict:
    """Get detailed information about a task including comments history.

    Args:
        task_id: The UUID of the task
    """
    task, err = _resolve_task(task_id)
    if err:
        return err

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
    task, err = _resolve_task(task_id)
    if err:
        return err

    status, err = _resolve_status(status_name)
    if err:
        return err

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
    task, err = _resolve_task(task_id)
    if err:
        return err

    person, err = _resolve_person(person_email)
    if err:
        return err

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
    task, err = _resolve_task(task_id)
    if err:
        return err

    gazu.task.update_task(task, {"estimation": days})
    return {"success": True, "task_id": task_id, "estimation_days": days}


@mcp.tool()
def delete_task(task_id: str, confirm: bool = False) -> dict:
    """Delete a task. Requires confirm=True as safety check.

    Args:
        task_id: The UUID of the task
        confirm: Must be True to proceed with deletion
    """
    if not confirm:
        return {"error": "Set confirm=True to delete. This action is irreversible."}

    task, err = _resolve_task(task_id)
    if err:
        return err

    gazu.task.remove_task(task)
    return {"success": True, "deleted_task_id": task_id}


# ============================================================
# TIME TRACKING
# ============================================================


@mcp.tool()
def add_time_spent(task_id: str, person_email: str, date: str, duration: float) -> dict:
    """Add time spent on a task.

    Args:
        task_id: The UUID of the task
        person_email: Email of the person who worked
        date: Date in YYYY-MM-DD format
        duration: Duration in hours (will be converted to minutes)
    """
    task, err = _resolve_task(task_id)
    if err:
        return err

    person, err = _resolve_person(person_email)
    if err:
        return err

    result = gazu.task.add_time_spent(task, person, date, duration * 60)
    return {"success": True, "task_id": task_id, "hours": duration, "date": date}


@mcp.tool()
def set_time_spent(task_id: str, person_email: str, date: str, duration: float) -> dict:
    """Set (overwrite) time spent on a task for a specific date.

    Args:
        task_id: The UUID of the task
        person_email: Email of the person who worked
        date: Date in YYYY-MM-DD format
        duration: Duration in hours (will be converted to minutes)
    """
    task, err = _resolve_task(task_id)
    if err:
        return err

    person, err = _resolve_person(person_email)
    if err:
        return err

    result = gazu.task.set_time_spent(task, person, date, duration * 60)
    return {"success": True, "task_id": task_id, "hours": duration, "date": date}


@mcp.tool()
def get_time_spent(task_id: str) -> dict:
    """Get all time entries for a task.

    Args:
        task_id: The UUID of the task
    """
    task, err = _resolve_task(task_id)
    if err:
        return err

    time_spents = gazu.task.get_time_spent(task)
    return {"task_id": task_id, "time_spents": time_spents}


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
    task, err = _resolve_task(task_id)
    if err:
        return err

    if status_name:
        status, err = _resolve_status(status_name)
        if err:
            return err
    else:
        status = gazu.task.get_task_status(task["task_status_id"])

    result = gazu.task.add_comment(task, status, comment=text)
    return {"success": True, "comment_id": result.get("id")}


@mcp.tool()
def list_comments(task_id: str) -> list[dict]:
    """List all comments for a task.

    Args:
        task_id: The UUID of the task
    """
    task, err = _resolve_task(task_id)
    if err:
        return [err]

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
# PREVIEWS
# ============================================================


@mcp.tool()
def upload_preview(
    task_id: str,
    file_path: str,
    comment: str = "",
    status_name: str | None = None,
) -> dict:
    """Upload a preview file (image/video) to a task with an optional comment and status change.

    Args:
        task_id: The UUID of the task
        file_path: Absolute path to the preview file (PNG, JPG, MP4, etc.)
        comment: Optional comment text
        status_name: Optional new status (e.g. 'wfa', 'wip')
    """
    task, err = _resolve_task(task_id)
    if err:
        return err

    if not os.path.isfile(file_path):
        return {"error": f"File not found: {file_path}"}

    if status_name:
        status, err = _resolve_status(status_name)
        if err:
            return err
    else:
        status = gazu.task.get_task_status(task["task_status_id"])

    comment_result = gazu.task.add_comment(task, status, comment=comment)
    preview = gazu.task.add_preview(task, comment_result, file_path)
    gazu.task.set_main_preview(preview)

    return {
        "success": True,
        "task_id": task_id,
        "comment_id": comment_result.get("id"),
        "preview_id": preview.get("id"),
    }


@mcp.tool()
def set_main_preview(
    preview_id: str,
) -> dict:
    """Set a preview file as the main preview (thumbnail) for its entity.

    Args:
        preview_id: The UUID of the preview file
    """
    try:
        result = gazu.task.set_main_preview({"id": preview_id})
        return {"success": True, "preview_id": preview_id}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def publish_preview(
    task_id: str,
    file_path: str,
    status_name: str,
    comment: str = "",
) -> dict:
    """Publish a preview: change status + add comment + upload preview file in one step.

    Args:
        task_id: The UUID of the task
        file_path: Absolute path to the preview file
        status_name: New status (e.g. 'wfa', 'done')
        comment: Optional comment text
    """
    task, err = _resolve_task(task_id)
    if err:
        return err

    if not os.path.isfile(file_path):
        return {"error": f"File not found: {file_path}"}

    status, err = _resolve_status(status_name)
    if err:
        return err

    comment_result = gazu.task.add_comment(task, status, comment=comment)
    preview = gazu.task.add_preview(task, comment_result, file_path)
    gazu.task.set_main_preview(preview)

    return {
        "success": True,
        "task_id": task_id,
        "new_status": status_name,
        "comment_id": comment_result.get("id"),
        "preview_id": preview.get("id"),
    }


# ============================================================
# BATCH OPERATIONS
# ============================================================


@mcp.tool()
def batch_create_shots(
    project_name: str,
    sequence_name: str,
    prefix: str = "SH",
    start: int = 10,
    end: int = 100,
    step: int = 10,
    nb_frames: int | None = None,
) -> dict:
    """Create multiple shots at once (e.g. SH010, SH020, ... SH100).

    Args:
        project_name: The name of the project
        sequence_name: The name of the sequence
        prefix: Shot name prefix (default 'SH')
        start: First shot number (default 10)
        end: Last shot number inclusive (default 100)
        step: Increment between shot numbers (default 10)
        nb_frames: Optional frame count for each shot
    """
    project, err = _resolve_project(project_name)
    if err:
        return err

    sequence, err = _resolve_sequence(project, sequence_name)
    if err:
        return err

    created = []
    errors = []
    for num in range(start, end + 1, step):
        name = f"{prefix}{num:03d}"
        try:
            shot = gazu.shot.new_shot(
                project=project,
                sequence=sequence,
                name=name,
                nb_frames=nb_frames,
            )
            created.append(name)
        except Exception as e:
            errors.append({"name": name, "error": str(e)})

    result = {"success": True, "created": len(created), "shot_names": created}
    if errors:
        result["errors"] = errors
    return result


@mcp.tool()
def batch_create_tasks(
    project_name: str,
    task_type_name: str,
    entity_type: str = "shot",
    sequence_name: str | None = None,
    asset_type_name: str | None = None,
    assignee_emails: list[str] | None = None,
) -> dict:
    """Create a task type for all shots in a sequence or all assets of a type.

    Args:
        project_name: The name of the project
        task_type_name: The task type (e.g. 'Animation', 'Lighting')
        entity_type: 'shot' or 'asset'
        sequence_name: Required if entity_type is 'shot' — which sequence
        asset_type_name: Required if entity_type is 'asset' — which asset type
        assignee_emails: Optional list of email addresses to assign to each task
    """
    project, err = _resolve_project(project_name)
    if err:
        return err

    task_type, err = _resolve_task_type(project, task_type_name)
    if err:
        return err

    # Resolve assignees
    assignees = []
    if assignee_emails:
        for email in assignee_emails:
            person, _ = _resolve_person(email)
            if person:
                assignees.append(person)

    # Get entities
    if entity_type == "shot":
        if not sequence_name:
            return {"error": "sequence_name is required for entity_type='shot'"}
        sequence, err = _resolve_sequence(project, sequence_name)
        if err:
            return err
        entities = gazu.shot.all_shots_for_sequence(sequence)
    else:
        assets = gazu.asset.all_assets_for_project(project)
        if asset_type_name:
            at = gazu.asset.get_asset_type_by_name(asset_type_name)
            if at:
                assets = [a for a in assets if a.get("asset_type_id") == at["id"]]
        entities = assets

    created = []
    errors = []
    for entity in entities:
        try:
            gazu.task.new_task(
                entity=entity,
                task_type=task_type,
                assignees=assignees or None,
            )
            created.append(entity.get("name", entity.get("id")))
        except Exception as e:
            errors.append({"entity": entity.get("name"), "error": str(e)})

    result = {"success": True, "created": len(created), "entity_names": created}
    if errors:
        result["errors"] = errors
    return result


# ============================================================
# DAILY PROGRESS REPORT
# ============================================================


@mcp.tool()
def daily_progress_report(project_name: str, hours: int = 24) -> dict:
    """Get a summary of all activity in a project in the last N hours.

    Args:
        project_name: The name of the project
        hours: Look-back window in hours (default 24)
    """
    project, err = _resolve_project(project_name)
    if err:
        return err

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    cutoff_str = cutoff.isoformat()

    # Get all tasks and filter by recent comment date
    tasks = gazu.task.all_tasks_for_project(project)
    recent_tasks = [
        t for t in tasks
        if t.get("last_comment_date") and t["last_comment_date"] >= cutoff_str
    ]

    activity = []
    for t in recent_tasks:
        comments = gazu.task.all_comments_for_task(t)
        recent_comments = [
            c for c in comments
            if c.get("created_at", "") >= cutoff_str
        ]
        for c in recent_comments:
            activity.append({
                "entity_name": t.get("entity_name", ""),
                "task_type": t.get("task_type_name", ""),
                "author": c.get("person", {}).get("full_name", "Unknown"),
                "status": c.get("task_status", {}).get("name", ""),
                "text": c.get("text", ""),
                "created_at": c.get("created_at", ""),
            })

    # Sort by time descending
    activity.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return {
        "project": project_name,
        "hours": hours,
        "total_updates": len(activity),
        "activity": activity[:100],
    }


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
    project, err = _resolve_project(project_name)
    if err:
        return [err]

    shot, _, err = _resolve_shot(project, sequence_name, shot_name)
    if err:
        return [err]

    casting = gazu.casting.get_shot_casting(shot)
    return [
        {
            "asset_name": c.get("asset_name"),
            "asset_type_name": c.get("asset_type_name"),
            "nb_occurences": c.get("nb_occurences"),
        }
        for c in casting
    ]


@mcp.tool()
def get_asset_casting(project_name: str, asset_name: str) -> list[dict]:
    """Get the casting for an asset (which shots it appears in).

    Args:
        project_name: The name of the project
        asset_name: The name of the asset
    """
    project, err = _resolve_project(project_name)
    if err:
        return [err]

    asset, err = _resolve_entity(project, asset_name, "asset")
    if err:
        return [err]

    casting = gazu.casting.get_asset_casting(asset)
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


def _get_project_membership(project_id: str, person_id: str) -> tuple[dict | None, dict | None]:
    """Fetch the project-membership record for a person in a project.

    Returns (membership_dict, None) on success or (None, error_dict) on failure.
    Project-memberships store the *project* role (artist/client/…), which is
    separate from the global Person role (user/admin/manager).
    """
    try:
        memberships = gazu.client.get(
            f"data/project-memberships?project_id={project_id}&person_id={person_id}"
        )
        if not memberships:
            return None, {"error": "Person is not a member of this project"}
        return memberships[0], None
    except Exception as exc:
        return None, {"error": f"Failed to fetch project membership: {exc}"}


def _set_membership_role(membership_id: str, role: str) -> dict | None:
    """PUT the new role on an existing project-membership record.

    Returns an error dict on failure, None on success.
    """
    try:
        gazu.client.put(
            f"data/project-memberships/{membership_id}",
            {"role": role},
        )
        return None
    except Exception as exc:
        return {"error": f"Failed to update membership role: {exc}"}


@mcp.tool()
def list_team_members(project_name: str) -> list[dict]:
    """List all team members in a project, showing their project-level role.

    Args:
        project_name: The name of the project
    """
    project, err = _resolve_project(project_name)
    if err:
        return [err]

    # Fetch persons and their project-membership roles in parallel
    team = gazu.project.get_team(project)
    try:
        memberships = gazu.client.get(
            f"data/project-memberships?project_id={project['id']}"
        )
        role_by_person = {m["person_id"]: m.get("role", "unknown") for m in memberships}
    except Exception:
        role_by_person = {}

    result = []
    for member in team:
        result.append({
            "id": member["id"],
            "full_name": member["full_name"],
            "email": member["email"],
            "project_role": role_by_person.get(member["id"], "unknown"),
            "active": member.get("active", True),
        })
    return result


@mcp.tool()
def update_team_member_role(
    project_name: str,
    person_email: str,
    role: str,
) -> dict:
    """Update a person's project-level role (artist/supervisor/manager/vendor/client).

    Args:
        project_name: The name of the project
        person_email: Email of the person whose role to change
        role: New project role — 'artist', 'supervisor', 'manager', 'vendor', or 'client'
    """
    valid_roles = {"artist", "supervisor", "manager", "vendor", "client"}
    if role.lower() not in valid_roles:
        return {"error": f"Invalid role '{role}'. Must be one of: {', '.join(sorted(valid_roles))}"}

    project, err = _resolve_project(project_name)
    if err:
        return err

    person, err = _resolve_person(person_email)
    if err:
        return err

    membership, err = _get_project_membership(project["id"], person["id"])
    if err:
        return err

    old_role = membership.get("role", "unknown")

    err = _set_membership_role(membership["id"], role.lower())
    if err:
        return err

    return {
        "success": True,
        "person": person["full_name"],
        "project": project_name,
        "old_role": old_role,
        "new_role": role.lower(),
    }


@mcp.tool()
def add_team_member(
    project_name: str,
    person_email: str,
    role: str = "artist",
) -> dict:
    """Add a person to a project's team with the specified role.

    Args:
        project_name: The name of the project
        person_email: Email of the person to add
        role: Project role — 'artist', 'supervisor', 'manager', 'vendor', or 'client' (default: 'artist')
    """
    valid_roles = {"artist", "supervisor", "manager", "vendor", "client"}
    if role.lower() not in valid_roles:
        return {"error": f"Invalid role '{role}'. Must be one of: {', '.join(sorted(valid_roles))}"}

    project, err = _resolve_project(project_name)
    if err:
        return err

    person, err = _resolve_person(person_email)
    if err:
        return err

    # Check if already a member
    team = gazu.project.get_team(project)
    if any(m["id"] == person["id"] for m in team):
        return {"error": f"{person['full_name']} is already a member of project '{project_name}'"}

    # Add to team (Kitsu always creates membership with default role 'artist')
    gazu.client.post(
        f"data/projects/{project['id']}/team",
        {"person_id": person["id"]},
    )

    # If a non-default role was requested, update the membership record directly
    if role.lower() != "artist":
        membership, err = _get_project_membership(project["id"], person["id"])
        if err:
            return {"error": f"Person added but role not set: {err['error']}"}
        err = _set_membership_role(membership["id"], role.lower())
        if err:
            return {"error": f"Person added but role not set: {err['error']}"}

    return {
        "success": True,
        "person": person["full_name"],
        "project": project_name,
        "role": role.lower(),
    }


@mcp.tool()
def get_person_tasks(person_email: str, project_name: str | None = None) -> list[dict]:
    """Get all tasks assigned to a specific person.

    Args:
        person_email: Email address of the person
        project_name: Optional project name to filter by
    """
    person, err = _resolve_person(person_email)
    if err:
        return [err]

    tasks = gazu.task.all_tasks_for_person(person)

    if project_name:
        project, _ = _resolve_project(project_name)
        if project:
            tasks = [t for t in tasks if t.get("project_id") == project["id"]]

    return _slim_list(tasks)


@mcp.tool()
def create_person(
    first_name: str,
    last_name: str,
    email: str,
    role: str = "user",
    phone: str | None = None,
) -> dict:
    """Create a new person/user in Kitsu.

    Args:
        first_name: First name
        last_name: Last name
        email: Email address (used for login)
        role: Role — 'user', 'manager', or 'admin'
        phone: Optional phone number
    """
    person = gazu.person.new_person(
        first_name=first_name,
        last_name=last_name,
        email=email,
        role=role,
        phone=phone,
    )

    # Automatically send invite email so the user can set their password
    try:
        gazu.client.post("auth/reset-password", {"email": email})
        invite_sent = True
    except Exception:
        invite_sent = False

    result = _slim_entity(person)
    result["invite_email_sent"] = invite_sent
    return result


@mcp.tool()
def list_departments() -> list[dict]:
    """List all departments in Kitsu."""
    departments = gazu.person.all_departments()
    return _slim_list(departments, ["id", "name", "color"])


@mcp.tool()
def create_department(name: str, color: str = "#999999") -> dict:
    """Create a new department.

    Args:
        name: Department name (e.g. 'Animation', 'Lighting')
        color: Hex color code (default '#999999')
    """
    department = gazu.person.new_department(name=name, color=color)
    return _slim_entity(department)


@mcp.tool()
def add_person_to_department(person_email: str, department_name: str) -> dict:
    """Add a person to a department.

    Args:
        person_email: Email of the person
        department_name: Name of the department
    """
    person, err = _resolve_person(person_email)
    if err:
        return err

    departments = gazu.person.all_departments()
    dept = None
    for d in departments:
        if d["name"].lower() == department_name.lower():
            dept = d
            break
    if not dept:
        return {"error": f"Department '{department_name}' not found"}

    gazu.person.add_person_to_department(person, dept)
    return {"success": True, "person": person["full_name"], "department": department_name}


@mcp.tool()
def remove_person_from_department(person_email: str, department_name: str) -> dict:
    """Remove a person from a department.

    Args:
        person_email: Email of the person
        department_name: Name of the department
    """
    person, err = _resolve_person(person_email)
    if err:
        return err

    departments = gazu.person.all_departments()
    dept = None
    for d in departments:
        if d["name"].lower() == department_name.lower():
            dept = d
            break
    if not dept:
        return {"error": f"Department '{department_name}' not found"}

    gazu.person.remove_person_from_department(person, dept)
    return {"success": True, "person": person["full_name"], "department": department_name}


# ============================================================
# PLAYLISTS
# ============================================================


@mcp.tool()
def list_playlists(project_name: str) -> list[dict]:
    """List all playlists in a project.

    Args:
        project_name: The name of the project
    """
    project, err = _resolve_project(project_name)
    if err:
        return [err]

    playlists = gazu.playlist.all_playlists_for_project(project)
    return _slim_list(playlists, ["id", "name", "created_at", "updated_at"])


@mcp.tool()
def create_playlist(project_name: str, name: str) -> dict:
    """Create a new playlist in a project.

    Args:
        project_name: The name of the project
        name: The name of the playlist
    """
    project, err = _resolve_project(project_name)
    if err:
        return err

    playlist = gazu.playlist.new_playlist(project=project, name=name)
    return _slim_entity(playlist)


@mcp.tool()
def add_entity_to_playlist(
    playlist_id: str,
    entity_id: str,
    preview_file_id: str | None = None,
) -> dict:
    """Add a shot or asset to a playlist.

    Args:
        playlist_id: The UUID of the playlist
        entity_id: The UUID of the shot or asset entity
        preview_file_id: Optional specific preview file ID to use
    """
    playlist = gazu.playlist.get_playlist(playlist_id)
    if not playlist:
        return {"error": f"Playlist '{playlist_id}' not found"}

    shot = {"id": entity_id}
    result = gazu.playlist.add_entity_to_playlist(
        playlist, shot, preview_file_id=preview_file_id
    )
    return {"success": True, "playlist_id": playlist_id, "entity_id": entity_id}


@mcp.tool()
def build_playlist_movie(playlist_id: str) -> dict:
    """Build a movie file from a playlist's shots.

    Args:
        playlist_id: The UUID of the playlist
    """
    playlist = gazu.playlist.get_playlist(playlist_id)
    if not playlist:
        return {"error": f"Playlist '{playlist_id}' not found"}

    result = gazu.playlist.build_playlist_movie(playlist)
    return {"success": True, "playlist_id": playlist_id, "result": str(result)}


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
        project, _ = _resolve_project(project_name)

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


@mcp.tool()
def close_project(project_name: str, confirm: bool = False) -> dict:
    """Close/archive a project. Requires confirm=True.

    Args:
        project_name: The name of the project
        confirm: Must be True to proceed
    """
    if not confirm:
        return {"error": "Set confirm=True to close the project."}

    project, err = _resolve_project(project_name)
    if err:
        return err

    gazu.project.close_project(project)
    return {"success": True, "closed": project_name}


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
    project, err = _resolve_project(project_name)
    if err:
        return err

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
    project, err = _resolve_project(project_name)
    if err:
        return err

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
    project, err = _resolve_project(project_name)
    if err:
        return err

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
    project, err = _resolve_project(project_name)
    if err:
        return err

    sequence, err = _resolve_sequence(project, sequence_name)
    if err:
        return err

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
    project, err = _resolve_project(project_name)
    if err:
        return err

    entity, err = _resolve_entity(project, entity_name, entity_type)
    if err:
        return err

    task_type, err = _resolve_task_type(project, task_type_name)
    if err:
        return err

    # Resolve assignees
    assignees = []
    if assignee_emails:
        for email in assignee_emails:
            person, _ = _resolve_person(email)
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
    project, err = _resolve_project(project_name)
    if err:
        return err

    shot, _, err = _resolve_shot(project, sequence_name, shot_name)
    if err:
        return err

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
# CSV IMPORT/EXPORT
# ============================================================


@mcp.tool()
def import_assets_csv(project_name: str, csv_path: str) -> dict:
    """Import assets from a CSV file into a project.

    Args:
        project_name: The name of the project
        csv_path: Absolute path to the CSV file
    """
    project, err = _resolve_project(project_name)
    if err:
        return err

    if not os.path.isfile(csv_path):
        return {"error": f"File not found: {csv_path}"}

    result = gazu.asset.import_assets_with_csv(project, csv_path)
    return {"success": True, "result": str(result)}


@mcp.tool()
def export_assets_csv(project_name: str, output_path: str) -> dict:
    """Export assets from a project to a CSV file.

    Args:
        project_name: The name of the project
        output_path: Absolute path where to save the CSV file
    """
    project, err = _resolve_project(project_name)
    if err:
        return err

    csv_content = gazu.asset.export_assets_with_csv(project)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(csv_content)
    return {"success": True, "path": output_path}


@mcp.tool()
def import_shots_csv(project_name: str, csv_path: str) -> dict:
    """Import shots from a CSV file into a project.

    Args:
        project_name: The name of the project
        csv_path: Absolute path to the CSV file
    """
    project, err = _resolve_project(project_name)
    if err:
        return err

    if not os.path.isfile(csv_path):
        return {"error": f"File not found: {csv_path}"}

    result = gazu.shot.import_shots_with_csv(project, csv_path)
    return {"success": True, "result": str(result)}


@mcp.tool()
def export_shots_csv(project_name: str, output_path: str) -> dict:
    """Export shots from a project to a CSV file.

    Args:
        project_name: The name of the project
        output_path: Absolute path where to save the CSV file
    """
    project, err = _resolve_project(project_name)
    if err:
        return err

    csv_content = gazu.shot.export_shots_with_csv(project)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(csv_content)
    return {"success": True, "path": output_path}


@mcp.tool()
def import_otio(project_name: str, otio_path: str) -> dict:
    """Import shots from an OpenTimelineIO file.

    Args:
        project_name: The name of the project
        otio_path: Absolute path to the OTIO file
    """
    project, err = _resolve_project(project_name)
    if err:
        return err

    if not os.path.isfile(otio_path):
        return {"error": f"File not found: {otio_path}"}

    result = gazu.shot.import_otio(project, otio_path)
    return {"success": True, "result": str(result)}


# ============================================================
# BUDGETS
# ============================================================


@mcp.tool()
def get_budgets(project_name: str) -> list[dict]:
    """List all budgets for a project.

    Args:
        project_name: The name of the project
    """
    project, err = _resolve_project(project_name)
    if err:
        return [err]

    budgets = gazu.project.get_budgets(project)
    return budgets


@mcp.tool()
def create_budget(project_name: str, name: str) -> dict:
    """Create a new budget for a project.

    Args:
        project_name: The name of the project
        name: Name of the budget
    """
    project, err = _resolve_project(project_name)
    if err:
        return err

    budget = gazu.project.create_budget(project, name)
    return budget


@mcp.tool()
def get_budget_entries(project_name: str, budget_id: str) -> list[dict]:
    """List all entries in a budget.

    Args:
        project_name: The name of the project
        budget_id: The UUID of the budget
    """
    project, err = _resolve_project(project_name)
    if err:
        return [err]

    entries = gazu.project.get_budget_entries(project, budget_id)
    return entries


@mcp.tool()
def create_budget_entry(
    project_name: str,
    budget_id: str,
    department_id: str | None = None,
    amount: float = 0,
    name: str = "",
) -> dict:
    """Create a budget entry.

    Args:
        project_name: The name of the project
        budget_id: The UUID of the budget
        department_id: Optional department UUID
        amount: Entry amount
        name: Entry name/description
    """
    project, err = _resolve_project(project_name)
    if err:
        return err

    entry = gazu.project.create_budget_entry(
        project, budget_id,
        department_id=department_id,
        amount=amount,
        name=name,
    )
    return entry


# ============================================================
# CONCEPTS
# ============================================================


@mcp.tool()
def list_concepts(project_name: str) -> list[dict]:
    """List all concepts in a project.

    Args:
        project_name: The name of the project
    """
    project, err = _resolve_project(project_name)
    if err:
        return [err]

    concepts = gazu.concept.all_concepts_for_project(project)
    return _slim_list(concepts)


@mcp.tool()
def create_concept(project_name: str, name: str, description: str = "") -> dict:
    """Create a new concept in a project.

    Args:
        project_name: The name of the project
        name: The name of the concept
        description: Optional description
    """
    project, err = _resolve_project(project_name)
    if err:
        return err

    concept = gazu.concept.new_concept(project=project, name=name, description=description or None)
    return _slim_entity(concept)


# ============================================================
# EDITS
# ============================================================


@mcp.tool()
def list_edits(project_name: str) -> list[dict]:
    """List all edits in a project.

    Args:
        project_name: The name of the project
    """
    project, err = _resolve_project(project_name)
    if err:
        return [err]

    edits = gazu.edit.all_edits_for_project(project)
    return _slim_list(edits)


@mcp.tool()
def create_edit(project_name: str, name: str, description: str = "") -> dict:
    """Create a new edit in a project.

    Args:
        project_name: The name of the project
        name: The name of the edit
        description: Optional description
    """
    project, err = _resolve_project(project_name)
    if err:
        return err

    edit = gazu.edit.new_edit(project=project, name=name, description=description or None)
    return _slim_entity(edit)


# ============================================================
# SCENES
# ============================================================


@mcp.tool()
def list_scenes(project_name: str) -> list[dict]:
    """List all scenes in a project.

    Args:
        project_name: The name of the project
    """
    project, err = _resolve_project(project_name)
    if err:
        return [err]

    scenes = gazu.scene.all_scenes_for_project(project)
    return _slim_list(scenes)


@mcp.tool()
def create_scene(project_name: str, sequence_name: str, name: str) -> dict:
    """Create a new scene in a sequence.

    Args:
        project_name: The name of the project
        sequence_name: The name of the sequence
        name: The name of the scene
    """
    project, err = _resolve_project(project_name)
    if err:
        return err

    sequence, err = _resolve_sequence(project, sequence_name)
    if err:
        return err

    scene = gazu.scene.new_scene(project=project, sequence=sequence, name=name)
    return _slim_entity(scene)


# ============================================================
# METADATA DESCRIPTORS
# ============================================================


@mcp.tool()
def list_metadata_descriptors(project_name: str) -> list[dict]:
    """List all custom metadata fields for a project.

    Args:
        project_name: The name of the project
    """
    project, err = _resolve_project(project_name)
    if err:
        return [err]

    descriptors = gazu.project.all_metadata_descriptors(project)
    return descriptors


@mcp.tool()
def add_metadata_descriptor(
    project_name: str,
    name: str,
    entity_type: str,
    field_name: str,
    data_type: str = "string",
    choices: list[str] | None = None,
) -> dict:
    """Add a custom metadata field to a project.

    Args:
        project_name: The name of the project
        name: Display name for the field
        entity_type: Entity type — 'Asset', 'Shot', or 'Edit'
        field_name: Internal field name (used in data dict)
        data_type: Data type — 'string', 'boolean', 'list', 'number'
        choices: List of choices (for 'list' data_type)
    """
    project, err = _resolve_project(project_name)
    if err:
        return err

    descriptor = gazu.project.add_metadata_descriptor(
        project,
        name=name,
        entity_type=entity_type,
        data_type=data_type,
        choices=choices,
    )
    return descriptor


# ============================================================

if __name__ == "__main__":
    mcp.run(transport="stdio")
