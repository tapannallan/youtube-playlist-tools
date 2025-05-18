#!/usr/bin/env python3
"""
Manage YouTube playlists:
1. Read videos from "Watch later" playlist
2. Add new videos to a specific unlisted playlist
3. Remove videos from "Watch later" playlist
"""

import json
import argparse
from typing import Dict, List
import subprocess
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tqdm import tqdm
import sys
import pprint

# YouTube API constants
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
SCOPES = ["https://www.googleapis.com/auth/youtube"]

# Default config values
DEFAULT_CONFIG = {
    "playlists": {
        "watch_later_id": "WL",  # This is a special ID for the "Watch later" playlist
        "target_unlisted_id": "PLwZYPD7MtnnyI36r-3Z6RbJQ__obH7FGu"
    }
}

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "youtube_playlist_tools" / "config.json"

def load_config() -> Dict:
    """
    Load configuration from config file or create default if not found.
    
    Returns:
        Dict: Configuration dictionary
    """
    # Check if config file exists
    if not CONFIG_PATH.exists():
        print(f"Warning: Config file not found at {CONFIG_PATH}")
        print("Using default config values.")
        return DEFAULT_CONFIG
    
    # Load config
    try:
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Error loading config file: {e}")
        print("Using default config values.")
        return DEFAULT_CONFIG


def get_secret_from_1password(reference: str) -> str:
    """
    Get a secret from 1Password using the op CLI.
    
    Args:
        reference: The 1Password reference (op://vault/item/field)
        
    Returns:
        str: The secret value
    """
    try:
        # This is the actual 1Password CLI command to get the secret
        return subprocess.check_output(["op", "read", reference]).decode().strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting secret from 1Password: {e}")
        print("Make sure you're signed in to 1Password CLI and the reference is correct.")
        sys.exit(1)


def get_api_key_from_1password(config: Dict) -> str:
    """
    Fetch the YouTube Data API key from 1Password.
    Returns the API key as a string.
    """
    api_key_ref = config.get("1password", {}).get("youtube_api_key")
    if not api_key_ref:
        print("Missing 1Password reference for YouTube API key.")
        sys.exit(1)
    try:
        api_key = get_secret_from_1password(api_key_ref)
        return api_key
    except Exception as e:
        print(f"Error retrieving API key from 1Password: {e}")
        sys.exit(1)


def get_authenticated_service(config: Dict) -> any:
    """
    Create and return a YouTube API service instance using an API key.
    """
    try:
        api_key = get_api_key_from_1password(config)
        return build(
            YOUTUBE_API_SERVICE_NAME,
            YOUTUBE_API_VERSION,
            developerKey=api_key
        )
    except Exception as e:
        print(f"Error building YouTube API service with API key: {e}")
        sys.exit(1)


def get_playlist_items(youtube, playlist_id: str) -> List[Dict]:
    """
    Get all videos in a playlist.
    
    Args:
        youtube: Authenticated YouTube API service
        playlist_id: ID of the playlist
        
    Returns:
        List[Dict]: List of playlist items with video IDs and titles
    """
    playlist_items = []
    next_page_token = None
    page_count = 0
    
    print(f"Fetching videos from playlist ID: {playlist_id}")
    
    try:
        while True:
            page_count += 1
            request = youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            )
            
            try:
                response = request.execute()
                
                if "items" not in response:
                    print("Warning: No items found in playlist response")
                    break
                
                for item in response["items"]:
                    try:
                        playlist_items.append({
                            "id": item["id"],  # Playlist item ID (needed for deletion)
                            "videoId": item["contentDetails"]["videoId"],
                            "title": item["snippet"]["title"]
                        })
                    except KeyError as e:
                        print(f"Warning: Skipping malformed playlist item: {e}")
                        continue
                
                # Print progress for large playlists
                if page_count % 5 == 0:
                    print(f"Retrieved {len(playlist_items)} videos so far...")
                
                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break
                    
            except HttpError as e:
                if e.resp.status == 404:
                    print(f"Error: Playlist not found (ID: {playlist_id})")
                elif e.resp.status == 403:
                    print(f"Error: Access forbidden to playlist (ID: {playlist_id})")
                    print("Make sure you have appropriate permissions and the playlist exists.")
                else:
                    print(f"Error retrieving playlist items: {e}")
                break
                
    except Exception as e:
        print(f"Unexpected error retrieving playlist: {e}")
    
    return playlist_items


def add_videos_to_playlist(youtube, playlist_id: str, video_ids: List[str]) -> int:
    """
    Add videos to a playlist.
    
    Args:
        youtube: Authenticated YouTube API service
        playlist_id: ID of the target playlist
        video_ids: List of video IDs to add
        
    Returns:
        int: Number of videos successfully added
    """
    count = 0
    
    if not video_ids:
        print("No new videos to add.")
        return 0
    
    print(f"Adding {len(video_ids)} videos to playlist ID: {playlist_id}")
    
    for video_id in tqdm(video_ids, desc="Adding videos"):
        request = youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id
                    }
                }
            }
        )
        
        try:
            request.execute()
            count += 1
        except HttpError as e:
            print(f"Error adding video {video_id}: {e}")
    
    return count


