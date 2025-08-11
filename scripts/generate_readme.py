#!/usr/bin/env python3
import re
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]

MAIN_TEX = REPO_ROOT / "main.tex"
EXPERIENCE_TEX = REPO_ROOT / "Experience.tex"
EDUCATION_TEX = REPO_ROOT / "Education.tex"
SKILLS_TEX = REPO_ROOT / "Skills.tex"
PATENTS_TEX = REPO_ROOT / "Patents-and-Publications.tex"
ADDITIONAL_TEX = REPO_ROOT / "Additional-Information.tex"
REFERENCES_TEX = REPO_ROOT / "References.tex"
README_MD = REPO_ROOT / "README.md"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def parse_definitions(tex: str) -> Dict[str, str]:
    defs: Dict[str, str] = {}
    i = 0
    n = len(tex)
    while i < n:
        if tex.startswith("\\def\\", i):
            i += len("\\def\\")
            # read name
            name_start = i
            while i < n and (tex[i].isalnum() or tex[i] == "_"):
                i += 1
            name = tex[name_start:i]
            # skip whitespace
            while i < n and tex[i].isspace():
                i += 1
            if i < n and tex[i] == '{':
                # parse balanced braces
                i += 1
                depth = 1
                val_start = i
                while i < n and depth > 0:
                    if tex[i] == '{':
                        depth += 1
                    elif tex[i] == '}':
                        depth -= 1
                    i += 1
                value = tex[val_start:i-1]
                if name:
                    defs[name] = value
            else:
                # not a standard def block; skip line
                while i < n and tex[i] != '\n':
                    i += 1
        else:
            i += 1
    return defs


def extract_mailto(tex: str) -> Tuple[str, str]:
    # returns (email, displayed_text)
    m = re.search(r"\\href\{mailto:([^}]+)\}\{([^}]+)\}", tex)
    if not m:
        return "", ""
    return m.group(1), m.group(2)


def latex_href_to_md(text: str) -> str:
    return re.sub(r"\\href\{([^}]+)\}\{([^}]+)\}", r"[\2](\1)", text)


def basic_latex_to_md(text: str) -> str:
    # Strip color/size wrappers early to simplify other patterns
    text = re.sub(r"\\textcolor\{[^}]*\}\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\scriptsize\b", "", text)
    text = re.sub(r"\\small\{", "", text)

    # Sections: capture cases like \section{\textbf{Title} \hfill ...}
    text = re.sub(r"\\section\{[^}]*?\\textbf\{([^}]*)\}[^}]*\}", r"## \1", text, flags=re.S)
    text = re.sub(r"\\section\{([^}]*)\}", r"## \1", text)

    # Replace common LaTeX constructs with Markdown equivalents
    text = text.replace("\\%", "%")
    text = text.replace("\\&", "&")
    text = text.replace("~", " ")
    text = text.replace("\\_", "_")
    text = text.replace("\\\\", "\n")
    text = re.sub(r"\\hfill", " — ", text)

    # Bold/italic
    text = re.sub(r"\\textbf\{([^}]*)\}", r"**\1**", text)
    text = re.sub(r"\\textit\{([^}]*)\}", r"_\1_", text)

    # Links
    text = latex_href_to_md(text)

    # Remove spacing commands
    text = re.sub(r"\\vspace\{[^}]*\}", "", text)

    # Itemize/enumerate environments and items
    text = re.sub(r"\\begin\{itemize\}[^\n]*\n", "", text)
    text = re.sub(r"\\end\{itemize\}[^\n]*\n?", "", text)
    text = re.sub(r"\\begin\{enumerate\}[^\n]*\n", "", text)
    text = re.sub(r"\\end\{enumerate\}[^\n]*\n?", "", text)
    text = re.sub(r"\n?\s*\\item\s+", "\n- ", text)

    # Generic cleanup of TeX commands we don't handle
    text = re.sub(r"\\resume\w+", "", text)
    text = re.sub(r"\\newcommand\{[^}]*\}\{[^}]*\}", "", text)

    # Remove stray closing braces
    text = re.sub(r"^\}\s*$", "", text, flags=re.M)

    # Whitespace normalization
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+$", "", text, flags=re.M)
    return text.strip() + "\n"


def convert_experience() -> str:
    header = "## Experience\n"
    tex = read_text(EXPERIENCE_TEX)
    if not tex:
        return ""
    entries = re.findall(r"\\input\{(Experience/[^}]+)\}", tex)
    parts: List[str] = []
    for rel in entries:
        path = REPO_ROOT / rel
        if not path.exists():
            path = path.with_suffix('.tex')
        raw = read_text(path)
        if not raw:
            continue
        s = basic_latex_to_md(raw)
        lines = [ln for ln in s.splitlines() if ln.strip()]
        if not lines:
            continue
        parts.append("\n".join(lines))
    return header + ("\n\n".join(parts) + "\n\n" if parts else "")


