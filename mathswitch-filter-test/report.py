"""Build report/index.html comparing the filters in data/results.json."""

import json
import random
from html import escape

import config
from filters import DESCRIPTIONS, FILTERS

CSS = """
:root {
  --bg: #fafaf9; --fg: #1c1917; --muted: #78716c; --card: #ffffff;
  --border: #e7e5e4; --accent: #2563eb; --yes: #15803d; --no: #b91c1c;
  --yes-bg: #dcfce7; --no-bg: #fee2e2; --na-bg: #f5f5f4; --heat: 37, 99, 235;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #1c1917; --fg: #f5f5f4; --muted: #a8a29e; --card: #292524;
    --border: #44403c; --accent: #60a5fa; --yes: #4ade80; --no: #f87171;
    --yes-bg: #14532d; --no-bg: #7f1d1d; --na-bg: #3a3633; --heat: 96, 165, 250;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg);
  font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 1200px; margin: 0 auto; padding: 24px 16px 64px; }
h1 { font-size: 24px; margin: 0 0 4px; }
h2 { font-size: 18px; margin: 40px 0 8px; }
p.lead, .muted { color: var(--muted); }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px; margin: 16px 0; }
.stat { background: var(--card); border: 1px solid var(--border); border-radius: 8px;
  padding: 12px; }
.stat b { display: block; font-size: 20px; font-variant-numeric: tabular-nums; }
.stat span { color: var(--muted); font-size: 12px; }
.scroll { overflow-x: auto; background: var(--card); border: 1px solid var(--border);
  border-radius: 8px; }
table { border-collapse: collapse; width: 100%; }
th, td { padding: 6px 10px; border-bottom: 1px solid var(--border); text-align: left;
  vertical-align: top; }
th { font-weight: 600; font-size: 12px; color: var(--muted); white-space: nowrap; }
th.sortable { cursor: pointer; user-select: none; }
th.sortable:hover { color: var(--fg); }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
tr:last-child td { border-bottom: none; }
.matrix td.cell { text-align: center; font-variant-numeric: tabular-nums; }
.matrix td.cell a { display: block; color: var(--fg); padding: 4px; border-radius: 4px; }
.matrix td.diag { color: var(--muted); text-align: center; }
.chip { display: inline-block; min-width: 20px; padding: 0 5px; border-radius: 4px;
  font-size: 12px; text-align: center; font-weight: 600; }
.chip.y { background: var(--yes-bg); color: var(--yes); }
.chip.n { background: var(--no-bg); color: var(--no); }
.chip.na { background: var(--na-bg); color: var(--muted); }
.badge { display: inline-block; padding: 0 6px; border-radius: 999px; font-size: 11px;
  border: 1px solid var(--accent); color: var(--accent); margin-left: 4px; }
.name { font-family: ui-monospace, "SFMono-Regular", Menlo, monospace; font-size: 13px;
  word-break: break-all; }
.doc { color: var(--muted); font-size: 12px; max-width: 420px; }
.module { color: var(--muted); font-size: 12px; word-break: break-all; }
details { background: var(--card); border: 1px solid var(--border); border-radius: 8px;
  margin: 8px 0; }
details > summary { cursor: pointer; padding: 10px 14px; font-weight: 600; }
details[open] > summary { border-bottom: 1px solid var(--border); }
details:target { outline: 2px solid var(--accent); }
.controls { display: flex; gap: 16px; flex-wrap: wrap; align-items: center;
  margin: 8px 0; }
.controls input[type=search] { padding: 6px 10px; border: 1px solid var(--border);
  border-radius: 6px; background: var(--card); color: var(--fg); min-width: 240px; }
.bar { height: 8px; background: rgba(var(--heat), 0.8); border-radius: 4px; }
"""

