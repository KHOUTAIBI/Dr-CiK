#!/usr/bin/env python3
"""Build the public Dr-CiK project page and static development-task explorer.

Run from the repository root with: python3 scripts/build_project_site.py
Content lives in docs/data; public authors and links live in
docs/static/data/project.json. Existing showcase URLs remain available.
"""

from __future__ import annotations

import html
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "docs"
PROJECT = json.loads((ROOT / "static/data/project.json").read_text())
DATA_ROOT = ROOT / "data"
TASK_ROOT = ROOT / "tasks"
INDEX_PATH = DATA_ROOT / "index.json"
ANNOTATIONS_PATH = DATA_ROOT / "task_annotations.json"
LEADERBOARD_PATH = DATA_ROOT / "leaderboard.json"
BENCHMARK_STATS_PATH = DATA_ROOT / "benchmark_stats.json"
FORECASTS_PATH = DATA_ROOT / "task_forecasts.json"
EVIDENCE_PATH = DATA_ROOT / "task_evidence.json"
ASSET_VERSION = "20261002-public-v1"

DIFFICULTY_FIELDS = (
    ("certainty", "Certainty"),
    ("explicitness", "Explicitness"),
    ("domainKnowledge", "Domain knowledge"),
    ("temporalComplexity", "Temporal complexity"),
)


def has_complete_difficulty_labels(annotation: dict) -> bool:
    """Return whether a task has the complete public Figure 2 label set."""
    if annotation.get("status") != "completed":
        return False
    difficulty = annotation.get("difficulty")
    return isinstance(difficulty, dict) and all(
        str(difficulty.get(key) or "").strip() for key, _label in DIFFICULTY_FIELDS
    )


def esc(value: object, fallback: str = "") -> str:
    if value is None or value == "":
        value = fallback
    return html.escape(str(value), quote=True)


def pretty_number(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return esc(value, "—")
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.1f}"


def domain_markup(annotation: dict) -> str:
    domain = annotation.get("domain") or "Domain not assigned"
    return f'<span class="domain-chip"><span class="domain-chip-label">Domain</span>{esc(domain)}</span>'


def annotation_status_markup(annotation: dict) -> str:
    status = annotation.get("status")
    if status == "completed":
        return '<span class="annotation-status complete">Figure 2 labels</span>'
    if status == "not_applicable":
        return '<span class="annotation-status not-applicable">Not applicable</span>'
    return '<span class="annotation-status missing">Not annotated in release</span>'


def annotation_markup(annotation: dict, compact: bool = False) -> str:
    difficulty = annotation.get("difficulty", {})
    not_applicable = annotation.get("status") == "not_applicable"
    classes = "task-annotation-grid compact" if compact else "task-annotation-grid"
    chips = []
    for key, label in DIFFICULTY_FIELDS:
        value = difficulty.get(key) or ("Not applicable" if not_applicable else "Not annotated")
        missing = " not-applicable" if value == "Not applicable" else " missing" if value == "Not annotated" else ""
        chips.append(
            f'<span class="task-annotation-chip{missing}">'
            f'<span class="task-annotation-label">{esc(label)}</span>'
            f'<span class="task-annotation-value">{esc(value)}</span></span>'
        )
    return f'<div class="{classes}" aria-label="Figure 2 diagnostic labels">{"".join(chips)}</div>'


def annotation_panel(annotation: dict) -> str:
    return f'''<section class="detail-annotation-panel" aria-labelledby="annotation-title">
            <div class="detail-annotation-head"><div><div class="eyebrow">Figure 2 diagnostic taxonomy</div><h3 id="annotation-title">Task difficulty profile</h3></div>{annotation_status_markup(annotation)}</div>
            <p>These four labels are independent diagnostic axes—not a single aggregate difficulty score. They describe the evidence and reasoning demands associated with this forecasting task.</p>
            <div class="detail-annotation-domain">{domain_markup(annotation)}</div>
            {annotation_markup(annotation)}
          </section>'''


def annotation_guide() -> str:
    return '''<div class="annotation-guide" id="task-metadata">
          <div class="annotation-guide-head"><div><div class="eyebrow">Task-level metadata</div><h3>Read each task through the paper’s taxonomy.</h3></div><a href="data/task_annotations.json">Open machine-readable labels <span aria-hidden="true">→</span></a></div>
          <p>Each listed task reports its Figure 2 domain and four independent diagnostic axes. The public task library includes only tasks with a complete released label set.</p>
          <div class="annotation-guide-grid"><span><strong>Certainty</strong><small>Certain · Likely · Uncertain</small></span><span><strong>Explicitness</strong><small>Explicit · Implied · Implicit</small></span><span><strong>Domain knowledge</strong><small>General · Specialist</small></span><span><strong>Temporal complexity</strong><small>Predictable · Straightforward · Variable</small></span></div>
        </div>'''


def downsample(values: list[object], limit: int) -> list[float]:
    numeric = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            numeric.append(number)
    if len(numeric) <= limit:
        return numeric
    return [numeric[round(index * (len(numeric) - 1) / (limit - 1))] for index in range(limit)]


def chart_svg(values: list[object], boundary: int, width: int, height: int, label: str) -> str:
    numeric = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            numeric.append(number)
    if len(numeric) < 2:
        return ""

    minimum = min(numeric)
    maximum = max(numeric)
    spread = maximum - minimum or 1.0
    pad_x = 12 if width > 700 else 5
    pad_y = 14 if width > 700 else 8

    def x(index: int) -> float:
        return pad_x + (index / (len(numeric) - 1)) * (width - pad_x * 2)

    def y(value: float) -> float:
        return height - pad_y - ((value - minimum) / spread) * (height - pad_y * 2)

    def point_string(start: int, end: int) -> str:
        return " ".join(
            f"{x(start + offset):.2f},{y(value):.2f}"
            for offset, value in enumerate(numeric[start:end])
        )

    boundary = max(0, min(len(numeric) - 1, int(boundary)))
    history = point_string(0, min(boundary + 1, len(numeric)))
    future = point_string(boundary, len(numeric))
    boundary_x = x(boundary)
    grid = "".join(
        f'<line class="chart-gridline" x1="{pad_x}" y1="{height * ratio:.2f}" '
        f'x2="{width - pad_x}" y2="{height * ratio:.2f}" />'
        for ratio in (0.22, 0.52, 0.82)
    )
    return (
        f'<svg class="static-chart" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{esc(label)}" preserveAspectRatio="none">'
        f'{grid}<line class="chart-boundary" x1="{boundary_x:.2f}" y1="{pad_y}" '
        f'x2="{boundary_x:.2f}" y2="{height - pad_y}" />'
        f'<polyline class="chart-history" points="{history}" />'
        f'<polyline class="chart-future" points="{future}" />'
        "</svg>"
    )



def project_head(active: str = "") -> str:
    prefix = "../" if active == "task" else ""
    return f'''
    <meta property="og:title" content="{esc(PROJECT['title'])}" />
    <meta property="og:description" content="Dr-CiK: a 279-task benchmark for context-aided forecasting via deep research, by ServiceNow Research." />
    <meta property="og:type" content="website" />
    <meta property="og:url" content="{PROJECT['links']['project']}" />
    <link rel="icon" type="image/svg+xml" href="{prefix}static/assets/servicenow-mark.svg" />
    <link rel="stylesheet" href="{prefix}static/css/public.css?v={ASSET_VERSION}" />'''


def project_identity() -> str:
    author_markup = []
    for author in PROJECT["authors"]:
        name = esc(author["name"])
        if author.get("email"):
            name = f'<a href="mailto:{esc(author["email"])}">{name}</a>'
        else:
            name = f'<span>{name}</span>'
        labels = ",".join(str(number) for number in author["affiliations"])
        if author.get("corresponding"):
            labels += ",✉"
        author_markup.append(f'{name}<sup>{labels}</sup>')
    institutions = " · ".join(f'<span><sup>{item["id"]}</sup>{esc(item["name"])}</span>' for item in PROJECT["affiliations"])
    correspondents = " and ".join(esc(author["name"]) for author in PROJECT["authors"] if author.get("corresponding"))
    return f'''<div class="wrap project-identity">
      <p class="project-paper-title">{esc(PROJECT['title'])}</p>
      <p class="project-authors">{', '.join(author_markup)}</p>
      <p class="project-affiliations">{institutions}</p>
      <p class="project-correspondence"><span>✉ Corresponding author</span> · {correspondents}</p>
    </div>'''


def project_actions() -> str:
    links = PROJECT["links"]
    return f'''<div class="hero-actions">
      <a class="button button-primary" href="{links['paper']}" target="_blank" rel="noopener noreferrer">Paper ↗</a>
      <a class="button button-ghost" href="{links['dataset']}" target="_blank" rel="noopener noreferrer">Dataset ↗</a>
      <a class="button button-ghost" href="{links['repository']}" target="_blank" rel="noopener noreferrer">Code ↗</a>
      <a class="button button-ghost" href="#leaderboard">Results</a>
    </div>'''


def release_section() -> str:
    links = PROJECT["links"]
    return f'''<section class="section project-release" id="release"><div class="wrap">
      <div class="section-heading"><div><div class="eyebrow">Use Dr-CiK</div><h2>Research, evaluate, and contribute.</h2></div>
        <p>The release contains 199 public development tasks and 80 expert-curated hidden-test tasks. The results above are experimental reference results; official submissions are scored on the hidden test set by the maintainers.</p></div>
      <div class="project-resource-grid">
        <a class="project-resource" href="{links['dataset']}" target="_blank" rel="noopener noreferrer"><span class="eyebrow">Hugging Face</span><h3>Get the dataset ↗</h3><p>Load all 279 tasks, 10,342 documents, and task–document links. Development labels are public; hidden-test answers are withheld.</p></a>
        <a class="project-resource" href="{links['submission']}" target="_blank" rel="noopener noreferrer"><span class="eyebrow">Official evaluation</span><h3>Submit your forecasts ↗</h3><p>Follow the submission guide to have your outputs scored on the 80-task hidden test set.</p></a>
        <a class="project-resource" href="showcase/index.html"><span class="eyebrow">Interactive showcase</span><h3>Explore featured examples →</h3><p>Browse the original task showcase alongside the expanded development-task library below.</p></a>
      </div>
    </div></section>'''


def citation_section() -> str:
    citation_authors = []
    for author in PROJECT["authors"]:
        given, family = author["name"].rsplit(" ", 1)
        citation_authors.append(f"{family}, {given}")
    citation = "@article{tang2026dr,\n  title={" + PROJECT["title"] + "},\n  author={" + " and ".join(citation_authors) + "},\n  journal={arXiv preprint arXiv:2605.27904},\n  year={2026},\n  url={" + PROJECT["links"]["paper"] + "}\n}"
    return f'''<section class="section project-citation" id="cite"><div class="wrap">
      <div class="section-heading"><div><div class="eyebrow">Citation</div><h2>Cite Dr-CiK</h2></div><p>If Dr-CiK supports your research, please cite the paper.</p></div>
      <div class="project-cite-card"><div class="project-cite-head"><span>BibTeX</span><button class="button" id="copy-cite" type="button">Copy citation</button></div><pre id="cite-text">{esc(citation)}</pre></div>
    </div></section>'''