def convert_education() -> str:
    tex = read_text(EDUCATION_TEX)
    if not tex:
        return ""
    # Handle multi-line \resumeSubheading blocks
    tex = re.sub(
        r"\\resumeSubheading\s*\{([^}]*)\}\s*\{([^}]*)\}\s*\{([^}]*)\}\s*\{([^}]*)\}",
        lambda m: "\n".join([
            f"- **{m.group(1)}** — {m.group(2)} ({m.group(4)})",
            f"  - _{m.group(3)}_",
        ]),
        tex,
        flags=re.S,
    )
    tex = re.sub(r"\\resumeItemList(Start|End)|\\resumeSubHeadingList(Start|End)", "", tex)
    tex = re.sub(r"\n?\\item\s+", "\n- ", tex)
    body = basic_latex_to_md(tex)
    return body + "\n"


def convert_skills() -> str:
    tex = read_text(SKILLS_TEX)
    if not tex:
        return ""
    # Convert multi-line resumeSubItem blocks
    tex = re.sub(
        r"\\resumeSubItem\s*\{([^}]*)\}\s*\{([^}]*)\}",
        r"- **\1** \2",
        tex,
        flags=re.S,
    )
    tex = re.sub(r"\\resumeHeadingSkill(Start|End)", "", tex)
    body = basic_latex_to_md(tex)
    return body + "\n"


def convert_patents() -> str:
    tex = read_text(PATENTS_TEX)
    if not tex:
        return ""
    body = basic_latex_to_md(tex)
    return body + "\n"


def convert_additional() -> str:
    tex = read_text(ADDITIONAL_TEX)
    if not tex:
        return ""
    body = basic_latex_to_md(tex)
    return body + "\n"


def convert_references() -> str:
    tex = read_text(REFERENCES_TEX)
    if not tex:
        return ""
    body = basic_latex_to_md(tex)
    return body + "\n"


def build_header(defs: Dict[str, str], email: str) -> str:
    full_name = defs.get("fullName", "")
    github = defs.get("githubUsername", "").strip("{}")
    linkedin = defs.get("linkedinProfile", "").strip("{}")
    phone = defs.get("phoneNumber", "").lstrip("+")

    # Robustly parse location as [text](url) if possible
    loc_raw = defs.get("location", "")
    location_md = ""
    mloc = re.match(r"\\href\{([^}]+)\}\{([^}]+)\}", loc_raw)
    if mloc:
        location_md = f"[{mloc.group(2)}]({mloc.group(1)})"
    elif loc_raw:
        location_md = latex_href_to_md(loc_raw)

    lines: List[str] = []
    if full_name:
        lines.append(f"# {full_name}")
    contact: List[str] = []
    if phone:
        contact.append(f"+{phone}")
    if email:
        contact.append(email)
    if linkedin:
        contact.append(f"[LinkedIn](https://www.linkedin.com/in/{linkedin})")
    if github:
        contact.append(f"[GitHub](https://github.com/{github})")
    if location_md:
        contact.append(location_md)

    if contact:
        lines.append(" | ".join(contact))

    # Link to latest PDF in repo root if present
    if (REPO_ROOT / "resume.pdf").exists():
        lines.append("\n[Download the latest resume (PDF)](./resume.pdf)\n")

    return "\n\n".join(lines).strip() + "\n\n"


def build_objective(defs: Dict[str, str]) -> str:
    objective = defs.get("Objective", "")
    if not objective:
        return ""
    return f"## Objective\n\n{basic_latex_to_md(objective)}\n\n"


def generate_readme() -> str:
    main_tex = read_text(MAIN_TEX)
    defs = parse_definitions(main_tex)
    email, _ = extract_mailto(main_tex)

    parts: List[str] = []
    parts.append(build_header(defs, email))
    parts.append(build_objective(defs))

    # Sections in order as per main.tex
    parts.append(convert_experience())
    parts.append(convert_education())
    parts.append(convert_patents())
    parts.append(convert_skills())
    parts.append(convert_additional())
    parts.append(convert_references())

    content = "".join(p for p in parts if p)
    return content.strip() + "\n"


def main() -> int:
    md = generate_readme()
    README_MD.write_text(md, encoding="utf-8")
    print(f"Wrote {README_MD} ({len(md)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())