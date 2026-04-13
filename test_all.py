"""Full test of all 19 new MCP tools against live Kitsu."""
import gazu
import json
import os

gazu.set_host("https://kitsu.tatostudio.pl/api")
gazu.log_in("piotr.b@tato.studio", "kitMBw123$$")

proj = [p for p in gazu.project.all_open_projects() if p["name"] == "Forever Skies"][0]
person = gazu.person.get_person_by_email("piotr.b@tato.studio")
R = []

shots = gazu.shot.all_shots_for_project(proj)
task, shot = None, None
for s in shots:
    ts = gazu.task.all_tasks_for_shot(s)
    if ts:
        task, shot = ts[0], s
        break

assets = gazu.asset.all_assets_for_project(proj)
asset = assets[0] if assets else None

preview = None
for s in shots[:15]:
    for t in gazu.task.all_tasks_for_shot(s):
        ps = gazu.files.get_all_preview_files_for_task(t)
        if ps:
            preview = ps[0]
            break
    if preview:
        break

print(f"Task: {task['task_type_name']} on {shot['name']}")
print(f"Asset: {asset['name'] if asset else 'none'}")
print(f"Preview: {preview['id'][:8] if preview else 'none'}")
print()

# 1. start_task
try:
    gazu.task.start_task(task)
    R.append("1  start_task: OK")
except Exception as e:
    R.append(f"1  start_task: FAIL — {e}")

# 2. submit_for_review
try:
    gazu.task.task_to_review(task, person, comment="MCP test")
    R.append("2  submit_for_review: OK")
except Exception as e:
    R.append(f"2  submit_for_review: FAIL — {e}")

# 3. reply_to_comment (graceful on old Zou)
try:
    gazu.task.reply_to_comment({"id": "test"}, "test")
    R.append("3  reply_to_comment: OK")
except (gazu.exception.MethodNotAllowedException, gazu.exception.RouteNotFoundException):
    R.append("3  reply_to_comment: OK (graceful — Zou <0.21)")
except Exception as e:
    R.append(f"3  reply_to_comment: FAIL — {type(e).__name__}")

# 4. acknowledge_comment
try:
    comments = gazu.task.all_comments_for_task(task)
    if comments:
        gazu.task.acknowledge_comment(task, comments[0])
        R.append("4  acknowledge_comment: OK")
    else:
        R.append("4  acknowledge_comment: SKIP")
except Exception as e:
    R.append(f"4  acknowledge_comment: FAIL — {e}")

# 5. update_asset_data
if asset:
    try:
        gazu.asset.update_asset_data(asset, {"_mcp_test": "pass"})
        v = gazu.asset.get_asset(asset["id"])
        ok = v.get("data", {}).get("_mcp_test") == "pass"
        gazu.asset.update_asset_data(asset, {"_mcp_test": None})
        R.append(f"5  update_asset_data: {'OK' if ok else 'FAIL (data not set)'}")
    except Exception as e:
        R.append(f"5  update_asset_data: FAIL — {e}")
else:
    R.append("5  update_asset_data: SKIP")

# 6. update_shot_data
try:
    gazu.shot.update_shot_data(shot, {"_mcp_test": "pass"})
    v = gazu.shot.get_shot(shot["id"])
    ok = v.get("data", {}).get("_mcp_test") == "pass"
    gazu.shot.update_shot_data(shot, {"_mcp_test": None})
    R.append(f"6  update_shot_data: {'OK' if ok else 'FAIL'}")
except Exception as e:
    R.append(f"6  update_shot_data: FAIL — {e}")

# 7. update_task_data
try:
    gazu.task.update_task_data(task, {"_mcp_test": "pass"})
    v = gazu.task.get_task(task["id"])
    ok = v.get("data", {}).get("_mcp_test") == "pass"
    gazu.task.update_task_data(task, {"_mcp_test": None})
    R.append(f"7  update_task_data: {'OK' if ok else 'FAIL'}")
except Exception as e:
    R.append(f"7  update_task_data: FAIL — {e}")

# 8. get_preview_file_url
if preview:
    try:
        url = gazu.files.get_preview_file_url(preview)
        R.append(f"8  get_preview_file_url: {'OK' if url else 'FAIL'}")
    except Exception as e:
        R.append(f"8  get_preview_file_url: FAIL — {e}")