JS = """
function openTarget() {
  const id = decodeURIComponent(location.hash.slice(1));
  const el = id && document.getElementById(id);
  if (el && el.tagName === 'DETAILS') { el.open = true; el.scrollIntoView(); }
}
window.addEventListener('hashchange', openTarget);
openTarget();

document.querySelectorAll('table.sort').forEach(table => {
  table.querySelectorAll('th.sortable').forEach((th, col) => {
    th.addEventListener('click', () => {
      const idx = Array.from(th.parentNode.children).indexOf(th);
      const body = table.tBodies[0];
      const asc = th.dataset.dir !== 'asc';
      th.dataset.dir = asc ? 'asc' : 'desc';
      const key = tr => tr.children[idx].dataset.v ?? tr.children[idx].textContent;
      const rows = Array.from(body.rows);
      rows.sort((a, b) => {
        const x = key(a), y = key(b), nx = parseFloat(x), ny = parseFloat(y);
        const c = (!isNaN(nx) && !isNaN(ny)) ? nx - ny : x.localeCompare(y);
        return asc ? c : -c;
      });
      rows.forEach(r => body.appendChild(r));
    });
  });
});

const gtSearch = document.getElementById('gt-search');
const gtMissed = document.getElementById('gt-missed');
function filterGt() {
  const q = gtSearch.value.toLowerCase();
  const onlyMissed = gtMissed.checked;
  let shown = 0;
  document.querySelectorAll('#gt-table tbody tr').forEach(tr => {
    const ok = tr.textContent.toLowerCase().includes(q)
      && (!onlyMissed || tr.dataset.missed === '1');
    tr.hidden = !ok;
    if (ok) shown++;
  });
  document.getElementById('gt-count').textContent = shown;
}
gtSearch.addEventListener('input', filterGt);
gtMissed.addEventListener('change', filterGt);
filterGt();
"""


def pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "–"


def chip(value):
    if value is None:
        return '<span class="chip na" title="not evaluated">·</span>'
    return '<span class="chip y">✓</span>' if value else '<span class="chip n">✗</span>'


def heat(value, maximum):
    alpha = 0.08 + 0.6 * (value / maximum) if maximum else 0
    return f"background: rgba(var(--heat), {alpha:.2f})"


def pair_id(a, b):
    return f"pair-{a}-{b}"


def compute(results):
    decls = results["decls"]
    names = list(FILTERS)
    kept = {f: {n for n, d in decls.items() if d["filters"][f]} for f in names}
    evaluated = {
        f: {n for n, d in decls.items() if d["filters"][f] is not None} for f in names
    }
    pairs = {}
    for a in names:
        for b in names:
            if a == b:
                continue
            # compare only where both filters were evaluated (the LLM runs on a sample)
            scope = evaluated[a] & evaluated[b]
            pairs[(a, b)] = sorted((kept[a] - kept[b]) & scope)
    return names, kept, evaluated, pairs


def render_example_rows(rows, decls, gt_sets, names):
    out = []
    for n in rows:
        d = decls[n]
        badges = "".join(
            f'<span class="badge">{escape(s)}</span>' for s in gt_sets.get(n, [])
        )
        if d.get("wikidata"):
            badges += (
                f'<a class="badge" href="https://www.wikidata.org/wiki/{d["wikidata"]}">'
                f'{d["wikidata"]}</a>'
            )
        doc = (
            escape(" ".join(d["doc"].split())[:200])
            if d["doc"]
            else "<i>no docstring</i>"
        )
        chips = "".join(chip(d["filters"][f]) for f in names)
        out.append(
            "<tr>"
            f'<td><a class="name" href="{escape(d["url"])}">{escape(n)}</a>{badges}'
            f'<div class="module">{escape(d["module"])}</div></td>'
            f"<td>{escape(d['kind'])}</td>"
            f'<td class="num">{d["refs"]}</td>'
            f'<td class="doc">{doc}</td>'
            f"<td>{chips}</td>"
            "</tr>"
        )
    return "\n".join(out)


