import os
import json
import requests
from googleapiclient.discovery import build

def get_uploads_playlist_id(channel_id):
    if channel_id and len(channel_id) > 2:
        return channel_id[:1] + 'U' + channel_id[2:]
    return channel_id

def send_telegram_alert(streamer_name, link, brand_suffix, platform):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    platform_icon = "🔴" if platform == "youtube" else "🟣" if platform == "twitch" else "🟢"
    
    message = (
        f"❄️ **FR0ZEN SCOUT ALERT** ❄️\n\n"
        f"{platform_icon} **{streamer_name}** is active on {platform.capitalize()}!\n"
        f"Brand Target: {brand_suffix}\n\n"
        f"Link: {link}\n\n"
        f"*(Open Colab to start the Fr0zen Edit)*"
    )
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def get_twitch_token(client_id, client_secret):
    try:
        auth_url = f"https://id.twitch.tv/oauth2/token?client_id={client_id}&client_secret={client_secret}&grant_type=client_credentials"
        response = requests.post(auth_url).json()
        return response.get('access_token')
    except:
        return None

def check_twitch(username, client_id, access_token):
    if not access_token:
        return None
    try:
        headers = {'Client-ID': client_id, 'Authorization': f'Bearer {access_token}'}
        url = f"https://api.twitch.tv/helix/streams?user_login={username}"
        response = requests.get(url, headers=headers).json()
        if response.get('data'):
            return str(response['data'][0]['id']) # Return the unique stream ID
    except Exception as e:
        print(f"Twitch check failed for {username}: {e}")
    return None

def check_kick(username):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }
        url = f"https://kick.com/api/v1/channels/{username}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            livestream = data.get('livestream')
            if livestream:
                return str(livestream['id'])
    except Exception as e:
        print(f"Kick check failed for {username}. Might be rate-limited: {e}")
    return None

def main():
    # 1. Load Accounts
    with open('accounts.json', 'r') as f:
        data = json.load(f)
        
    streamers = data if isinstance(data, list) else data.get('accounts', [])

    # 2. Load Memory
    memory_file = 'tracked_videos.json'
    if os.path.exists(memory_file):
        with open(memory_file, 'r') as f:
            tracked = json.load(f)
    else:
        tracked = {}

    # 3. Setup API Clients
    youtube_key = os.environ.get('YT_API_KEY')
    youtube = build('youtube', 'v3', developerKey=youtube_key) if youtube_key else None
    
    twitch_client_id = os.environ.get('TWITCH_CLIENT_ID')
    twitch_client_secret = os.environ.get('TWITCH_CLIENT_SECRET')
    twitch_token = get_twitch_token(twitch_client_id, twitch_client_secret) if twitch_client_id else None

    updated = False

    # 4. Check Each Streamer
    for streamer in streamers:
        name = streamer.get('name') or streamer.get('streamer_name')
        platform = streamer.get('platform', 'youtube').lower() # Defaults to youtube if missing
        account_id = streamer.get('id') or streamer.get('yt_channel_id')
        brand = streamer.get('brand') or streamer.get('brand_suffix')
        
        if not account_id:
            continue

        latest_id = None
        link = ""

        try:
            if platform == "youtube" and youtube:
                playlist_id = get_uploads_playlist_id(account_id)
                request = youtube.playlistItems().list(part="snippet", playlistId=playlist_id, maxResults=1)
                response = request.execute()
                if response.get('items'):
                    latest_id = response['items'][0]['snippet']['resourceId']['videoId']
                    link = f"https://www.youtube.com/watch?v={latest_id}"

            elif platform == "twitch" and twitch_token:
                latest_id = check_twitch(account_id, twitch_client_id, twitch_token)
                link = f"https://www.twitch.tv/{account_id}"

            elif platform == "kick":
                latest_id = check_kick(account_id)
                link = f"https://kick.com/{account_id}"
                
        except Exception as e:
            print(f"Error checking {name} on {platform}: {e}")
            continue

        # 5. Alert if New Content Found
        if latest_id:
            if tracked.get(name) != latest_id:
                print(f"New content found for {name} on {platform}: {latest_id}")
                send_telegram_alert(name, link, brand, platform)
                tracked[name] = latest_id
                updated = True
            else:
                print(f"No new content for {name} on {platform}.")

    # 6. Save Memory
    if updated:
        with open(memory_file, 'w') as f:
            json.dump(tracked, f, indent=4)

if __name__ == "__main__":
    main()
