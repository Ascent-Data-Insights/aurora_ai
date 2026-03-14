# Project Conventions

## Package Management
- Always use `uv` for Python dependency management (not pip, not pipenv, not poetry)

## Running Tests
- Tests require dev dependencies: `cd backend && uv run --extra dev pytest`
- Do NOT use bare `uv run pytest` — it will fail because pytest is in `[project.optional-dependencies] dev`
