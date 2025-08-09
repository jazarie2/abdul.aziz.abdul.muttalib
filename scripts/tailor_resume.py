#!/usr/bin/env python3
import os
import re
import shutil
import sys
from pathlib import Path

import json

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

REPO_ROOT = Path(__file__).resolve().parents[1]
JOBS_DIR = REPO_ROOT / "jobs description"
TAILORED_DIR = REPO_ROOT / "tailored"

MAIN_TEX = REPO_ROOT / "main.tex"

PROMPT_TEMPLATE = (
    "You are an expert resume writer. Given the following resume LaTeX and a job description, "
    "produce a tailored 'Objective' line (one paragraph, <= 80 words) that best matches the JD, "
    "using the candidate's existing skills and experience. Return ONLY the tailored objective text.\n\n"
    "JOB DESCRIPTION:\n{jd}\n\n"
    "CANDIDATE CONTEXT (LaTeX header and skills excerpts):\n{ctx}\n"
)


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "job"


def read_job_descriptions() -> list[Path]:
    if not JOBS_DIR.exists():
        return []
    files = [
        p for p in JOBS_DIR.iterdir()
        if p.is_file()
        and p.suffix.lower() in {".md", ".txt"}
        and p.name.lower() != "readme.md"
    ]
    return sorted(files)


def extract_context_for_prompt() -> str:
    # Read key LaTeX files to give the model helpful context
    parts = []
    for fname in ["main.tex", "Skills.tex", "Experience.tex", "Education.tex"]:
        p = REPO_ROOT / fname
        if p.exists():
            try:
                text = p.read_text(encoding="utf-8")
            except Exception:
                text = ""
            # keep first ~4000 chars to control token size
            parts.append(f"===== {fname} =====\n" + text[:4000])
    return "\n\n".join(parts)


def call_openai_objective(jd_text: str, ctx: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY environment variable")
    if OpenAI is None:
        raise RuntimeError("openai package not installed")

    client = OpenAI(api_key=api_key)
    prompt = PROMPT_TEMPLATE.format(jd=jd_text, ctx=ctx)

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You rewrite resume objectives succinctly and professionally."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=220,
    )
    content = resp.choices[0].message.content.strip()
    # clean LaTeX-unfriendly unicode if needed
    return content


def tailor_main_tex(source_tex: Path, new_objective: str) -> str:
    tex = source_tex.read_text(encoding="utf-8")
    # Replace the \def\Objective{...} definition content
    pattern = r"(\\def\\Objective\{)(.*?)(\})"
    repl = r"\1" + new_objective.replace("\\", "\\\\").replace("\n", " ") + r"\3"
    new_tex, n = re.subn(pattern, repl, tex, flags=re.S)
    if n == 0:
        # If no Objective found, prepend a section
        insertion = f"\\newcommand{{\\Objective}}{{{new_objective}}}\n"
        new_tex = insertion + tex
    return new_tex


def write_tailored_copy(job_file: Path, new_objective: str) -> Path:
    job_slug = slugify(job_file.stem)
    out_dir = TAILORED_DIR / job_slug
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Copy all top-level .tex and directories used by main.tex
    for item in REPO_ROOT.iterdir():
        if item.name.startswith("."):
            continue
        if item == TAILORED_DIR or item == JOBS_DIR or item.name == "scripts":
            continue
        if item.suffix.lower() == ".tex" or item.is_dir() or item.name in {"latexmkrc", "ieee_collabratec_icon.png"}:
            dest = out_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

    # Update main.tex with tailored objective
    tailored_main = tailor_main_tex(out_dir / "main.tex", new_objective)
    (out_dir / "main.tex").write_text(tailored_main, encoding="utf-8")

    # Save JD for traceability
    shutil.copy2(job_file, out_dir / f"{job_slug}.txt")

    return out_dir


def main() -> int:
    job_files = read_job_descriptions()
    if not job_files:
        print("No job descriptions found; nothing to tailor.")
        return 0

    ctx = extract_context_for_prompt()

    errors: list[dict] = []
    results: list[dict] = []

    for jf in job_files:
        try:
            jd_text = jf.read_text(encoding="utf-8")
            objective = call_openai_objective(jd_text, ctx)
            out_dir = write_tailored_copy(jf, objective)
            results.append({"job": jf.name, "output": str(out_dir)})
            print(f"Tailored resume for {jf.name} -> {out_dir}")
        except Exception as exc:
            errors.append({"job": jf.name, "error": str(exc)})
            print(f"ERROR processing {jf.name}: {exc}", file=sys.stderr)

    report = {
        "results": results,
        "errors": errors,
    }
    (TAILORED_DIR / "report.json").parent.mkdir(parents=True, exist_ok=True)
    (TAILORED_DIR / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())