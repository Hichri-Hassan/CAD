"""Dark theme CSS for the evaluation dashboard."""

DARK_THEME_CSS = """
<style>
:root {
  --bg: #0f1117;
  --panel: #171a21;
  --panel-2: #1f2430;
  --border: #2a3142;
  --text: #e6e9ef;
  --muted: #9aa4b2;
  --accent: #6ea8fe;
  --good: #3ddc97;
  --warn: #ffcc66;
  --bad: #ff6b6b;
  --extra: rgba(255, 107, 107, 0.18);
  --missing: rgba(255, 204, 102, 0.18);
}

.stApp {
  background: var(--bg);
  color: var(--text);
}

.block-container {
  padding-top: 1rem;
  max-width: 100%;
}

section[data-testid="stSidebar"] {
  background: var(--panel);
  border-right: 1px solid var(--border);
}

.eval-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.75rem 1rem;
  margin-bottom: 0.5rem;
}

.eval-card.selected {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent);
}

.eval-card:hover {
  border-color: #4f5d75;
  cursor: pointer;
}

.metric-pill {
  display: inline-block;
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
  font-size: 0.75rem;
  margin-right: 0.25rem;
  border: 1px solid var(--border);
}

.metric-pill.good { color: var(--good); border-color: rgba(61, 220, 151, 0.35); }
.metric-pill.bad { color: var(--bad); border-color: rgba(255, 107, 107, 0.35); }
.metric-pill.warn { color: var(--warn); border-color: rgba(255, 204, 102, 0.35); }

.json-panel {
  background: var(--panel-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.5rem;
  max-height: 420px;
  overflow: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.78rem;
}

.diff-missing, .diff-extra {
  display: block;
  border-radius: 4px;
  padding: 0 2px;
}
.diff-missing { background: var(--missing); }
.diff-extra { background: var(--extra); }

.error-chip {
  display: inline-block;
  background: #2a1f24;
  color: #ffb4b4;
  border: 1px solid #5a3038;
  border-radius: 999px;
  padding: 0.15rem 0.55rem;
  margin: 0.15rem 0.25rem 0.15rem 0;
  font-size: 0.78rem;
}

kbd {
  background: #2b3140;
  border: 1px solid #4a5568;
  border-radius: 4px;
  padding: 0.05rem 0.35rem;
  font-size: 0.75rem;
}

h1, h2, h3, h4 { color: var(--text) !important; }
</style>
"""