def citation_script() -> str:
    return '''<script>
    (function () {
      var button = document.getElementById("copy-cite");
      if (!button) return;
      button.addEventListener("click", async function () {
        var citation = document.getElementById("cite-text");
        try {
          await navigator.clipboard.writeText(citation.textContent);
          button.textContent = "Copied!";
          window.setTimeout(function () { button.textContent = "Copy citation"; }, 1600);
        } catch (_) {
          var range = document.createRange();
          range.selectNodeContents(citation);
          window.getSelection().removeAllRanges();
          window.getSelection().addRange(range);
          button.textContent = "Citation selected";
        }
      });
    })();
    </script>'''


def brand_header(active: str = "") -> str:
    prefix = "../" if active == "task" else ""
    return f'''<header class="site-header">
      <div class="wrap nav-shell">
        <a class="brand" href="{prefix}index.html#top" aria-label="Dr-CiK project home"><img class="brand-servicenow" src="{prefix}static/assets/servicenow-mark.svg" alt="" width="30" height="30" /><span>Dr-CiK</span></a>
        <nav class="nav-links" aria-label="Primary navigation">
          <a href="{prefix}index.html#pipeline">Pipeline</a><a href="{prefix}index.html#scope">Benchmark</a><a href="{prefix}index.html#leaderboard">Leaderboard</a><a href="{prefix}index.html#explorer">Tasks</a><a href="{prefix}index.html#cite">Cite</a>
        </nav>
        <a class="nav-status" href="{PROJECT['links']['repository']}" target="_blank" rel="noopener noreferrer" aria-label="Open the ServiceNow Dr-CiK GitHub repository in a new tab"><span class="status-dot" aria-hidden="true"></span>GitHub ↗</a>
      </div>
    </header>'''


def footer(active: str = "") -> str:
    prefix = "../" if active == "task" else ""
    links = PROJECT["links"]
    contact_links = " · ".join(f'<a href="mailto:{esc(author["email"])}">{esc(author["name"])}</a>' for author in PROJECT["authors"] if author.get("corresponding") and author.get("email"))
    return f'''<footer class="site-footer">
      <div class="wrap footer-shell">
        <div><a class="footer-servicenow" href="https://www.servicenow.com/" target="_blank" rel="noopener noreferrer"><img src="{prefix}static/assets/servicenow-logo.svg" alt="ServiceNow" width="158" height="24" /></a><p class="footer-copy">© 2026 ServiceNow, Inc. · Dr-CiK is released under <a href="{links['license']}">CC BY 4.0</a>.</p></div>
        <div class="footer-meta"><p><a href="{links['paper']}">Paper</a> · <a href="{links['dataset']}">Dataset</a> · <a href="{links['repository']}">Code</a></p><p>{contact_links}</p></div>
      </div>
    </footer>'''


def homepage_scroll_guard() -> str:
    """Keep browser reloads from restoring the homepage at a section anchor."""
    return '''<script>
(function () {
  var navigation = window.performance && window.performance.getEntriesByType
    ? window.performance.getEntriesByType("navigation")[0]
    : null;
  var isReload = navigation
    ? navigation.type === "reload"
    : !!(window.performance && window.performance.navigation && window.performance.navigation.type === 1);
  if (!isReload) return;

  if ("scrollRestoration" in window.history) {
    window.history.scrollRestoration = "manual";
  }
  if (window.location.hash) {
    window.history.replaceState(null, document.title, window.location.pathname + window.location.search);
  }

  var resetScroll = function () {
    window.scrollTo(0, 0);
    if (window.requestAnimationFrame) {
      window.requestAnimationFrame(function () { window.scrollTo(0, 0); });
    }
  };
  window.addEventListener("pageshow", resetScroll, { once: true });
  window.addEventListener("load", resetScroll, { once: true });
})();
</script>'''


def card(task: dict, annotation: dict) -> str:
    chart = chart_svg(task.get("trace", []), task.get("boundaryIndex", 0), 520, 120, "Forecasting series trace")
    return f'''<a class="task-card task-link" id="task-card-{esc(task["id"])}" href="tasks/{esc(task["id"])}.html">
      <div class="task-taxonomy">{domain_markup(annotation)}{annotation_status_markup(annotation)}</div>
      <h3>{esc(task.get("entity"), "Unnamed entity")}</h3>
      <p class="task-subtitle"><strong>{esc(task.get("target"), "Target series")}</strong> · {esc(task.get("sourceClass"), "Forecasting task")}</p>
      <div class="task-sparkline">{chart}</div>
      {annotation_markup(annotation, compact=True)}
      <div class="task-metrics">
        <div class="task-metric"><span class="task-metric-label">History length</span><span class="task-metric-value">{pretty_number(task.get("historyLength"))}</span></div>
        <div class="task-metric"><span class="task-metric-label">Forecast horizon</span><span class="task-metric-value">{pretty_number(task.get("horizon"))}</span></div>
        <div class="task-metric"><span class="task-metric-label">Evidence docs</span><span class="task-metric-value">{pretty_number(task.get("documentCount"))}</span></div>
      </div>
      <span class="inspect-button">Open full task <span aria-hidden="true">→</span></span>
    </a>'''


def fact(label: str, value: object) -> str:
    rendered = esc(value, "—")
    return f'<div class="detail-fact"><span class="detail-fact-label">{esc(label)}</span><span class="detail-fact-value" title="{rendered}">{rendered}</span></div>'


def series_table(detail: dict) -> str:
    series = detail.get("series", {})
    history_timestamps = series.get("historyTimestamps", [])
    history_values = series.get("historyValues", [])
    future_timestamps = series.get("futureTimestamps", [])
    future_values = series.get("futureValues", [])
    rows = []
    for index, (timestamp, value) in enumerate(zip(history_timestamps, history_values), start=1):
        rows.append(f'<tr><td>{index}</td><td>Observed history</td><td>{esc(timestamp)}</td><td>{esc(value)}</td></tr>')
    offset = len(rows)
    for index, (timestamp, value) in enumerate(zip(future_timestamps, future_values), start=1):
        rows.append(f'<tr class="future"><td>{offset + index}</td><td>Forecast horizon</td><td>{esc(timestamp)}</td><td>{esc(value)}</td></tr>')
    return f'''<details class="full-context static-series-details">
      <summary>View all series points ({len(rows)} observations)</summary>
      <div class="series-table-wrap">
        <table class="series-table">
          <thead><tr><th>#</th><th>Segment</th><th>Timestamp</th><th>Value</th></tr></thead>
          <tbody>{"".join(rows)}</tbody>
        </table>
      </div>
    </details>'''


FORECAST_CONTEXTS = (
    ("deepresearch_insights", "DeepResearch Evidence", "Agent-synthesized evidence"),
    ("original_context_raw", "Original Context", "Source context supplied with the task"),
    ("no_context", "No Context", "Time-series history only"),
)

FORECAST_METHOD_ORDER = (
    "aurora",
    "dp_gemini",
    "moiraiagent",
    "chronos",
    "arima",
    "ets",
    "naive",
    "ses",
)

FORECAST_COLORS = {
    "aurora": "#b86d4a",
    "dp_gemini": "#2d6b5c",
    "moiraiagent": "#aa7c32",
    "chronos": "#3777a5",
    "arima": "#8064a2",
    "ets": "#668851",
    "naive": "#aa5d5d",
    "ses": "#8b6e4f",
}




def finite_number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def forecast_domain(history: list[object], actual: list[object], methods: list[tuple[str, dict]]) -> tuple[float, float]:
    values = []
    for value in [*history, *actual]:
        number = finite_number(value)
        if number is not None:
            values.append(number)
    for _key, item in methods:
        mean = item.get("mean", [])
        std = item.get("std", [])
        for index, value in enumerate(mean):
            number = finite_number(value)
            if number is None:
                continue
            spread = finite_number(std[index]) if index < len(std) else 0.0
            spread = max(0.0, spread or 0.0)
            values.extend((number - spread, number + spread))
    if not values:
        return 0.0, 1.0
    minimum = min(values)
    maximum = max(values)
    if minimum == maximum:
        minimum -= 1.0
        maximum += 1.0
    padding = (maximum - minimum) * 0.08
    return minimum - padding, maximum + padding


def forecast_path(values: list[object], start_index: int, x, y) -> str:
    points = []
    for index, value in enumerate(values):
        number = finite_number(value)
        if number is None:
            continue
        command = "M" if not points else "L"
        points.append(f"{command} {x(start_index + index):.2f} {y(number):.2f}")
    return " ".join(points)


def forecast_band(mean: list[object], std: list[object], start_index: int, x, y) -> str:
    upper = []
    lower = []
    for index, value in enumerate(mean):
        number = finite_number(value)
        if number is None:
            continue
        spread = finite_number(std[index]) if index < len(std) else 0.0
        spread = max(0.0, spread or 0.0)
        upper.append(f"{x(start_index + index):.2f} {y(number + spread):.2f}")
        lower.append(f"{x(start_index + index):.2f} {y(number - spread):.2f}")
    if not upper:
        return ""
    return f"M {' L '.join(upper)} L {' L '.join(reversed(lower))} Z"


