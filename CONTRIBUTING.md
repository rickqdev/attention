# Contributing To attention

Thanks for helping make `attention` more useful for creators and developers.

## What To Open Where

Use GitHub Discussions for:
- questions about setup or usage
- workflow ideas
- public feedback on creator or developer use cases

Use GitHub Issues for:
- reproducible bugs
- scoped feature requests
- structured use case submissions

## Good First Contributions

- improve the quickstart flow for non-technical users
- tighten API or MCP documentation
- add public example use cases
- improve error messages and recovery guidance
- refine demo UX without hiding the BYOK model

## Local Setup

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -e .
pytest
```

Useful entry points:
- `python3 app.py --inbrowser`
- `attention-api --host 127.0.0.1 --port 8000`
- `attention-mcp`

## Pull Request Guidelines

- keep changes focused on one user-visible improvement
- include before/after notes for README, docs, or UI changes
- mention whether the change targets creators, developers, or both
- update docs or examples when public behavior changes
- do not commit real keys, real photos, or generated private outputs

## Example Contributions

If you add a public example:
- use a scenario that can be shared safely
- explain the image pattern and expected hook
- avoid claims that require unpublished or private data

## Testing Expectations

- run `pytest` for code changes
- test the browser demo locally when the UI changes
- smoke-test one API or MCP flow when integration behavior changes