def remove_videos_from_playlist(youtube, playlist_items: List[Dict]) -> int:
    """
    Remove videos from a playlist.
    
    Args:
        youtube: Authenticated YouTube API service
        playlist_items: List of playlist items with their IDs
        
    Returns:
        int: Number of videos successfully removed
    """
    count = 0
    
    if not playlist_items:
        print("No videos to remove.")
        return 0
    
    print(f"Removing {len(playlist_items)} videos from 'Watch later' playlist")
    
    for item in tqdm(playlist_items, desc="Removing videos"):
        request = youtube.playlistItems().delete(
            id=item["id"]
        )
        
        try:
            request.execute()
            count += 1
        except HttpError as e:
            print(f"Error removing video {item['videoId']} ({item['title']}): {e}")
    
    return count


def find_new_videos(watch_later_videos: List[Dict], target_playlist_videos: List[Dict]) -> List[str]:
    """
    Find videos that are in watch_later but not in target_playlist.
    
    Args:
        watch_later_videos: List of videos in the Watch Later playlist
        target_playlist_videos: List of videos in the target playlist
        
    Returns:
        List[str]: List of video IDs that need to be added to the target playlist
    """
    target_video_ids = {item["videoId"] for item in target_playlist_videos}
    new_video_ids = [item["videoId"] for item in watch_later_videos if item["videoId"] not in target_video_ids]
    
    return new_video_ids


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Manage YouTube playlists")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without making any changes to playlists (read-only mode)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=str(CONFIG_PATH),
        help=f"Path to config file (default: {CONFIG_PATH})"
    )
    return parser.parse_args()
        

def main():
    """Main function to execute the script."""
    try:
        # Parse command-line arguments
        args = parse_arguments()
        
        # Update config path if specified
        global CONFIG_PATH
        if args.config != str(CONFIG_PATH):
            CONFIG_PATH = Path(args.config)
        
        # Load configuration
        config = load_config()
        watch_later_id = config.get("playlists", {}).get("watch_later_id", "WL")
        target_unlisted_id = config.get("playlists", {}).get("target_unlisted_id")
        
        if not target_unlisted_id:
            print("Error: Target unlisted playlist ID not specified in config.")
            print("Please update your config.json file with a valid target playlist ID.")
            sys.exit(1)
        
        print("Starting YouTube playlist management tool")
        print(f"Watch Later playlist ID: {watch_later_id}")
        print(f"Target unlisted playlist ID: {target_unlisted_id}")
        
        # Create an authenticated YouTube API service
        print("Authenticating with YouTube...")
        youtube = get_authenticated_service(config)
        
        # Step 1: Get videos from "Watch later" playlist
        print("\nRetrieving videos from 'Watch later' playlist...")
        watch_later_videos = get_playlist_items(youtube, watch_later_id)
        print(f"Found {len(watch_later_videos)} videos in 'Watch later' playlist")
        
        # Step 2: Get videos from target unlisted playlist
        print("\nRetrieving videos from target unlisted playlist...")
        target_playlist_videos = get_playlist_items(youtube, target_unlisted_id)
        print(f"Found {len(target_playlist_videos)} videos in target unlisted playlist")
        
        # Step 3: Find videos that need to be added to the target playlist
        print("\nFinding new videos to add...")
        new_video_ids = find_new_videos(watch_later_videos, target_playlist_videos)
        print(f"Found {len(new_video_ids)} new videos to add to target playlist")
        
        if args.dry_run:
            print("\n" + "="*50)
            print("DRY RUN MODE - No changes will be made to playlists")
            print("="*50)
            print("Summary (potential changes):")
            print(f"- Videos that would be added to unlisted playlist: {len(new_video_ids)}")
            print(f"- Videos that would be removed from 'Watch later' playlist: {len(watch_later_videos)}")
            return
        
        # Step 4: Add new videos to target playlist
        if new_video_ids:
            print("\nAdding new videos to target playlist...")
            videos_added = add_videos_to_playlist(youtube, target_unlisted_id, new_video_ids)
        else:
            print("\nNo new videos to add to target playlist")
            videos_added = 0
        
        # Step 5: Remove all videos from "Watch later" playlist
        if watch_later_videos:
            print("\nRemoving videos from 'Watch later' playlist...")
            videos_removed = remove_videos_from_playlist(youtube, watch_later_videos)
        else:
            print("\nNo videos to remove from 'Watch later' playlist")
            videos_removed = 0
        
        # Step 6: Display summary
        print("\n" + "="*50)
        print("Operation completed successfully!")
        print("="*50)
        print("Summary:")
        print(f"- Videos added to unlisted playlist: {videos_added}")
        print(f"- Videos removed from 'Watch later' playlist: {videos_removed}")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        print("Please check your configuration and try again")
        sys.exit(1)
    

if __name__ == "__main__":
    sys.argv = ['/Users/tapannallan/Workspace/codebase/personal/youtube-playlist-tools/youtube_playlist_tools/src/manage_playlists.py', '--config', 'youtube_playlist_tools/config.json']
    main()