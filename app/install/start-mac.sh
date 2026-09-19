#!/bin/bash
cd "$(dirname "$0")/../.."
export PATH="$HOME/.local/bin:$PATH"
uv run app/jobs.py update
exec uv run app/jobs.py launch
