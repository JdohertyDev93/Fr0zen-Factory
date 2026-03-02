import os
import json
import requests
from googleapiclient.discovery import build

def get_uploads_playlist_id(channel_id):
    if channel_id and len(channel_id) > 2:
        return channel_id[:1] + 'U' + channel_id[2:]
    return channel_id

def send_telegram_alert(streamer_name, link, brand_suffix, platform, is_live=False):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    platform_icon = "🔴" if platform == "youtube" else "🟣" if platform == "twitch" else "🟢"
    status_text = "is LIVE right now" if is_live else "just uploaded a new video"
    
    message = (
        f"❄️ **FR0ZEN SCOUT ALERT** ❄️\n\n"
        f"{platform_icon} **{streamer_name}** {status_text} on {platform.capitalize()}!\n"
        f"Brand Target: {brand_suffix}\n\n"
        f"Link: {link}\n\n"
        f"*(Open Colab to start the Fr0zen Edit)*"
    )
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def check_youtube_live_free(channel_id):
    url = f"https://www.youtube.com/channel/{channel_id}/live"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    try:
        response = requests.get(url, headers=headers, allow_redirects=True)
        if "watch?v=" in response.url:
            video_id = response.url.split("v=")[1].split("&")[0]
            if "isLiveNow" in response.text or "isLiveBroadcast" in response.text:
                return video_id
    except Exception as e:
        print(f"YouTube Live check failed for {channel_id}: {e}")
    return None

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
            return str(response['data'][0]['id'])
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
        print(f"Kick check failed for {username}: {e}")
    return None

def main():
    # 1. Load Accounts
    with open('accounts.json', 'r') as f:
        data = json.load(f)
    streamers = data if isinstance(data, list) else data.get('accounts', [])

    # 2. Load Memory (Now supports lists!)
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
        platform = streamer.get('platform', 'youtube').lower()
        account_id = streamer.get('id') or streamer.get('yt_channel_id')
        brand = streamer.get('brand') or streamer.get('brand_suffix')
        
        if not account_id:
            continue

        latest_id = None
        link = ""
        is_live = False

        try:
            if platform == "youtube":
                latest_id = check_youtube_live_free(account_id)
                if latest_id:
                    is_live = True
                    link = f"https://www.youtube.com/watch?v={latest_id}"
                
                if not latest_id and youtube:
                    playlist_id = get_uploads_playlist_id(account_id)
                    request = youtube.playlistItems().list(part="snippet", playlistId=playlist_id, maxResults=1)
                    response = request.execute()
                    if response.get('items'):
                        latest_id = response['items'][0]['snippet']['resourceId']['videoId']
                        link = f"https://www.youtube.com/watch?v={latest_id}"

            elif platform == "twitch" and twitch_token:
                latest_id = check_twitch(account_id, twitch_client_id, twitch_token)
                if latest_id:
                    is_live = True
                    link = f"https://www.twitch.tv/{account_id}"

            elif platform == "kick":
                latest_id = check_kick(account_id)
                if latest_id:
                    is_live = True
                    link = f"https://kick.com/{account_id}"
                
        except Exception as e:
            print(f"Error checking {name} on {platform}: {e}")
            continue

        # 5. Alert if New Content Found
        if latest_id:
            # Grab the streamer's history (convert old strings to lists if needed)
            history = tracked.get(name, [])
            if isinstance(history, str):
                history = [history]

            if latest_id not in history:
                print(f"New content found for {name} on {platform}: {latest_id}")
                send_telegram_alert(name, link, brand, platform, is_live)
                
                # Add to history and keep only the last 10 to save space
                history.append(latest_id)
                tracked[name] = history[-10:] 
                updated = True
            else:
                print(f"Content {latest_id} for {name} has already been processed.")

    # 6. Save Memory
    if updated:
        with open(memory_file, 'w') as f:
            json.dump(tracked, f, indent=4)

if __name__ == "__main__":
    main()