def build_html(results):
    decls = results["decls"]
    stats = results["stats"]
    gt = results["ground_truth"]
    names, kept, evaluated, pairs = compute(results)
    total = len(decls)

    gt_sets = {}
    for set_name, g in gt.items():
        for n in g["inside"]:
            gt_sets.setdefault(n, []).append(set_name)
    gt_all = sorted(gt_sets)

    llm_scope = evaluated["llm"]
    parts = []
    parts.append(
        f"""<h1>Mathlib concept filters</h1>
<p class="lead">Each filter on its own, evaluated on Mathlib <code>def</code>/<code>structure</code>/<code>class</code>/<code>inductive</code>
declarations. Ground truth is the concept lists in mathlib4's <code>docs/*.yaml</code>.</p>
<div class="stats">
  <div class="stat"><b>{total:,}</b><span>candidate declarations</span></div>
  <div class="stat"><b>{stats['coverage']:.1%}</b><span>found by the source parser</span></div>
  <div class="stat"><b>{len(gt_all):,}</b><span>ground-truth concepts in universe</span></div>
  <div class="stat"><b>{len(llm_scope):,}</b><span>judged by LLM ({escape(results['llm_model'])})</span></div>
</div>"""
    )

    # --- summary ---
    gt_cols = list(gt)
    head = "".join(
        f'<th class="num">recall {escape(s)} <span class="muted">(n={len(gt[s]["inside"])})</span></th>'
        for s in gt_cols
    )
    rows = []
    for f in names:
        ev = evaluated[f]
        recall_cells = []
        for s in gt_cols:
            inside = [n for n in gt[s]["inside"] if n in ev]
            hit = sum(1 for n in inside if n in kept[f])
            recall_cells.append(
                f'<td class="num" title="{hit}/{len(inside)}">{pct(hit, len(inside))}</td>'
            )
        all_inside = [n for n in gt_all if n in ev]
        all_hit = sum(1 for n in all_inside if n in kept[f])
        scope = ev & llm_scope
        agree = sum(
            1 for n in scope if decls[n]["filters"][f] == decls[n]["filters"]["llm"]
        )
        share = len(kept[f]) / len(ev) if ev else 0
        rows.append(
            f"<tr><td><b>{f}</b><div class='muted'>{escape(DESCRIPTIONS[f])}</div></td>"
            f'<td class="num">{len(kept[f]):,} <span class="muted">/ {len(ev):,}</span></td>'
            f'<td class="num">{share:.1%}<div class="bar" style="width:{share * 100:.0f}%"></div></td>'
            + "".join(recall_cells)
            + f'<td class="num">{pct(all_hit, len(all_inside))}</td>'
            + f'<td class="num">{"–" if f == "llm" else pct(agree, len(scope))}</td></tr>'
        )
    parts.append(
        f"""<h2>Summary</h2>
<p class="muted">Recall = share of ground-truth concepts the filter keeps. Lower “kept %” with high recall is better.
Agreement with LLM is measured on the LLM-judged subset.</p>
<div class="scroll"><table>
<thead><tr><th>filter</th><th class="num">kept</th><th class="num">kept %</th>{head}
<th class="num">recall all</th><th class="num">agrees with LLM</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>"""
    )

    # --- how many filters agree ---
    base = [f for f in names if f != "llm"]
    hist = [0] * (len(base) + 1)
    for d in decls.values():
        hist[sum(1 for f in base if d["filters"][f])] += 1
    hmax = max(hist)
    hist_rows = "".join(
        f'<tr><td class="num">{k}</td><td class="num">{v:,}</td>'
        f'<td style="width:60%"><div class="bar" style="width:{100 * v / hmax:.0f}%"></div></td></tr>'
        for k, v in enumerate(hist)
    )
    parts.append(
        f"""<h2>How many filters keep each declaration</h2>
<p class="muted">Counts over the {len(base)} non-LLM filters ({', '.join(base)}).</p>
<div class="scroll"><table><thead><tr><th class="num">filters keeping it</th><th class="num">declarations</th><th></th></tr></thead>
<tbody>{hist_rows}</tbody></table></div>"""
    )

    # --- pairwise matrix ---
    pmax = max((len(v) for v in pairs.values()), default=0)
    mrows = []
    for a in names:
        cells = []
        for b in names:
            if a == b:
                cells.append('<td class="diag">—</td>')
                continue
            v = len(pairs[(a, b)])
            star = "*" if "llm" in (a, b) else ""
            cells.append(
                f'<td class="cell" style="{heat(v, pmax)}"><a href="#{pair_id(a, b)}" '
                f'title="kept by {a}, dropped by {b}">{v:,}{star}</a></td>'
            )
        mrows.append(f"<tr><th>{a}</th>{''.join(cells)}</tr>")
    parts.append(
        f"""<h2>Pairwise differences</h2>
<p class="muted">Row A, column B = number of declarations <b>kept by A but dropped by B</b>. Click a cell for examples.
* = computed only on the LLM-judged subset.</p>
<div class="scroll"><table class="matrix"><thead><tr><th>kept by ↓ / dropped by →</th>
{''.join(f'<th style="text-align:center">{b}</th>' for b in names)}</tr></thead>
<tbody>{''.join(mrows)}</tbody></table></div>"""
    )

    # --- pair details ---
    rng = random.Random(config.EXAMPLES_SEED)
    chip_head = " ".join(f[:4] for f in names)
    details = []
    for (a, b), members in pairs.items():
        gt_members = [n for n in members if n in gt_sets]
        others = [n for n in members if n not in gt_sets]
        k = max(0, config.EXAMPLES_PER_CELL - len(gt_members))
        sample = gt_members + sorted(rng.sample(others, min(k, len(others))))
        details.append(
            f"""<details id="{pair_id(a, b)}"><summary>Kept by <b>{a}</b>, dropped by <b>{b}</b>
<span class="muted">— {len(members):,} declarations, {len(gt_members)} ground truth; showing {len(sample)}</span></summary>
<div class="scroll" style="border:none"><table class="sort">
<thead><tr><th class="sortable">name</th><th class="sortable">kind</th><th class="sortable num">refs</th>
<th>docstring</th><th>{chip_head}</th></tr></thead>
<tbody>{render_example_rows(sample, decls, gt_sets, names)}</tbody></table></div></details>"""
        )
    parts.append(
        "<h2>Examples per pair</h2><p class='muted'>Ground-truth concepts are listed first, "
        "then a fixed random sample. Chips show every filter's verdict in order: "
        + ", ".join(names)
        + ".</p>"
        + "\n".join(details)
    )

    # --- ground truth table ---
    gt_rows = []
    for n in gt_all:
        d = decls[n]
        verdicts = [d["filters"][f] for f in names]
        missed = any(v is False for v in verdicts)
        cells = "".join(
            f'<td data-v="{"" if v is None else int(v)}" style="text-align:center">{chip(v)}</td>'
            for v in verdicts
        )
        n_keep = sum(1 for v in verdicts if v)
        labels = ", ".join(
            f"{s}" + (f" ({gt[s]['labels'][n]})" if s in ("100", "1000") else "")
            for s in gt_sets[n]
        )
        gt_rows.append(
            f'<tr data-missed="{int(missed)}"><td><a class="name" href="{escape(d["url"])}">{escape(n)}</a>'
            f'<div class="module">{escape(d["module"])}</div></td>'
            f'<td class="muted">{escape(labels)}</td><td>{escape(d["kind"])}</td>'
            f'<td class="num">{d["refs"]}</td>{cells}<td class="num">{n_keep}</td></tr>'
        )
    gt_notes = "; ".join(
        f"{s}: {len(g['inside'])} of {g['total']} in universe "
        f"({g['other_kind']} are theorems/other kinds, {g['missing']} not in the index)"
        for s, g in gt.items()
    )
    parts.append(
        f"""<h2>Ground-truth concepts: who misses what</h2>
<p class="muted">{escape(gt_notes)}.</p>
<div class="controls"><input type="search" id="gt-search" placeholder="Filter by name, module, set…">
<label><input type="checkbox" id="gt-missed"> only rows some filter misses</label>
<span class="muted"><span id="gt-count"></span> rows</span></div>
<div class="scroll"><table class="sort" id="gt-table"><thead><tr>
<th class="sortable">name</th><th class="sortable">set</th><th class="sortable">kind</th><th class="sortable num">refs</th>
{''.join(f'<th class="sortable" style="text-align:center">{f}</th>' for f in names)}
<th class="sortable num">kept by</th></tr></thead>
<tbody>{''.join(gt_rows)}</tbody></table></div>"""
    )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mathlib concept filters</title>
<style>{CSS}</style></head>
<body><main>
{''.join(parts)}
</main><script>{JS}</script></body></html>
"""


def main():
    with open(config.RESULTS_JSON) as f:
        results = json.load(f)
    config.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    config.REPORT_HTML.write_text(build_html(results), encoding="utf-8")
    print(f"Wrote {config.REPORT_HTML}")


if __name__ == "__main__":
    main()