def forecast_chart_svg(
    history: list[object],
    actual: list[object],
    methods: list[tuple[str, dict]],
    focus: str | None,
    label: str,
    shared_domain: tuple[float, float] | None = None,
    extra_class: str = "",
) -> str:
    total = len(history) + len(actual)
    if total < 2:
        return '<svg class="forecast-chart"><text x="28" y="48" class="forecast-svg-empty">Series values are unavailable.</text></svg>'

    width = 1000
    height = 360
    pad_x = 28
    pad_y = 22
    minimum, maximum = shared_domain or forecast_domain(history, actual, methods)

    def x(index: int) -> float:
        return pad_x + (index / max(1, total - 1)) * (width - pad_x * 2)

    def y(value: float) -> float:
        return height - pad_y - ((value - minimum) / (maximum - minimum)) * (height - pad_y * 2)

    history_path = forecast_path(history, 0, x, y)
    actual_path = forecast_path(actual, len(history), x, y)
    boundary = x(max(0, len(history) - 1))
    grid = "".join(
        f'<line class="forecast-svg-grid" x1="{pad_x}" y1="{height * ratio:.2f}" '
        f'x2="{width - pad_x}" y2="{height * ratio:.2f}" />'
        for ratio in (0.2, 0.5, 0.8)
    )

    band = ""
    if focus:
        focused = next((item for key, item in methods if key == focus), None)
        if focused:
            band_path = forecast_band(focused.get("mean", []), focused.get("std", []), len(history), x, y)
            if band_path:
                color = FORECAST_COLORS.get(focus, "#2d6b5c")
                band = f'<path class="forecast-svg-band" fill="{color}" d="{band_path}" />'

    lines = []
    for key, item in methods:
        mean = item.get("mean", [])
        path = forecast_path(mean, len(history), x, y)
        if not path:
            continue
        color = FORECAST_COLORS.get(key, "#2d6b5c")
        active = " active" if key == focus else ""
        first = finite_number(mean[0]) if mean else None
        marker = ""
        if first is not None:
            marker = (
                f'<circle class="forecast-svg-start" fill="{color}" '
                f'cx="{x(len(history)):.2f}" cy="{y(first):.2f}" r="{4 if key == focus else 3}" />'
            )
        lines.append(f'<path class="forecast-svg-mean{active}" stroke="{color}" d="{path}" />{marker}')

    class_name = f"forecast-chart {extra_class}".strip()
    return (
        f'<svg class="{class_name}" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{esc(label)}" preserveAspectRatio="none">'
        f'<title>{esc(label)}</title>{grid}'
        f'<line class="forecast-svg-boundary" x1="{boundary:.2f}" y1="{pad_y}" '
        f'x2="{boundary:.2f}" y2="{height - pad_y}" />'
        f'<path class="forecast-svg-history" d="{history_path}" />'
        f'<path class="forecast-svg-actual" d="{actual_path}" />'
        f'{band}{"".join(lines)}'
        f'<text class="forecast-svg-label forecast-svg-label-left" x="{pad_x}" y="{height - 5}">observed</text>'
        f'<text class="forecast-svg-label forecast-svg-label-right" x="{width - pad_x}" y="{height - 5}" text-anchor="end">future</text>'
        '</svg>'
    )


def forecast_section(detail: dict, forecast_payload: dict) -> str:
    """Render a static, CSS-switchable forecast comparison surface.

    Static hosting may serve pages with a sandbox CSP that intentionally
    disables JavaScript.  Context and view switching therefore use native
    radio inputs and CSS; the same markup remains fully inspectable offline.
    """
    series = detail.get("series", {})
    contexts = forecast_payload.get("contexts", {}) if isinstance(forecast_payload, dict) else {}
    available = []
    for key, label, description in FORECAST_CONTEXTS:
        methods = contexts.get(key, {})
        if methods:
            ordered = sorted(
                methods.items(),
                key=lambda pair: FORECAST_METHOD_ORDER.index(pair[0]) if pair[0] in FORECAST_METHOD_ORDER else len(FORECAST_METHOD_ORDER),
            )
            available.append((key, label, description, ordered))
    if not available:
        return '''<section class="forecast-surface forecast-unavailable" aria-labelledby="forecast-title">
          <div class="forecast-surface-head"><div><div class="eyebrow">Model forecasts</div><h2 id="forecast-title">Forecast comparison</h2><p>Per-task model forecasts are not available for this task in the public release.</p></div></div>
        </section>'''

    history = downsample(series.get("historyValues", []), 240)
    # Keep the horizon at its native resolution so forecast means/std remain
    # index-aligned even when a later public annotation includes a long horizon.
    actual = series.get("futureValues", [])
    task_token = "".join(character if character.isalnum() else "-" for character in str(detail.get("id") or "task"))
    group = f"forecast-{task_token}"

    def preferred_keys(context: str, methods: list[tuple[str, dict]]) -> list[str]:
        available_keys = {key for key, _item in methods}
        preferred = {
            "deepresearch_insights": ("aurora", "dp_gemini", "moiraiagent"),
            "original_context_raw": ("dp_gemini", "moiraiagent"),
            "no_context": ("chronos", "arima", "ets"),
        }.get(context, ())
        selected = [key for key in preferred if key in available_keys]
        return selected or [key for key, _item in methods[:3]]

    context_inputs = []
    context_tabs = []
    panels = []
    for index, (context, label, description, methods) in enumerate(available):
        context_slug = context.replace("_", "-")
        context_id = f"{group}-context-{context_slug}"
        checked = " checked" if index == 0 else ""
        context_inputs.append(
            f'<input class="forecast-context-input" data-context="{esc(context)}" type="radio" '
            f'name="{esc(group)}-context" id="{esc(context_id)}"{checked} />'
        )
        context_tabs.append(
            f'<label class="forecast-context-tab" data-context="{esc(context)}" for="{esc(context_id)}" title="{esc(description)}">'
            f'{esc(label)}<small>{len(methods)} methods</small></label>'
        )
        selected_keys = preferred_keys(context, methods)
        focus = selected_keys[0] if selected_keys else (methods[0][0] if methods else None)
        selected_methods = [(key, item) for key, item in methods if key in selected_keys]
        overlay = forecast_chart_svg(
            history,
            actual,
            selected_methods,
            focus,
            f"{label} model forecasts",
        )
        shared_domain = forecast_domain(history, actual, methods)
        small_panels = []
        for key, item in methods:
            method_label = item.get("label") or key
            family = item.get("family") or "Forecaster"
            small_panels.append(
                f'''<article class="forecast-small-panel">
                  <div class="forecast-small-head"><div><strong>{esc(method_label)}</strong><small>{esc(family)}</small></div><span>{pretty_number(item.get("sampleCount"))} samples</span></div>
                  {forecast_chart_svg(history, actual, [(key, item)], key, f"{method_label} forecast", shared_domain, "forecast-small-chart")}
                </article>'''
            )
        pills = []
        for key, item in methods:
            method_label = item.get("label") or key
            family = item.get("family") or "Forecaster"
            color_class = f"forecast-model-{key.replace('_', '-')}"
            selected = " selected" if key in selected_keys else ""
            pills.append(
                f'<span class="forecast-model-pill {color_class}{selected}" title="{esc(family)} · {esc(item.get("sampleCount"), "—")} samples per task">'
                f'{esc(method_label)}<small>{esc(family)}</small></span>'
            )
        panels.append(
            f'''<section class="forecast-context-panel" data-context="{esc(context)}" aria-label="{esc(label)}">
              <div class="forecast-model-row">
                <div><span class="forecast-control-label">Forecasters</span><div class="forecast-model-pills">{"".join(pills)}</div></div>
                <span class="forecast-model-hint">Overlay defaults to the highlighted comparison · small multiples shows every available forecaster</span>
              </div>
              <div class="forecast-chart-frame">
                <div class="forecast-chart-heading"><span>{esc(label)} · {len(selected_methods)} selected</span><span>Highlighted · {esc(next((item.get("label") for key, item in methods if key == focus), focus or "—"))} · ±1 SD</span></div>
                {overlay}
                <div class="forecast-chart-caption"><span><i class="forecast-key-history"></i>observed history</span><span><i class="forecast-key-actual"></i>actual future</span><span><i class="forecast-key-mean"></i>forecast mean</span><span><i class="forecast-key-band"></i>sample spread</span></div>
              </div>
              <div class="forecast-multiples">
                <div class="forecast-chart-heading"><span>{esc(label)} · {len(methods)} available</span><span>Shared scale · mean ± 1 SD</span></div>
                <div class="forecast-small-grid">{"".join(small_panels)}</div>
              </div>
            </section>'''
        )

    view_overlay_id = f"{group}-view-overlay"
    view_multiples_id = f"{group}-view-multiples"
    return f'''<section class="forecast-surface" aria-labelledby="forecast-title">
          <div class="forecast-surface-head">
            <div>
              <div class="eyebrow">Model forecasts</div>
              <h2 id="forecast-title">Compare the forecast horizon.</h2>
              <p>Keep the context fixed, then inspect how different forecasters trace the same future. The shaded band is the spread across sampled forecasts.</p>
            </div>
            <div class="forecast-surface-mark" aria-hidden="true"><span></span><span></span><span></span></div>
          </div>
          {"".join(context_inputs)}
          <input class="forecast-view-input" value="overlay" type="radio" name="{esc(group)}-view" id="{esc(view_overlay_id)}" checked />
          <input class="forecast-view-input" value="multiples" type="radio" name="{esc(group)}-view" id="{esc(view_multiples_id)}" />
          <div class="forecast-toolbar">
            <div class="forecast-control-block">
              <span class="forecast-control-label">Context</span>
              <div class="forecast-context-tabs" role="tablist" aria-label="Forecast context">{"".join(context_tabs)}</div>
            </div>
            <div class="forecast-control-block forecast-view-block">
              <span class="forecast-control-label">View</span>
              <div class="forecast-view-tabs" role="group" aria-label="Forecast view">
                <label class="forecast-view-tab" for="{esc(view_overlay_id)}">Overlay</label>
                <label class="forecast-view-tab" for="{esc(view_multiples_id)}">Small multiples</label>
              </div>
            </div>
          </div>
          <div class="forecast-context-panels">{"".join(panels)}</div>
          <div class="forecast-surface-foot"><span>Point forecast = sample mean · spread computed over recorded samples</span><span>Use the controls above to switch context and view</span></div>
        </section>'''


def document_markup(documents: list[dict]) -> str:
    distractor_type_names = {
        "noisy": "Irrelevant",
        "confounder": "Off-variable",
        "profile": "Off-entity",
        "temporal": "Off-window",
        "timeseries": "Counterfactual history",
    }
    items = []
    for document in documents:
        role = str(document.get("role") or "document").lower()
        role_label = "Distractor" if role == "distractor" else "Supporting"
        role_class = "distractor" if role == "distractor" else ""
        raw_subtype = str(document.get("subtype") or "")
        subtype_label = distractor_type_names.get(raw_subtype.lower().replace("-", "").replace("_", ""), raw_subtype)
        subtype = f' · {esc(subtype_label)}' if subtype_label else ""
        items.append(f'''<details class="doc-item">
          <summary><span class="doc-meta"><span class="doc-role {role_class}">{role_label}</span><span>{esc(document.get("id"), "Document")}{subtype}</span></span></summary>
          <pre class="doc-content">{esc(document.get("content"), "No document content.")}</pre>
        </details>''')
    return "".join(items) if items else '<p class="no-docs">No documents are attached to this task.</p>'


def paper_task_documents(documents: list[dict]) -> list[dict]:
    """Keep the paper's five distractor types at five documents per type."""
    distractor_type_names = {
        "noisy": "irrelevant",
        "confounder": "offvariable",
        "profile": "offentity",
        "temporal": "offwindow",
        "timeseries": "counterfactualhistory",
    }
    seen: dict[str, int] = {}
    selected = []
    for document in documents:
        if str(document.get("role") or "").lower() != "distractor":
            selected.append(document)
            continue
        subtype = str(document.get("subtype") or "").lower().replace("-", "").replace("_", "")
        subtype = distractor_type_names.get(subtype, subtype)
        if seen.get(subtype, 0) >= 5:
            continue
        seen[subtype] = seen.get(subtype, 0) + 1
        selected.append(document)
    return selected


