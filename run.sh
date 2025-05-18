#!/bin/bash

# Activate virtual environment
source .venv/bin/activate

# Run the YouTube playlist management tool
if [ "$1" == "--dry-run" ]; then
    python -m youtube_playlist_tools.src.manage_playlists --dry-run
else
    python -m youtube_playlist_tools.src.manage_playlists "$@"
fi