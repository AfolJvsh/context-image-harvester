from __future__ import annotations

import csv
import html
import json
import zipfile
from pathlib import Path

from .models import Item


def write_reports(output: Path, items: list[Item], records: list[dict], summary: dict) -> None:
    if records:
        with (output / "manifest.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()))
            writer.writeheader()
            writer.writerows(records)
    (output / "manifest.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    markdown = [
        "# Image Review Pack",
        "",
        f"Target: {summary['target_total']}",
        f"Actual: {summary['actual_total']}",
        f"SerpApi requests: {summary['serpapi_requests_used']}",
        f"Rights mode: {summary['rights_mode']}",
        "",
    ]
    sections: list[str] = []
    for item in items:
        rows = [record for record in records if int(record["item_id"]) == item.id]
        markdown.append(f"## {item.id:03d}. {item.name} — {len(rows)}/{summary['target_per_item']}")
        cards: list[str] = []
        for record in rows:
            markdown.append(
                f"- {record['candidate']}: `{record['file']}` — {record['provider']} — "
                f"{record['rights_status']} — {record['license']} — {record['source_page']}"
            )
            cards.append(
                "<article class='card' "
                f"data-provider='{html.escape(record['provider'])}' "
                f"data-rights='{html.escape(record['rights_status'])}' "
                f"data-file='{html.escape(record['file'])}'>"
                f"<img src='{html.escape(record['file'])}' loading='lazy'>"
                f"<b>Candidate {record['candidate']}</b>"
                f"<small>{html.escape(record['provider'])}</small>"
                f"<small>{html.escape(record['rights_status'])}</small>"
                f"<small>score {record['final_score']}</small>"
                f"<a href='{html.escape(record['source_page'])}' target='_blank' rel='noopener'>Source</a>"
                "<div class='actions'><button data-action='approve'>✓ Approve</button>"
                "<button data-action='reject'>✗ Reject</button></div></article>"
            )
        markdown.append("")
        sections.append(
            f"<section><h2>{item.id:03d}. {html.escape(item.name)} — {len(rows)}/{summary['target_per_item']}</h2>"
            f"<div class='grid'>{''.join(cards)}</div></section>"
        )
    (output / "DESCRIPTIONS.md").write_text("\n".join(markdown), encoding="utf-8")

    css = """
    body{font-family:system-ui,sans-serif;background:#f4f4f4;margin:20px;color:#171717}
    header{position:sticky;top:0;background:#fff;padding:12px;z-index:10;border-bottom:1px solid #ddd}
    section{background:#fff;padding:16px;margin:16px 0;border-radius:10px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
    .card{border:1px solid #ddd;padding:8px;border-radius:8px}.card.approved{outline:3px solid #2e7d32}.card.rejected{opacity:.45;outline:3px solid #c62828}
    img{width:100%;aspect-ratio:16/10;object-fit:cover;border-radius:4px}b,small,a{display:block;margin-top:4px}.actions{display:flex;gap:6px;margin-top:8px}
    button,select{padding:7px 10px}button{cursor:pointer}
    """
    script = """
    const key='context-image-harvester-review-v1';
    const state=JSON.parse(localStorage.getItem(key)||'{}');
    function save(){localStorage.setItem(key,JSON.stringify(state));}
    function paint(card){card.classList.remove('approved','rejected');const v=state[card.dataset.file];if(v)card.classList.add(v);}
    document.querySelectorAll('.card').forEach(card=>{paint(card);card.querySelectorAll('button').forEach(btn=>btn.onclick=()=>{state[card.dataset.file]=btn.dataset.action==='approve'?'approved':'rejected';save();paint(card);});});
    function applyFilter(){const p=document.querySelector('#provider').value,r=document.querySelector('#rights').value,s=document.querySelector('#status').value;document.querySelectorAll('.card').forEach(c=>{const st=state[c.dataset.file]||'unreviewed';c.style.display=(!p||c.dataset.provider===p)&&(!r||c.dataset.rights===r)&&(!s||st===s)?'':'none';});}
    document.querySelectorAll('select').forEach(x=>x.onchange=applyFilter);
    function downloadStatus(status,name){const rows=[];document.querySelectorAll('.card').forEach(c=>{if((state[c.dataset.file]||'unreviewed')===status)rows.push({file:c.dataset.file,provider:c.dataset.provider,rights_status:c.dataset.rights});});const b=new Blob([JSON.stringify(rows,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=name;a.click();URL.revokeObjectURL(a.href);}
    """
    providers = sorted({record["provider"] for record in records})
    rights = sorted({record["rights_status"] for record in records})
    provider_options = "".join(f"<option value='{html.escape(v)}'>{html.escape(v)}</option>" for v in providers)
    rights_options = "".join(f"<option value='{html.escape(v)}'>{html.escape(v)}</option>" for v in rights)
    page = (
        "<!doctype html><meta charset='utf-8'><title>Image Review Pack</title>"
        f"<style>{css}</style><header><h1>Image Review Pack</h1>"
        f"Provider <select id='provider'><option value=''>All</option>{provider_options}</select> "
        f"Rights <select id='rights'><option value=''>All</option>{rights_options}</select> "
        "Status <select id='status'><option value=''>All</option><option>unreviewed</option><option>approved</option><option>rejected</option></select> "
        "<button onclick=\"downloadStatus('approved','approved.json')\">Export approved.json</button> "
        "<button onclick=\"downloadStatus('rejected','rejected.json')\">Export rejected.json</button></header>"
        + "".join(sections)
        + f"<script>{script}</script>"
    )
    (output / "CONTACT_SHEET.html").write_text(page, encoding="utf-8")


def make_zip(output: Path) -> Path:
    zip_path = output.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in output.rglob("*"):
            if path.is_file() and path.name != "state.json" and ".cache" not in path.parts:
                archive.write(path, path.relative_to(output.parent))
    return zip_path