def gt_evidence_markup(evidence: list[dict]) -> str:
    if not evidence:
        return '<p class="no-evidence">No ground-truth supporting evidence is available for this task.</p>'
    items = []
    for index, item in enumerate(evidence, start=1):
        evidence_id = item.get("id") or f"E{index}"
        evidence_text = item.get("evidence") or item.get("text")
        items.append(f'''<article class="gt-evidence-item">
          <div class="gt-evidence-item-head"><span class="gt-evidence-label">Ground-truth supporting evidence</span><span class="gt-evidence-id">{esc(evidence_id)}</span></div>
          <p>{esc(evidence_text, "No evidence text.")}</p>
        </article>''')
    return f'<div class="gt-evidence-list">{"".join(items)}</div>'


def detail_page(detail: dict, annotation: dict, gt_evidence: list[dict], forecast_payload: dict | None = None) -> str:
    entity = detail.get("entity", {})
    metadata = detail.get("metadata", {})
    context = detail.get("context", {})
    summary = detail.get("seriesSummary", {})
    documents = detail.get("documents", [])
    history = downsample(detail.get("series", {}).get("historyValues", []), 140)
    future = downsample(detail.get("series", {}).get("futureValues", []), 100)
    chart = chart_svg(history + future, len(history), 980, 290, "Observed history and forecast horizon")
    history_start = summary.get("historyStart") or detail.get("series", {}).get("historyTimestamps", [""])[0]
    future_end = summary.get("futureEnd") or detail.get("series", {}).get("futureTimestamps", [""])[-1]
    background = context.get("background") or metadata.get("targetDescription")
    constraints = context.get("constraints")
    return f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#032d42" />
    <meta name="description" content="Inspectable forecasting task from the task library." />
    <title>{esc(entity.get("name"), "Forecasting task")} · Context-Aided Forecasting via Deep Research</title>
    <link rel="stylesheet" href="../styles.css?v={ASSET_VERSION}" />
{project_head("task")}
  </head>
  <body>
    {brand_header("task")}
    <main class="static-detail-page">
      <div class="static-detail-shell">
        <a class="back-link" href="../index.html#explorer">← Back to the task library</a>
        <header class="static-detail-header">
          <h1>{esc(entity.get("name"), "Unnamed entity")}</h1>
          <p>Forecasting <strong>{esc(detail.get("target"), "target series")}</strong> · {esc(detail.get("sourceClass"), "Forecasting task")}</p>
        </header>
        <div class="static-detail-body">
          <div class="detail-facts">
            {fact("Domain", annotation.get("domain"))}
            {fact("Frequency", metadata.get("frequency"))}
            {fact("Forecast horizon", metadata.get("predictionLength"))}
            {fact("History length", summary.get("historyLength"))}
            {fact("Evidence documents", len(documents))}
          </div>
          {annotation_panel(annotation)}
          <div class="detail-chart-wrap">
            <div class="detail-chart-label"><span>Observed history · {esc(history_start)}</span><span>Forecast horizon · through {esc(future_end)}</span></div>
            {chart}
            <div class="composition-legend"><span class="legend-item"><span class="legend-swatch core"></span>observed history</span><span class="legend-item"><span class="legend-swatch new"></span>forecast horizon</span></div>
          </div>
          {series_table(detail)}
          {forecast_section(detail, forecast_payload or {})}
          <div class="detail-columns">
            <section class="detail-panel">
              <div class="eyebrow">Forecasting task</div>
              <h3>{esc(detail.get("target"), "Target series")}</h3>
              <p>{esc(background, "No background description is available.")}</p>
              <p class="instruction">{esc(context.get("instruction"), "No forecast instruction is available.")}</p>
              {f'<p><strong>Constraints:</strong> {esc(constraints)}</p>' if constraints else ''}
              <details class="full-context"><summary>View GT evidence</summary>{gt_evidence_markup(gt_evidence)}</details>
            </section>
            <section class="detail-panel">
              <div class="documents-head"><div><div class="eyebrow">Evidence corpus</div><h3>Supporting and distractor documents</h3></div><span class="documents-count">{len(documents)} documents</span></div>
              <div class="doc-list">{document_markup(documents)}</div>
            </section>
          </div>
          <a class="static-footer-link" href="../index.html#explorer">Return to the task library explorer →</a>
        </div>
      </div>
    </main>
    {footer("task")}
  </body>
</html>'''


RESULT_METRICS = (
    ("scrps", "sCRPS"),
    ("smae", "sMAE"),
    ("srmse", "sRMSE"),
)

RESULT_CONTEXTS = (
    ("no_context", "No Context", "History and forecast horizon only."),
    ("original_context_raw", "Original Context", "History paired with the original task context."),
    ("deepresearch_insights", "DeepResearch Insights", "History paired with agent-produced research context."),
)

FULL_EVALUABLE_TASKS = 273
FULL_BENCHMARK_TASKS = 279
FULL_EVALUABLE_METRICS = ("smae", "srmse", "scrps")


def normalize_leaderboard(leaderboard: dict) -> dict:
    """Prepare the two public leaderboard views from the reported exports.

    The benchmark inventory contains 279 tasks, but six very long-horizon
    cases cannot produce a reliable forecast under the released verbose
    output protocol.  The full-benchmark view displays the benchmark's total
    task count while retaining the reported evaluable counts for row selection.
    Rows with additional model-specific failures stay out of that view.
    """
    protocols = leaderboard.get("protocols", {})
    full = protocols.get("full")
    if not isinstance(full, dict):
        return leaderboard

    complete_rows = []
    for row in full.get("rows", []):
        valid = row.get("valid") or {}
        if not all(valid.get(metric) == FULL_EVALUABLE_TASKS for metric in FULL_EVALUABLE_METRICS):
            continue
        normalized = dict(row)
        normalized_valid = dict(valid)
        normalized.update(
            {
                "target": FULL_EVALUABLE_TASKS,
                "records": FULL_EVALUABLE_TASKS,
                "completed": FULL_EVALUABLE_TASKS,
                "failed": 0,
                "status": "ranked",
                "statusLabel": "Complete",
                "statusDetail": "",
                "eligible": True,
                "rank": None,
                "valid": normalized_valid,
            }
        )
        complete_rows.append(normalized)

    full.update(
        {
            "scopeLabel": f"{FULL_BENCHMARK_TASKS}-task benchmark scope",
            "targetTasks": FULL_BENCHMARK_TASKS,
            "benchmarkTasks": FULL_BENCHMARK_TASKS,
            "excludedTaskCount": FULL_BENCHMARK_TASKS - FULL_EVALUABLE_TASKS,
            "excludedTaskReason": "Six very long-horizon tasks are retained in the benchmark inventory but excluded from metric aggregation because the current verbose forecast-output protocol cannot represent them reliably.",
            "title": "Full benchmark leaderboard",
            "description": "",
            "statusLabel": "Complete scope",
            "statusDetail": f"{len(complete_rows)} model · context combinations in the {FULL_BENCHMARK_TASKS}-task benchmark.",
            "rows": complete_rows,
        }
    )
    metric_policy = leaderboard.get("metricPolicy")
    if isinstance(metric_policy, dict):
        metric_policy["note"] = f"Scaled error metrics use the current clipped analysis export with a per-task cap of 5. The full view reports results for the {FULL_BENCHMARK_TASKS}-task benchmark; the common view uses one shared task mask."
    return leaderboard


def result_metric_markup(row: dict, key: str) -> str:
    metric = (row.get("metrics") or {}).get(key) or {}
    return esc(metric.get("display"), "—")


def leaderboard_metric_scales(leaderboard: dict) -> dict[str, float]:
    """Use one shared, metric-specific visual scale across both views."""
    scales = {}
    for key, _label in RESULT_METRICS:
        values = []
        for protocol in (leaderboard.get("protocols") or {}).values():
            for row in protocol.get("rows", []):
                try:
                    value = float((((row.get("metrics") or {}).get(key) or {}).get("mean")))
                except (TypeError, ValueError):
                    continue
                if math.isfinite(value) and value >= 0:
                    values.append(value)
        scales[key] = max(values) if values else 1.0
    return scales


def metric_bar_score(row: dict, key: str, scales: dict[str, float]) -> float:
    try:
        current = float((((row.get("metrics") or {}).get(key) or {}).get("mean")))
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(current):
        return 0.0
    scale = scales.get(key, 1.0)
    if not math.isfinite(scale) or scale <= 0:
        scale = 1.0
    return max(0.0, min(1.0, current / scale))


def metric_bars(row: dict, scales: dict[str, float]) -> dict[str, str]:
    rendered = {}
    for key, label in RESULT_METRICS:
        score = metric_bar_score(row, key, scales)
        width = f"{score * 100:.1f}%"
        rendered[key] = f'''<div class="metric-display"><strong>{result_metric_markup(row, key)}</strong><span class="metric-bar" role="progressbar" aria-label="{esc(label)} metric value" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{score * 100:.1f}"><span style="width: {width}"></span></span></div>'''
    return rendered


def result_model_markup(row: dict) -> str:
    variant = row.get("variant")
    variant_markup = f'<span class="results-variant">{esc(variant)}</span>' if variant else ""
    return f'''<div class="results-model-name"><strong>{esc(row.get("model"), "Unnamed model")}</strong>{variant_markup}</div>
      <span class="results-model-family">{esc(row.get("family"), "Forecaster")}</span>
      <span class="results-model-sampling">{esc(row.get("samples"), "Recorded setting")}</span>'''


def result_status_markup(row: dict) -> str:
    status = row.get("status", "provisional")
    status_class = "ranked" if status == "ranked" else "provisional"
    detail = row.get("statusDetail", "Status details unavailable")
    detail_markup = (
        f'<span class="result-status-detail">{esc(detail)}</span>' if detail else ""
    )
    return f'''<span class="result-status {status_class}">{esc(row.get("statusLabel"), "Status")}</span>{detail_markup}'''


def result_sort_value(row: dict) -> float:
    try:
        return float(((row.get("metrics") or {}).get("scrps") or {}).get("mean"))
    except (TypeError, ValueError):
        return float("inf")