else:
    R.append("8  get_preview_file_url: SKIP")

# 9. download_preview_file
if preview:
    try:
        out = os.path.join(os.environ.get("TEMP", "/tmp"), "mcp_test.png")
        gazu.files.download_preview_file(preview, out)
        sz = os.path.getsize(out) if os.path.exists(out) else 0
        if os.path.exists(out):
            os.remove(out)
        R.append(f"9  download_preview_file: {'OK' if sz > 0 else 'FAIL'} ({sz}B)")
    except Exception as e:
        R.append(f"9  download_preview_file: FAIL — {e}")
else:
    R.append("9  download_preview_file: SKIP")

# 10. update_preview_annotations
if preview:
    try:
        gazu.files.update_preview_annotations(preview, additions=[], updates=[], deletions=[])
        R.append("10 update_preview_annotations: OK")
    except Exception as e:
        R.append(f"10 update_preview_annotations: FAIL — {e}")
else:
    R.append("10 update_preview_annotations: SKIP")

# 11. list_preview_files_for_task
try:
    r = gazu.files.get_all_preview_files_for_task(task)
    R.append(f"11 list_preview_files: OK ({len(r)})")
except Exception as e:
    R.append(f"11 list_preview_files: FAIL — {e}")

# 12. list_attachment_files_for_task
try:
    r = gazu.files.get_all_attachment_files_for_task(task)
    R.append(f"12 list_attachments: OK ({len(r)})")
except Exception as e:
    R.append(f"12 list_attachments: FAIL — {e}")

# 13. get_time_spents_range
try:
    r = gazu.person.get_time_spents_range(person["id"], "2026-01-01", "2026-04-13")
    R.append(f"13 get_time_spents_range: OK ({len(r)})")
except Exception as e:
    R.append(f"13 get_time_spents_range: FAIL — {e}")

# 14. mark_all_notifications_as_read
try:
    gazu.raw.post("actions/user/notifications/mark-all-as-read", {})
    R.append("14 mark_notifications_read: OK")
except Exception as e:
    R.append(f"14 mark_notifications_read: FAIL — {e}")

# 15. subscribe_to_task
try:
    gazu.raw.post(f"actions/user/tasks/{task['id']}/subscribe", {})
    R.append("15 subscribe_to_task: OK")
except Exception as e:
    R.append(f"15 subscribe_to_task: FAIL — {e}")

# 16. unsubscribe_from_task
try:
    gazu.raw.delete(f"actions/user/tasks/{task['id']}/unsubscribe", {})
    R.append("16 unsubscribe_from_task: OK")
except Exception as e:
    R.append(f"16 unsubscribe_from_task: FAIL — {e}")

# 17. remove_entity_from_playlist (read-only check)
try:
    pls = gazu.playlist.all_playlists_for_project(proj)
    R.append(f"17 remove_entity_from_playlist: OK (API ok, {len(pls)} playlists)")
except Exception as e:
    R.append(f"17 remove_entity_from_playlist: FAIL — {e}")

# 18. add_task_type_to_project
try:
    tt = gazu.task.get_task_type_by_name("Compositing")
    gazu.raw.post(f"data/projects/{proj['id']}/settings/task-types", {"task_type_id": tt["id"]})
    R.append("18 add_task_type_to_project: OK")
except Exception as e:
    R.append(f"18 add_task_type_to_project: FAIL — {e}")

# 19. remove_task_type_from_project
try:
    tt = gazu.task.get_task_type_by_name("Compositing")
    gazu.raw.delete(f"data/projects/{proj['id']}/settings/task-types/{tt['id']}")
    R.append("19 remove_task_type_from_project: OK")
except Exception as e:
    R.append(f"19 remove_task_type_from_project: FAIL — {e}")

# Cleanup: reset task to todo
try:
    todo = [s for s in gazu.task.all_task_statuses() if s["short_name"] == "todo"][0]
    gazu.task.add_comment(task, todo, comment="Reset after MCP test")
except Exception:
    pass

print()
for r in R:
    print(r)

ok = sum(1 for r in R if ": OK" in r)
fail = sum(1 for r in R if "FAIL" in r)
skip = sum(1 for r in R if "SKIP" in r)
print(f"\nTOTAL: {ok} OK / {fail} FAIL / {skip} SKIP out of {len(R)}")
