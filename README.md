# YouTube Playlist Tools

Tool to manage YouTube playlists with a focus on:
1. Reading videos from your "Watch later" playlist
2. Adding those videos to a specific unlisted playlist
3. Removing all videos from the "Watch later" playlist

## Installation

### Prerequisites

- Python 3.8 or higher
- uv package manager: https://github.com/astral-sh/uv
- 1Password CLI: https://1password.com/downloads/command-line/

### Setup Steps

```bash
# Clone the repository
git clone https://github.com/yourusername/youtube-playlist-tools.git
cd youtube-playlist-tools

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
uv pip install -e .
```

## Setup

### YouTube API Credentials

1. Create a project in the [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the YouTube Data API v3:
   - In your project, go to APIs & Services > Library
   - Search for "YouTube Data API v3"
   - Click "Enable"

3. Create OAuth 2.0 credentials:
   - Go to APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop application" as the application type
   - Name your client (e.g., "YouTube Playlist Manager")
   - Click "Create"

4. Download the OAuth credentials:
   - After creating, you'll see a dialog with your client ID and client secret
   - Click the download icon to download the JSON file
   - Open the JSON file and note your client ID and client secret

5. Store your credentials in 1Password:
   - Create a new item in 1Password for your client ID
   - Create another item (or use the same one) for your client secret
   - Note the references (e.g., "op://vault-name/item-name/field-name")

### Configuration

1. Copy the template config file:
   ```bash
   cp youtube_playlist_tools/config.template.json youtube_playlist_tools/config.json
   ```
   
2. Edit the config file to add your 1Password references:
   ```json
   {
     "1password": {
       "youtube_oauth_client_id": "op://vault-name/item-name/field-name",
       "youtube_oauth_client_secret": "op://vault-name/item-name/field-name"
     },
     "playlists": {
       "watch_later_id": "WL",
       "target_unlisted_id": "PLwZYPD7MtnnyI36r-3Z6RbJQ__obH7FGu"
     }
   }
   ```

3. Make sure you're signed in to the 1Password CLI:
   ```bash
   op signin
   ```

## Usage

Run the script to move videos from "Watch later" to your target unlisted playlist:

```bash
# Dry run (no changes will be made)
yt-manage-playlists --dry-run

# Actual run
yt-manage-playlists
```

### First-Time Authorization

The first time you run the script, you'll be prompted to authorize the application to access your YouTube account:

1. A browser window will open automatically
2. Sign in to your Google Account
3. Review the permissions requested (YouTube access)
4. Click "Allow"
5. The browser will redirect to a success page
6. Return to the terminal where the script is running

After this one-time process, the script will save a refresh token that allows it to access your YouTube account without requiring authorization each time. The token is stored securely in `~/.yt_playlist_token.json`.

### Important OAuth Security Notes

- The OAuth flow is designed to protect your Google account credentials
- You never enter your Google password into the script
- All authorization is handled through Google's secure OAuth consent screen
- The script only has access to the specific YouTube permissions you approve
- You can revoke access at any time through your [Google Account Security settings](https://myaccount.google.com/security)

## Development

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Format code
black youtube_playlist_tools

# Lint code
ruff youtube_playlist_tools
```