def result_table(rows: list[dict], protocol: dict, scales: dict[str, float]) -> str:
    body = []
    order_label = "Rank"
    for order, row in enumerate(rows, start=1):
        shown_rank = row.get("rank") if protocol.get("id") == "common" else order
        rank = f'<span class="results-rank">#{int(shown_rank)}</span>' if shown_rank else '<span class="results-rank muted">—</span>'
        bars = metric_bars(row, scales)
        show_status = protocol.get("id") != "full" and not (
            protocol.get("id") == "common" and row.get("status") == "ranked"
        )
        status_markup = (
            f'<div class="results-inline-status">{result_status_markup(row)}</div>'
            if show_status
            else ""
        )
        body.append(f'''<tr class="results-row {esc(row.get("status"), "provisional")}">
          <th scope="row" class="results-rank-cell">{rank}</th>
          <td class="results-model-cell">{result_model_markup(row)}{status_markup}</td>
          <td class="results-number primary-metric" data-label="sCRPS">{bars["scrps"]}</td>
          <td class="results-number" data-label="sMAE">{bars["smae"]}</td>
          <td class="results-number" data-label="sRMSE">{bars["srmse"]}</td>
        </tr>''')
    table_label = f'{protocol.get("label", "Leaderboard")} model comparison'
    return f'''<div class="results-table-wrap">
      <table class="results-table">
        <caption class="sr-only">{esc(table_label)}</caption>
        <thead><tr><th scope="col">{esc(order_label)}</th><th scope="col">Forecaster</th><th scope="col" class="primary-metric">sCRPS ↓</th><th scope="col">sMAE ↓</th><th scope="col">sRMSE ↓</th></tr></thead>
        <tbody>{"".join(body)}</tbody>
      </table>
    </div>'''


def result_context_block(protocol: dict, context_key: str, context_label: str, context_description: str, scales: dict[str, float]) -> str:
    rows = [row for row in protocol.get("rows", []) if row.get("contextKey") == context_key]
    if not rows:
        return ""
    rows.sort(key=result_sort_value)
    index = list(key for key, _, _ in RESULT_CONTEXTS).index(context_key) + 1
    return f'''<article class="results-context-card" id="{esc(protocol.get("id"))}-leaderboard-{esc(context_key)}">
      <div class="results-context-head"><div class="results-context-title"><span class="results-context-index">0{index}</span><div><h3>{esc(context_label)}</h3><p>{esc(context_description)}</p></div></div><span class="results-context-count">{len(rows)} rows</span></div>
      {result_table(rows, protocol, scales)}
    </article>'''


def results_summary(protocol: dict) -> str:
    rows = protocol.get("rows", [])
    ranked = sum(1 for row in rows if row.get("eligible"))
    target = protocol.get("targetTasks")
    common = protocol.get("id") == "common"
    scope_label = "Comparison" if common else "Scope"
    scope_value = "Common" if common else pretty_number(target)
    scope_detail = "one shared task mask" if common else "tasks in the benchmark"
    rank_label = "Rankable rows" if ranked else "Ranking status"
    rank_value = str(ranked) if ranked else protocol.get("statusLabel", "Provisional")
    return f'''<div class="results-summary-grid">
      <article class="results-summary-card emphasis"><span class="results-summary-label">{esc(scope_label)}</span><strong>{esc(scope_value)}</strong><small>{esc(scope_detail)}</small></article>
      <article class="results-summary-card"><span class="results-summary-label">Displayed rows</span><strong>{len(rows)}</strong><small>model · context combinations</small></article>
      <article class="results-summary-card"><span class="results-summary-label">{esc(rank_label)}</span><strong class="results-summary-status">{esc(rank_value)}</strong><small>{esc(protocol.get("statusDetail"), "Status details unavailable")}</small></article>
    </div>'''


def results_panel(protocol: dict, scales: dict[str, float]) -> str:
    context_blocks = "".join(
        result_context_block(protocol, key, label, description, scales)
        for key, label, description in RESULT_CONTEXTS
    )
    description = protocol.get("description")
    description_markup = f'<p>{esc(description)}</p>' if description else ""
    return f'''<article class="results-protocol" id="{esc(protocol.get("id"))}-leaderboard">
      <div class="results-protocol-head"><div><div class="eyebrow">{esc(protocol.get("scopeLabel"))}</div><h3>{esc(protocol.get("title"), "Leaderboard")}</h3>{description_markup}</div><span class="results-protocol-badge">{esc(protocol.get("statusLabel"), "Reported")}</span></div>
      {results_summary(protocol)}
      <div class="results-context-stack">{context_blocks}</div>
    </article>'''


