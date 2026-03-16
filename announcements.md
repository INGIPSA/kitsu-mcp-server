# Kitsu MCP Server — Announcements

## 1. Reddit r/ClaudeAI

**Title:** I built an MCP server for Kitsu — manage your animation/VFX/game production from Claude

**Body:**

Hey everyone,

I run a small game trailer studio and we use Kitsu (open-source production tracker by CGWire) to manage our pipeline. I got tired of switching between Claude and Kitsu, so I built an MCP server that connects them.

**What it does:**
- List and create projects, assets, shots, sequences, episodes
- Manage tasks — create, assign, update status, set estimates
- Add comments, check casting/breakdown, search across everything
- 30 tools total, covering the full production pipeline

**Tech:** Python + FastMCP + Gazu (Kitsu's Python client). Runs via stdio.

**Setup:** Clone, pip install, set 3 env vars (KITSU_HOST, KITSU_USER, KITSU_PASSWORD), done.

GitHub: https://github.com/INGIPSA/kitsu-mcp-server

It's MIT licensed and works with any Kitsu instance. If you work in animation, VFX, or gamedev and use Kitsu — give it a try and let me know what tools you'd want added.

---

## 2. Reddit r/vfx and r/gamedev

**Title:** Open-source MCP server for Kitsu — manage your production pipeline with AI

**Body:**

I built an open-source tool that connects AI assistants (Claude, etc.) to Kitsu production management.

Instead of clicking through the Kitsu UI, you can now say things like:
- "Create 10 shots in sequence SQ01"
- "Assign all lighting tasks to anna@studio.com"
- "What's the status of all assets in the project?"
- "Add a comment to the animation task on SH030"

It uses the Model Context Protocol (MCP) — an open standard by Anthropic that lets AI tools talk to external services.

30 tools covering projects, assets, shots, tasks, comments, casting, and team management.

GitHub: https://github.com/INGIPSA/kitsu-mcp-server

MIT licensed, works with any Kitsu instance. Would love feedback from other pipeline TDs and production folks.

---

## 3. LinkedIn

I just open-sourced my first MCP server — and it connects AI to production management in animation, VFX, and game studios.

If your studio uses Kitsu (the open-source production tracker by CGWire), you can now manage your entire pipeline through Claude or any MCP-compatible AI assistant.

What it does:
→ Create and manage projects, assets, shots, sequences
→ Assign tasks, update statuses, set estimates
→ Add comments, manage casting/breakdown
→ Search across your entire production
→ 30 tools total

Why I built it:
I run Tato Studio — we make game trailers in Unreal Engine 5. We use Kitsu for production tracking and Claude for everything else. Switching between them was slowing us down, so I built a bridge.

The result: natural language production management. "Create 10 shots in sequence SQ01" just works.

Open-source, MIT licensed, works with any Kitsu instance.

GitHub: https://github.com/INGIPSA/kitsu-mcp-server

If you work in production management, pipeline, or tech art — I'd love your feedback. What tools would you want added?

#MCP #AI #VFX #GameDev #Animation #ProductionManagement #OpenSource #Kitsu #CGWire

---

## 4. Kitsu Discord (CGWire)

Hey everyone! 👋

I built an open-source MCP server that connects AI assistants (like Claude) to Kitsu.

It uses the Gazu Python client under the hood and exposes 30 tools via the Model Context Protocol — so you can manage projects, assets, shots, tasks, comments, and casting through natural language.

Examples:
- "List all open projects"
- "Create a shot SH010 in sequence SQ01"
- "Assign the animation task to john@studio.com"
- "What tasks are assigned to me?"

Setup is simple: clone, pip install, set KITSU_HOST + credentials, done.

GitHub: https://github.com/INGIPSA/kitsu-mcp-server

MIT licensed. Feedback and PRs welcome!

---

## 5. awesome-mcp-servers PR

**File to edit:** README.md in https://github.com/punkpeye/awesome-mcp-servers

**Add under appropriate category (e.g. "Productivity" or "Project Management"):**

- [Kitsu MCP Server](https://github.com/INGIPSA/kitsu-mcp-server) - Manage animation/VFX/game production in Kitsu — projects, assets, shots, tasks, comments, and casting via the Gazu API.

---

## 6. MCP Registry (official)

To publish to the official MCP Registry (modelcontextprotocol.io):

1. Install mcp-publisher CLI: download from https://github.com/modelcontextprotocol/registry
2. Run: mcp-publisher init (generates server.json)
3. Run: mcp-publisher login (GitHub auth)
4. Run: mcp-publisher publish

The mcpName should be: io.github.INGIPSA/kitsu-mcp-server
