import os
import json
import requests
from googleapiclient.discovery import build

def get_uploads_playlist_id(channel_id):
    # Replaces the second letter of a Channel ID from 'C' to 'U' to get the Uploads playlist
    if channel_id and len(channel_id) > 2:
        return channel_id[:1] + 'U' + channel_id[2:]
    return channel_id

def send_telegram_alert(streamer_name, video_id, brand_suffix):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    message = (
        f"❄️ **FR0ZEN SCOUT ALERT** ❄️\n\n"
        f"New content detected for: **{streamer_name}**\n"
        f"Brand Target: {brand_suffix}\n\n"
        f"Link: {video_url}\n\n"
        f"*(Open Colab to start the Fr0zen Edit)*"
    )
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def main():
    # 1. Load your streamers safely (handles both Lists and Dictionaries)
    with open('accounts.json', 'r') as f:
        data = json.load(f)
        
    if isinstance(data, list):
        streamers = data
    else:
        streamers = data.get('accounts', [])

    # 2. Load "Memory"
    memory_file = 'tracked_videos.json'
    if os.path.exists(memory_file):
        with open(memory_file, 'r') as f:
            tracked = json.load(f)
    else:
        tracked = {}

    # 3. Connect to YouTube
    youtube = build('youtube', 'v3', developerKey=os.environ['YT_API_KEY'])
    updated = False

    # 4. Check each streamer
    for streamer in streamers:
        # Safely grab the keys regardless of how you named them in accounts.json
        name = streamer.get('name') or streamer.get('streamer_name')
        channel_id = streamer.get('id') or streamer.get('yt_channel_id')
        brand = streamer.get('brand') or streamer.get('brand_suffix')
        
        if not channel_id:
            continue

        playlist_id = get_uploads_playlist_id(channel_id)
        
        try:
            request = youtube.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=1
            )
            response = request.execute()
            
            if response['items']:
                latest_video_id = response['items'][0]['snippet']['resourceId']['videoId']
                
                if tracked.get(name) != latest_video_id:
                    print(f"New video found for {name}: {latest_video_id}")
                    send_telegram_alert(name, latest_video_id, brand)
                    tracked[name] = latest_video_id
                    updated = True
                else:
                    print(f"No new videos for {name}.")
                    
        except Exception as e:
            print(f"Error checking {name}: {e}")

    # 5. Save memory
    if updated:
        with open(memory_file, 'w') as f:
            json.dump(tracked, f, indent=4)

if __name__ == "__main__":
    main()