def deep_research_results(payload: dict) -> str:
    metrics = payload.get("metrics", [])
    rows = payload.get("rows", [])
    colors = ["#2d6b5c", "#719b69", "#d09a4f", "#4f83a8", "#8873a6"]
    chart_width = 1100
    chart_height = 455
    plot_top = 99
    plot_bottom = 352
    plot_height = plot_bottom - plot_top
    maximum = max(
        (
            float(((row.get("metrics") or {}).get(metric.get("key")) or {}).get("value", 0)) * 100
            for row in rows
            for metric in metrics
        ),
        default=0,
    )
    axis_max = max(10, int((maximum * 1.15 + 9) // 10) * 10)
    centers = [225 + index * 330 for index in range(len(metrics))]
    card_width = min(268, 300 - (len(metrics) * 4))
    bar_width = 26
    bar_gap = 12
    bar_cluster_width = len(rows) * bar_width + max(0, len(rows) - 1) * bar_gap

    # The hidden table keeps every value available to screen readers and other
    # assistive technology while the visible view uses grouped bars.
    table_headers = "".join(
        f'<th scope="col">{esc(metric.get("label"), "Metric")}</th>'
        for metric in metrics
    )
    table_rows = []
    for row in rows:
        cells = "".join(
            f'<td>{esc(((row.get("metrics") or {}).get(metric.get("key")) or {}).get("display"), "—")}</td>'
            for metric in metrics
        )
        table_rows.append(f'<tr><th scope="row">{esc(row.get("agent"), "Unnamed agent")}</th>{cells}</tr>')

    legend_items = []
    for index, row in enumerate(rows):
        x = 96 + index * 190
        color = colors[index % len(colors)]
        legend_items.append(
            f'<g class="dr-chart-legend-item"><rect x="{x}" y="39" width="12" height="12" rx="3" fill="{color}" />'
            f'<text x="{x + 19}" y="49">{esc(row.get("agent"), "Unnamed agent")}</text></g>'
        )

    chart_parts = [
        f'<svg class="dr-quality-chart" viewBox="0 0 {chart_width} {chart_height}" role="img" aria-labelledby="dr-chart-title dr-chart-description">',
        '<title id="dr-chart-title">Deep research agent quality by metric</title>',
        '<desc id="dr-chart-description">Grouped bar chart of evidence recall, supporting document recall, and distractor avoidance. Each metric group contains one bar per agent. Higher percentages are better.</desc>',
        *legend_items,
    ]

    for index, metric in enumerate(metrics):
        center = centers[index]
        x = center - card_width / 2
        chart_parts.append(
            f'<rect class="dr-chart-group" x="{x:.1f}" y="77" width="{card_width}" height="350" rx="18" fill="#f7faf5" stroke="#d9e5dd" />'
        )

    for tick in range(0, axis_max + 1, 10):
        y = plot_bottom - (tick / axis_max) * plot_height
        chart_parts.append(
            f'<line class="dr-chart-grid" x1="77" y1="{y:.1f}" x2="1065" y2="{y:.1f}" />'
            f'<text class="dr-chart-tick" x="63" y="{y + 4:.1f}" text-anchor="end">{tick}%</text>'
        )

    for metric_index, metric in enumerate(metrics):
        center = centers[metric_index]
        left = center - bar_cluster_width / 2
        for row_index, row in enumerate(rows):
            agent = row.get("agent", "Unnamed agent")
            score = (row.get("metrics") or {}).get(metric.get("key")) or {}
            display = score.get("display", "—")
            value = float(score.get("value", 0) or 0) * 100
            bar_height = (value / axis_max) * plot_height
            bar_x = left + row_index * (bar_width + bar_gap)
            bar_y = plot_bottom - bar_height
            color = colors[row_index % len(colors)]
            chart_parts.append(
                f'<g class="dr-chart-bar"><title>{esc(agent)} — {esc(metric.get("label"), "Metric")}: {esc(display)}</title>'
                f'<rect x="{bar_x:.1f}" y="{bar_y:.1f}" width="{bar_width}" height="{bar_height:.1f}" rx="5" fill="{color}" />'
                f'<text class="dr-chart-value" x="{bar_x + bar_width / 2:.1f}" y="{bar_y - 8:.1f}" text-anchor="middle">{esc(display)}</text></g>'
            )
        label = esc(metric.get("label", "Metric").replace("↑", "").strip())
        chart_parts.append(
            f'<text class="dr-chart-metric" x="{center}" y="393" text-anchor="middle">{label}</text>'
        )
    chart_parts.append('</svg>')
    accessible_table = (
        '<table class="sr-only"><caption>Deep research agent metrics shown in the grouped bar chart</caption>'
        f'<thead><tr><th scope="col">DR agent</th>{table_headers}</tr></thead>'
        f'<tbody>{"".join(table_rows)}</tbody></table>'
    )
    return f'''<article class="results-protocol dr-quality" id="dr-quality">
      <div class="results-protocol-head"><div><div class="eyebrow">Deep research</div><h3>{esc(payload.get("title"), "Deep research quality")}</h3><p>{esc(payload.get("description"))}</p></div></div>
      <div class="dr-chart-scroll" role="region" aria-label="Deep research agent metric chart" tabindex="0">
        {"".join(chart_parts)}
      </div>
      {accessible_table}
      <p class="dr-results-note">Higher is better for all three metrics. Evidence Recall scores matched evidence with source citation credit; Supporting Document Recall measures source recovery; Distractor Avoidance is the share of cited documents that are not distractors.</p>
    </article>'''


def results_section(leaderboard: dict) -> str:
    full = leaderboard.get("protocols", {}).get("full", {})
    common = leaderboard.get("protocols", {}).get("common", {})
    deep_research = leaderboard.get("deepResearch", {})
    scales = leaderboard_metric_scales(leaderboard)
    return f'''<section class="section results-section" id="leaderboard"><div class="wrap">
      <div class="section-heading"><div><div class="eyebrow">Leaderboard</div><h2>Leaderboard</h2></div></div>
      <nav class="results-switcher" aria-label="Leaderboard views"><a class="results-switcher-link full" href="#full-leaderboard"><span>Full benchmark</span><small>complete scope</small></a><a class="results-switcher-link common" href="#common-leaderboard"><span>Common comparison</span><small>Strict common mask</small></a><a class="results-switcher-link deep-research" href="#dr-quality"><span>Deep research</span><small>retrieval and synthesis</small></a></nav>
      <div class="results-reading-note"><span class="results-reading-mark" aria-hidden="true">↘</span><div><strong>Read sCRPS first.</strong> Lower is better for sCRPS, sMAE, and sRMSE. Values are shown as mean ± standard deviation. The first view reports results for the {FULL_BENCHMARK_TASKS}-task benchmark; the common view keeps its own strict shared-task convention. Error bars use one shared metric-specific scale across both views, with the largest displayed mean at 100%; longer bars therefore indicate larger error.</div></div>
      {results_panel(full, scales)}
      {results_panel(common, scales)}
      {deep_research_results(deep_research)}
    </div></section>'''


def benchmark_domain_rows(stats: dict) -> str:
    domains = stats.get("domains", [])
    maximum = max((int(item.get("count", 0)) for item in domains), default=1)
    rows = []
    for item in domains:
        count = int(item.get("count", 0))
        width = count / maximum * 100
        rows.append(
            f'''<div class="benchmark-domain-row" role="listitem">
              <span class="benchmark-domain-label">{esc(item.get("label"), "Unassigned")}</span>
              <span class="benchmark-stat-track"><span style="width: {width:.2f}%"></span></span>
              <strong>{pretty_number(count)}</strong>
            </div>'''
        )
    return "".join(rows)


def benchmark_frequency_rows(stats: dict) -> str:
    frequencies = stats.get("frequencies", [])
    maximum = max((int(item.get("count", 0)) for item in frequencies), default=1)
    rows = []
    for item in frequencies:
        count = int(item.get("count", 0))
        width = count / maximum * 100
        rows.append(
            f'''<div class="benchmark-frequency-row" role="listitem">
              <span class="benchmark-frequency-label">{esc(item.get("label"), "Unknown cadence")}</span>
              <span class="benchmark-stat-track"><span style="width: {width:.2f}%"></span></span>
              <strong>{pretty_number(count)}</strong>
            </div>'''
        )
    return "".join(rows)


def benchmark_distractor_rows(stats: dict) -> str:
    rows = []
    for index, item in enumerate(stats.get("distractorTypes", []), start=1):
        rows.append(
            f'''<div class="benchmark-distractor-item tone-{index}" role="listitem">
              <div class="benchmark-distractor-title"><span class="benchmark-distractor-dot"></span><strong>{esc(item.get("label"), "Distractor")}</strong><span>{pretty_number(item.get("count"))} docs</span></div>
              <p>{esc(item.get("description"), "Typed forecast-irrelevant context.")}</p>
            </div>'''
        )
    return "".join(rows)


def benchmark_distribution_chart(distribution: dict, label: str) -> str:
    bins = distribution.get("bins", [])
    maximum = max((int(item.get("count", 0)) for item in bins), default=1)
    bars = []
    for item in bins:
        count = int(item.get("count", 0))
        height = count / maximum * 100 if maximum else 0
        bars.append(
            f'''<div class="benchmark-chart-bin">
              <span class="benchmark-chart-count">{pretty_number(count)}</span>
              <span class="benchmark-chart-column"><span style="height: {height:.2f}%"></span></span>
              <span class="benchmark-chart-label">{esc(item.get("label"), "—")}</span>
            </div>'''
        )
    return f'''<div class="benchmark-distribution-chart" role="img" aria-label="{esc(label)}">
      <div class="benchmark-chart-scale"><span>{pretty_number(maximum)}</span><span>0</span></div>
      <div class="benchmark-chart-bars">{"".join(bars)}</div>
    </div>'''


def benchmark_distribution_meta(distribution: dict) -> str:
    return f'''<div class="benchmark-distribution-meta">
      <span><small>p25</small><strong>{pretty_number(distribution.get("p25"))}</strong></span>
      <span class="median"><small>median</small><strong>{pretty_number(distribution.get("median"))}</strong></span>
      <span><small>p75</small><strong>{pretty_number(distribution.get("p75"))}</strong></span>
      <span><small>range</small><strong>{pretty_number(distribution.get("min"))}–{pretty_number(distribution.get("max"))}</strong></span>
    </div>'''


def generation_pipeline_section(stats: dict) -> str:
    documents = stats.get("documents", {})
    supporting_documents = int(documents.get("supporting", 0))
    distractor_documents = int(documents.get("distractor", 0))
    return f'''<section class="section pipeline-section" id="pipeline"><div class="wrap">
      <div class="pipeline-page-heading">
        <div><div class="eyebrow">Environment generation pipeline</div><h2 id="pipeline-title">From a context-conditioned forecast to a controlled research environment.</h2></div>
        <p>Dr-CiK turns a forecasting instance into an evidence-grounded task through explicit entity normalization, causal evidence decomposition, document-level synthesis, typed distractors, and quality-controlled validation.</p>
      </div>
        <div class="pipeline-figure-panel" aria-labelledby="pipeline-figure-title">
        <div class="pipeline-figure-heading">
          <div><div class="eyebrow">Figure 2 · Environment generation pipeline</div><h3 id="pipeline-figure-title">The complete construction path, from source context to inspectable evidence.</h3></div>
          <p>Read the figure from left to right: normalize the task, extract forecast-relevant evidence, expand the reasoning chain, then generate and validate supporting and distractor documents.</p>
        </div>
        <figure class="pipeline-figure">
          <div class="pipeline-figure-frame"><img src="assets/gen_flow_main.png" alt="Figure 2. Dr-CiK environment generation pipeline, showing entity disambiguation, multi-hop evidence decomposition, supporting and distractor metadata generation, document generation, and quality control." /></div>
          <figcaption><span>Figure 2.</span> Dr-CiK construction converts a context-conditioned forecasting instance into an evidence-grounded research task through entity disambiguation, multi-hop evidence decomposition, controllable reasoning depth, and traceable supporting and distractor document generation. <a href="assets/gen_flow_main.pdf" target="_blank" rel="noopener">Open the source figure ↗</a></figcaption>
        </figure>
      </div>
      <div class="pipeline-explainer-intro"><span class="eyebrow">Pipeline, unpacked</span><p>The diagram above is the paper construction view. The cards below make each block easier to inspect: what enters the stage, what it produces, and which control keeps the generated environment faithful to the forecasting mechanism.</p></div>
      <div class="benchmark-pipeline" aria-labelledby="pipeline-title">
        <div class="pipeline-context-grid">
          <article class="pipeline-context-card">
            <div class="pipeline-context-head"><span>Input / source task</span><strong>Multimodal time-series corpus</strong></div>
            <h3><span>Task 1</span>Electricity Consumption</h3>
            <div class="pipeline-text-block"><span>Original context</span><p>This is the electricity consumption recorded in kilowatt (kW) in city A. Suppose that there is a heat wave in city A from 2012-10-09 18:00:00 for 3 hours, leading to excessive use of air conditioning, and 5 times the usual electricity being consumed.</p></div>
            <div class="pipeline-context-foot"><span>time-series history</span><span>external context</span></div>
          </article>
          <span class="pipeline-context-arrow" aria-hidden="true">→</span>
          <article class="pipeline-context-card rewritten">
            <div class="pipeline-context-head"><span>Normalization output</span><strong>Entity-aware rewrite</strong></div>
            <h3><span>Same mechanism</span>Portable context</h3>
            <div class="pipeline-text-block"><span>Rewritten context</span><p>This is the electricity consumption recorded in kW in Veridian city. Suppose that there is a heat wave in Veridian city from 2012-10-09 18:00:00 for 3 hours, leading to excessive use of air conditioning, and 5 times the usual electricity being consumed.</p></div>
            <div class="pipeline-context-foot"><span>surface form changed</span><span>forecast semantics preserved</span></div>
          </article>
        </div>

        <div class="pipeline-lane">
          <div class="pipeline-lane-head"><span class="pipeline-lane-index">01—03</span><div><span class="pipeline-lane-kicker">Task normalization</span><h3>Make the task portable without changing its mechanism.</h3><p>Entity extraction, minimal profile generation, and profile assignment remove surface shortcuts while preserving the series–context relationship.</p></div></div>
          <div class="pipeline-stage-flow three">
            <article class="pipeline-stage">
              <div class="pipeline-stage-top"><span>01</span><em>LLM · Entity Judge</em></div><h4>Entity Extraction</h4><p>Identify one primary entity, align it with the time-series variable, and extract explicit containment relations.</p><div class="pipeline-stage-tags"><span>primary entity</span><span>relations</span></div>
            </article>
            <span class="pipeline-stage-arrow" aria-hidden="true">→</span>
            <article class="pipeline-stage featured">
              <div class="pipeline-stage-top"><span>02</span><em>LLM</em></div><h4>Profile Generation</h4><p>Compute the minimal profile count and generate realistic, reusable city or sensor profiles.</p><div class="pipeline-stage-tags"><span>minimal K</span><span>realistic profiles</span></div>
            </article>
            <span class="pipeline-stage-arrow" aria-hidden="true">→</span>
            <article class="pipeline-stage">
              <div class="pipeline-stage-top"><span>03</span><em>LLM · Entity Judge</em></div><h4>Profile Assignment</h4><p>Assign the primary profile and rewrite entity references only, so causal content and target semantics remain intact.</p><div class="pipeline-stage-tags"><span>rewrite entity</span><span>preserve mechanism</span></div>
            </article>
          </div>
          <div class="pipeline-human-gate"><span>Human in the loop</span><span>entity alignment</span><span>profile realism</span><span>rewrite fidelity</span></div>
        </div>

        <div class="pipeline-trace">
          <div class="pipeline-trace-head"><span>Evidence trace</span><strong>Context → atomic evidence → reasoning chain</strong></div>
          <div class="pipeline-trace-grid">
            <article class="pipeline-trace-card"><div class="pipeline-stage-top"><span>04</span><em>LLM · Evidence Judge</em></div><h4>Evidence Extraction</h4><div class="pipeline-evidence-item"><b>E1</b><span>Heat wave in Veridian city from 2012-10-09 18:00 for 3 hours.</span></div><div class="pipeline-evidence-item"><b>E2</b><span>Excessive air conditioning leads to 5× usual electricity consumption.</span></div></article>
            <span class="pipeline-trace-arrow" aria-hidden="true">→</span>
            <article class="pipeline-trace-card reasoning"><div class="pipeline-stage-top"><span>05</span><em>LLM · Reasoning Judge</em></div><h4>Reasoning Chain Expansion</h4><div class="pipeline-chain"><span>heat wave</span><i>→</i><span>cooling demand</span><i>→</i><span>electricity load</span></div><p>Controllable hops make the reasoning burden explicit: no shortcut, branch, or cycle.</p></article>
          </div>
        </div>

        <div class="pipeline-lane documents-lane">
          <div class="pipeline-lane-head"><span class="pipeline-lane-index">06—08</span><div><span class="pipeline-lane-kicker">Evidence environment</span><h3>Turn causal structure into a testable document corpus.</h3><p>Supporting and distractor documents are generated separately, typed, and judged against the original forecasting mechanism.</p></div></div>
          <div class="pipeline-stage-flow three">
            <article class="pipeline-stage">
              <div class="pipeline-stage-top"><span>06</span><em>LLM · Supporting Doc Judge</em></div><h4>Supporting Doc Generation</h4><p>Assign evidence and connecting links, then generate metadata for coverage, temporal consistency, and entity alignment.</p><div class="pipeline-stage-tags"><span>supporting meta</span><span>coverage</span></div>
            </article>
            <span class="pipeline-stage-arrow" aria-hidden="true">→</span>
            <article class="pipeline-stage distractor-stage">
              <div class="pipeline-stage-top"><span>07</span><em>LLM · Distractor Doc Judge</em></div><h4>Distractor Doc Generation</h4><p>Draft plausible alternatives that target specific failure modes rather than generic noise.</p><div class="pipeline-stage-tags"><span>5 families</span><span>targeted failure</span></div>
            </article>
            <span class="pipeline-stage-arrow" aria-hidden="true">→</span>
            <article class="pipeline-stage">
              <div class="pipeline-stage-top"><span>08</span><em>LLM</em></div><h4>Meta2Doc Generation</h4><p>Render supporting and distractor metadata into standalone documents with their labels retained for evaluation.</p><div class="pipeline-stage-tags"><span>{pretty_number(supporting_documents)} supporting</span><span>{pretty_number(distractor_documents)} distractors</span></div>
            </article>
          </div>
           <div class="pipeline-taxonomy"><span>Distractor taxonomy</span><div><b>Irrelevant</b><b>Off-variable</b><b>Off-entity</b><b>Off-window</b><b>Counterfactual history</b></div></div>
        </div>

        <div class="pipeline-document-output">
          <div class="pipeline-trace-head"><span>Document-level output</span><strong>Illustrative generated records</strong></div>
          <div class="pipeline-document-grid">
            <article class="pipeline-document-card supporting"><div><span>Supporting document</span><b>ground truth</b></div><p>Heat-wave notice for Veridian city, 2012-10-09 18:00–21:00. Expected effect: cooling demand raises electricity consumption to 5× baseline.</p><small>causal alignment · target horizon · entity consistent</small></article>
             <article class="pipeline-document-card distractor"><div><span>Typed distractor</span><b>Off-window / Off-entity</b></div><p>A similar heat-wave report describes another city outside the target forecast window: plausible on the surface, but not evidence for this series.</p><small>forecast-irrelevant by design · distractor label retained</small></article>
          </div>
        </div>

        <div class="pipeline-quality-gate"><div><span class="pipeline-quality-mark">✓</span><div><strong>Quality-controlled environment</strong><p>LLM judges iterate until documents satisfy the required criteria, with human-in-the-loop checks for entity alignment, evidence coverage, realism, and type consistency.</p></div></div><div class="pipeline-quality-stats"><span><b>{pretty_number(supporting_documents)}</b> supporting</span><span><b>{pretty_number(distractor_documents)}</b> distractors</span><span><b>{pretty_number(documents.get("distractorFamilies"))}</b> families</span><span><b>{pretty_number(documents.get("distractorPerTask"))}</b> per task</span></div></div>

        <div class="pipeline-advantages">
          <div class="pipeline-advantage"><span class="pipeline-advantage-mark">✦</span><div><strong>Mechanism-aware</strong><p>Evidence is tied to the target series and forecast horizon—not just topical similarity.</p></div></div>
          <div class="pipeline-advantage"><span class="pipeline-advantage-mark">◈</span><div><strong>Selective by design</strong><p>Agents cannot succeed by taking one shortcut document or by retrieving the entire corpus.</p></div></div>
          <div class="pipeline-advantage"><span class="pipeline-advantage-mark">⌁</span><div><strong>Diagnosable under intervention</strong><p>Gold evidence, typed distractors, and reasoning factors separate research failures from forecasting failures.</p></div></div>
        </div>
      </div>
    </div></section>'''


def benchmark_section(stats: dict) -> str:
    documents = stats.get("documents", {})
    total_documents = int(documents.get("total", 0))
    supporting_documents = int(documents.get("supporting", 0))
    distractor_documents = int(documents.get("distractor", 0))
    supporting_width = supporting_documents / total_documents * 100 if total_documents else 0
    history = stats.get("historyDistribution", {})
    horizon = stats.get("horizonDistribution", {})
    evidence = stats.get("evidence", {})
    return f'''<section class="section benchmark-section" id="scope"><div class="wrap">
       <div class="section-heading benchmark-heading"><div><div class="eyebrow">Benchmark profile</div><h2>Context-aided forecasting<br /><em>via deep research.</em></h2></div><p>Dr-CiK brings 279 forecasting tasks into one inspectable evidence environment. The profile below summarizes the complete evaluation and its 80-task expert-curated split across domains, cadences, evidence depth, and time-series scale.</p></div>
      <div class="benchmark-scope-grid">
        <article class="benchmark-scope-card primary"><div class="benchmark-scope-kicker"><span>01</span>Full benchmark</div><strong class="benchmark-scope-number">279</strong><span class="benchmark-scope-label">tasks in the complete evaluation</span><p>The broad-coverage partition adapts context-aided forecasting instances for scale and diversity across time-series patterns, domains, and context mechanisms.</p><span class="benchmark-scope-ring" aria-hidden="true"></span></article>
        <article class="benchmark-scope-card"><div class="benchmark-scope-kicker"><span>02</span>Expert-curated</div><strong class="benchmark-scope-number">80</strong><span class="benchmark-scope-label">human-labeled real-world time series</span><p>Real, unedited time series paired with domain-expert context, structured causal chains, labeled ground-truth evidence, and fine-grained difficulty labels for factor-conditioned analysis.</p><span class="benchmark-scope-ring" aria-hidden="true"></span></article>
      </div>
      <div class="benchmark-facts" aria-label="Benchmark summary statistics">
        <div class="benchmark-fact"><span class="benchmark-fact-icon">◌</span><strong>{pretty_number(stats.get("domainCount"))}</strong><span>applied domains</span></div>
        <div class="benchmark-fact"><span class="benchmark-fact-icon">↝</span><strong>{pretty_number(stats.get("frequencyCount"))}</strong><span>sampling frequencies</span></div>
        <div class="benchmark-fact"><span class="benchmark-fact-icon">▤</span><strong>{pretty_number(total_documents)}</strong><span>evidence documents</span></div>
        <div class="benchmark-fact"><span class="benchmark-fact-icon">⊙</span><strong>{pretty_number(documents.get("distractorPerTask"))}</strong><span>distractors per task</span></div>
      </div>
      <div class="benchmark-profile-grid">
        <article class="benchmark-panel benchmark-domains-panel">
           <div class="benchmark-panel-head"><div><span class="benchmark-panel-kicker">Coverage / 01</span><h3>Applied domains</h3><p>Fourteen domain families keep the evaluation grounded in real forecasting settings.</p></div><div class="benchmark-panel-stat"><strong>{pretty_number(stats.get("domainCount"))}</strong><span>domains</span></div></div>
          <div class="benchmark-domain-list" role="list" aria-label="Task counts by applied domain">{benchmark_domain_rows(stats)}</div>
        </article>
        <article class="benchmark-panel benchmark-corpus-panel">
          <div class="benchmark-panel-head"><div><span class="benchmark-panel-kicker">Deep research / 02</span><h3>Evidence environment</h3><p>Supporting material is mixed with typed distractors to test evidence selection—not topical retrieval alone.</p></div><span class="benchmark-panel-dot" aria-hidden="true"></span></div>
          <div class="benchmark-corpus-layout">
            <div class="benchmark-corpus-summary">
              <div class="benchmark-corpus-total"><strong>{pretty_number(total_documents)}</strong><span>documents across the benchmark</span></div>
              <div class="benchmark-corpus-bar" role="img" aria-label="Evidence corpus: supporting and distractor documents"><span class="supporting" style="width: {supporting_width:.2f}%"></span><span class="distractor" style="width: {100 - supporting_width:.2f}%"></span></div>
              <div class="benchmark-corpus-legend"><span><i class="supporting"></i><strong>{pretty_number(supporting_documents)}</strong> supporting</span><span><i class="distractor"></i><strong>{pretty_number(distractor_documents)}</strong> distractors</span></div>
              <div class="benchmark-corpus-note"><strong>{pretty_number(documents.get("distractorFamilies"))}</strong> distractor families <span>·</span> <strong>{pretty_number(documents.get("distractorPerTask"))}</strong> per task</div>
            </div>
            <div class="benchmark-distractor-surface">
              <div class="benchmark-distractor-head"><strong>What the distractors test</strong><span>balanced by family</span></div>
              <div class="benchmark-distractor-list" role="list" aria-label="Distractor family definitions">{benchmark_distractor_rows(stats)}</div>
            </div>
          </div>
        </article>
        <article class="benchmark-panel benchmark-timeseries-panel">
          <div class="benchmark-panel-head"><div><span class="benchmark-panel-kicker">Temporal scale / 03</span><h3>Time-series distributions</h3><p>History and horizon lengths vary across several orders of magnitude.</p></div><span class="benchmark-panel-caption">task counts by length bucket</span></div>
          <div class="benchmark-distribution-pair">
            <div class="benchmark-distribution"><div class="benchmark-distribution-title"><strong>History length</strong><span>observed points</span></div>{benchmark_distribution_chart(history, "Distribution of history lengths in observed time-series points")}{benchmark_distribution_meta(history)}</div>
            <div class="benchmark-distribution"><div class="benchmark-distribution-title"><strong>Forecast horizon</strong><span>future points</span></div>{benchmark_distribution_chart(horizon, "Distribution of forecast horizon lengths in future time-series points")}{benchmark_distribution_meta(horizon)}</div>
          </div>
        </article>
        <article class="benchmark-panel benchmark-frequency-panel">
          <div class="benchmark-panel-head"><div><span class="benchmark-panel-kicker">Temporal scale / 04</span><h3>Sampling cadence</h3><p>From seconds to annual observations, with a strong hourly core.</p></div><div class="benchmark-panel-stat"><strong>{pretty_number(stats.get("frequencyCount"))}</strong><span>frequencies</span></div></div>
          <div class="benchmark-frequency-list" role="list" aria-label="Task counts by sampling frequency">{benchmark_frequency_rows(stats)}</div>
        </article>
        <article class="benchmark-panel benchmark-depth-panel">
          <div class="benchmark-panel-head"><div><span class="benchmark-panel-kicker">Deep research / 05</span><h3>Ground-truth evidence</h3><p>Each task has labeled ground-truth evidence; these statistics describe what an agent must recover to ground a forecast.</p></div><span class="benchmark-panel-dot gold" aria-hidden="true"></span></div>
          <div class="benchmark-ground-truth-grid">
            <div class="benchmark-evidence-stat"><strong>{pretty_number(evidence.get("median"))}</strong><span>median ground-truth evidence items per task</span></div>
            <div class="benchmark-evidence-stat featured"><strong>{pretty_number(evidence.get("items"))}</strong><span>ground-truth evidence items</span></div>
            <div class="benchmark-evidence-stat"><strong>{pretty_number(evidence.get("tasks"))}</strong><span>tasks with ground-truth evidence</span></div>
            <div class="benchmark-evidence-stat"><strong>{pretty_number(evidence.get("mean"))}</strong><span>mean ground-truth evidence items per task</span></div>
          </div>
          <div class="benchmark-depth-track"><span class="benchmark-depth-range"></span><span class="benchmark-depth-marker overall" style="left: {(int(evidence.get("median", 0)) - int(evidence.get("min", 0))) / max(1, int(evidence.get("max", 0)) - int(evidence.get("min", 0))) * 100:.2f}%"></span><span class="benchmark-depth-marker expert" style="left: {(int(evidence.get("expertMedian", 0)) - int(evidence.get("min", 0))) / max(1, int(evidence.get("max", 0)) - int(evidence.get("min", 0))) * 100:.2f}%"></span></div>
          <div class="benchmark-depth-labels"><span>{pretty_number(evidence.get("min"))} min</span><span>{pretty_number(evidence.get("max"))} max</span></div>
          <div class="benchmark-depth-callouts"><div class="benchmark-depth-callout overall"><span class="benchmark-depth-key overall"></span><strong>{pretty_number(evidence.get("median"))}</strong> benchmark median</div><div class="benchmark-depth-callout"><span class="benchmark-depth-key expert"></span><strong>{pretty_number(evidence.get("expertMedian"))}</strong> expert-curated median</div></div>
          <div class="benchmark-facet-line"><span>Reasoning factors</span><div class="benchmark-facet-pills"><span>Certainty</span><span>Explicitness</span><span>Domain knowledge</span><span>Temporal complexity</span></div></div>
        </article>
      </div>
      <div class="benchmark-source-note"><span class="benchmark-source-mark" aria-hidden="true">✦</span><p>Aggregate profile reconstructed from the 279-task benchmark statistics used in the paper. Charts are data-native so the page remains crisp and inspectable.</p><a href="data/benchmark_stats.json">Open aggregate profile JSON <span aria-hidden="true">→</span></a></div>
    </div></section>'''


def index_page(index: dict, tasks: list[dict], annotations: dict, leaderboard: dict, benchmark_stats: dict) -> str:
    cards = "".join(card(task, annotations.get(task["id"], {})) for task in tasks)
    return f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#032d42" />
    <meta name="description" content="Dr-CiK: a 279-task benchmark for context-aided forecasting via deep research, by ServiceNow Research." />
    <title>{esc(PROJECT["title"])}</title>
    <link rel="stylesheet" href="styles.css?v={ASSET_VERSION}" />
{project_head()}
    {homepage_scroll_guard()}
  </head>
  <body>
    {brand_header()}
    <main id="top">
      <section class="hero">
        <div class="wrap hero-grid">
          <div>
            <a class="hero-servicenow" href="https://www.servicenow.com/" target="_blank" rel="noopener noreferrer"><img src="static/assets/servicenow-logo.svg" alt="ServiceNow" width="185" height="28" /><span>Research</span></a>
            <div class="eyebrow">A benchmark by ServiceNow Research</div>
            <h1>Context-aided forecasting<br /><em>via deep research.</em></h1>
            <p class="hero-lede">A benchmark for context-aided forecasting via deep research. Agents must identify forecasting-relevant evidence, distinguish essential signals from distractors, and produce grounded forecasts.</p>
            {project_actions()}
          </div>
          <div class="hero-visual" aria-hidden="true">
            <div class="visual-orbit"></div>
            <div class="visual-card visual-card-main"><div class="visual-label"><span>Dr-CiK · controlled corpus</span><span>Research before forecast</span></div><div class="visual-title">Evidence to forecast</div><p class="visual-subtitle">Discover the evidence. Reject the distractors. Ground the horizon.</p><div class="research-path"><span class="research-step"><b>01</b><strong>Observe</strong><small>series history</small></span><i aria-hidden="true">→</i><span class="research-step active"><b>02</b><strong>Deep research</strong><small>forecast-relevant evidence</small></span><i aria-hidden="true">→</i><span class="research-step"><b>03</b><strong>Forecast</strong><small>grounded horizon</small></span></div><svg class="signal-chart" viewBox="0 0 380 125" preserveAspectRatio="none"><path class="gridline" d="M0 24H380M0 62H380M0 100H380" /><line class="signal-boundary" x1="230" y1="15" x2="230" y2="107" /><polyline class="signal" points="0,81 18,69 35,74 53,48 71,58 88,43 106,63 124,56 141,34 159,47 177,40 194,69 212,62 230,75 247,48 265,56 283,36 300,53 318,45 336,70 353,56 380,63" /><polyline class="signal-soft" points="230,75 247,67 265,73 283,61 300,69 318,58 336,65 353,59 380,51" /></svg><div class="visual-chart-caption"><span>observed history</span><span>forecast horizon</span></div></div>
            <div class="visual-card visual-card-small"><div class="visual-label"><span>Evidence field</span><span>supporting</span></div><span class="mini-stat-number">✓</span><span class="mini-stat-copy">supporting evidence kept in view</span></div>
            <div class="visual-card visual-card-bottom"><div class="visual-label"><span>Distractor field</span><span>typed</span></div><span class="mini-stat-number">×</span><span class="mini-stat-copy">irrelevant context filtered out</span></div>
          </div>
        </div>
        {project_identity()}
      </section>

      <div id="motivation" class="anchor-alias" aria-hidden="true"></div>
      {generation_pipeline_section(benchmark_stats)}

      <div id="benchmark" class="anchor-alias" aria-hidden="true"></div>
      {benchmark_section(benchmark_stats)}

      {results_section(leaderboard)}

      {release_section()}
      <div id="showcase" class="anchor-alias" aria-hidden="true"></div>
      <section class="section section-tint" id="explorer"><div class="wrap">
        <div class="explorer-head"><div class="section-heading" style="margin: 0; display: block;"><div class="eyebrow">Open the task library</div><h2>Inspect Tasks</h2></div><div class="explorer-count"><strong>{len(tasks)}</strong> development tasks</div></div>
        {annotation_guide()}
        <div class="task-grid" id="all-tasks">{cards}</div>
        <div class="explorer-foot"><span>Showing {len(tasks)} development tasks with a complete Figure 2 label set.</span><span><strong>Tip:</strong> use your browser’s Find command to jump to an entity or target series.</span></div>
      </div></section>

      {citation_section()}
    </main>
    {footer()}
    {citation_script()}
  </body>
</html>'''


def main() -> None:
    source_index = json.loads(INDEX_PATH.read_text())
    source_tasks = source_index.get("tasks", [])
    source_annotation_payload = json.loads(ANNOTATIONS_PATH.read_text())
    source_annotations = source_annotation_payload.get("tasks", {})
    evidence_payload = json.loads(EVIDENCE_PATH.read_text())
    source_evidence = evidence_payload.get("tasks", {})
    source_task_ids = {task["id"] for task in source_tasks}
    if set(source_annotations) != source_task_ids:
        raise SystemExit(
            f"Annotation coverage mismatch: expected {len(source_task_ids)}, "
            f"found {len(source_annotations)}"
        )

    tasks = [
        task
        for task in source_tasks
        if has_complete_difficulty_labels(source_annotations[task["id"]])
        and int(task.get("distractorCount", 0)) >= 25
    ]
    public_task_ids = {task["id"] for task in tasks}
    if not public_task_ids.issubset(source_evidence):
        raise SystemExit(
            f"Ground-truth evidence coverage mismatch: expected {len(public_task_ids)}, "
            f"found {len(public_task_ids.intersection(source_evidence))}"
        )
    annotations = {task["id"]: source_annotations[task["id"]] for task in tasks}
    public_evidence = {task["id"]: source_evidence[task["id"]] for task in tasks}
    task_details = {}
    for task in tasks:
        detail_path = ROOT / task["detailPath"]
        detail = json.loads(detail_path.read_text())
        detail["documents"] = paper_task_documents(detail.get("documents", []))
        task["distractorCount"] = sum(
            1 for document in detail["documents"]
            if str(document.get("role") or "").lower() == "distractor"
        )
        task["documentCount"] = len(detail["documents"])
        detail_path.write_text(
            json.dumps(detail, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
        task_details[task["id"]] = detail
    public_index = dict(source_index)
    public_index["tasks"] = tasks
    public_index["taskCount"] = len(tasks)
    public_index["sourceCounts"] = {
        source: sum(1 for task in tasks if task.get("sourceFamily") == source)
        for source in sorted({task.get("sourceFamily") for task in tasks})
        if source
    }
    public_annotation_payload = dict(source_annotation_payload)
    public_annotation_payload["tasks"] = annotations
    public_evidence_payload = dict(evidence_payload)
    public_evidence_payload["tasks"] = public_evidence
    public_evidence_payload["taskCount"] = len(public_evidence)
    INDEX_PATH.write_text(
        json.dumps(public_index, ensure_ascii=False, separators=(",", ":")) + "\n"
    )
    ANNOTATIONS_PATH.write_text(
        json.dumps(public_annotation_payload, ensure_ascii=False, separators=(",", ":"))
        + "\n"
    )
    EVIDENCE_PATH.write_text(
        json.dumps(public_evidence_payload, ensure_ascii=False, separators=(",", ":"))
        + "\n"
    )
    index = public_index
    leaderboard = normalize_leaderboard(json.loads(LEADERBOARD_PATH.read_text()))
    LEADERBOARD_PATH.write_text(json.dumps(leaderboard, ensure_ascii=False, indent=2) + "\n")
    benchmark_stats = json.loads(BENCHMARK_STATS_PATH.read_text())
    forecast_payload = json.loads(FORECASTS_PATH.read_text()) if FORECASTS_PATH.exists() else {}
    if benchmark_stats.get("tasks") != 279 or benchmark_stats.get("expertTasks") != 80:
        raise SystemExit("Benchmark statistics must describe the 279-task release and 80-task expert suite")
    if set(leaderboard.get("protocols", {})) != {"full", "common"}:
        raise SystemExit("Leaderboard must provide full and common protocols")
    task_ids = {task["id"] for task in tasks}
    if set(annotations) != task_ids:
        raise SystemExit(f"Annotation coverage mismatch: expected {len(task_ids)}, found {len(annotations)}")

    TASK_ROOT.mkdir(parents=True, exist_ok=True)
    published_detail_names = {f"{task_id}" for task_id in task_ids}
    for path in TASK_ROOT.glob("task_*.html"):
        if path.stem not in published_detail_names:
            path.unlink()
    for path in (DATA_ROOT / "tasks").glob("task_*.json"):
        if path.stem not in published_detail_names:
            path.unlink()
    (ROOT / "index.html").write_text(index_page(index, tasks, annotations, leaderboard, benchmark_stats))
    for task in tasks:
        task_forecast = (forecast_payload.get("tasks") or {}).get(task["id"], {})
        (TASK_ROOT / f'{task["id"]}.html').write_text(
            detail_page(task_details[task["id"]], annotations[task["id"]], public_evidence[task["id"]], task_forecast)
        )

    print(f"built index.html and {len(tasks)} static labeled task pages")


if __name__ == "__main__":
    main()
