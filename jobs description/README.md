# Jobs Description

Place one or more job descriptions here as `.md` or `.txt` files. On push/merge to `main`, the CI will:

- Use AI to tailor the resume Objective to each job description
- Copy the LaTeX sources into `tailored/<job-slug>/`
- Build a PDF for each tailored resume and upload as workflow artifacts

## How to use
- Add files like `senior-validation-engineer.md`, `staff-rtl-designer.txt`, etc.
- Keep 1 role per file. Use clear responsibilities and requirements.
- Merge to `main` (or trigger the workflow manually). Artifacts will include PDFs for each JD.

## Secrets
This workflow requires `OPENAI_API_KEY` configured in repository secrets.