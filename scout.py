import os
import json
import requests
from googleapiclient.discovery import build

# --- HELPER FUNCTIONS ---

def get_uploads_playlist_id(channel_id):
    if channel_id and len(channel_id) > 2:
        return channel_id[:1] + 'U' + channel_id[2:]
    return channel_id

def send_telegram_alert(streamer_name, link, brand_suffix, platform, is_live=False):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    platform_icon = "🔴" if platform == "youtube" else "🟣" if platform == "twitch" else "🟢"
    status_text = "is LIVE right now" if is_live else "just uploaded a new video"
    
    # DISPATCHER COMMAND: Leads with /clip for the Colab Forge to hear
    message = (
        f"/clip {link}\n\n"
        f"❄️ **FR0ZEN SCOUT ALERT** ❄️\n\n"
        f"{platform_icon} **{streamer_name}** {status_text} on {platform.capitalize()}!\n"
        f"Brand Target: {brand_suffix}\n"
        f"*(Forge is now processing this link)*"
    )
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

# --- DISCOVERY MODULES ---

def discover_trending_twitch(client_id, access_token):
    print("🔎 Searching for trending Twitch streamers...")
    headers = {'Client-ID': client_id, 'Authorization': f'Bearer {access_token}'}
    url = "https://api.twitch.tv/helix/streams?first=5"
    try:
        response = requests.get(url, headers=headers).json()
        new_streamers = []
        for stream in response.get('data', []):
            new_streamers.append({
                "name": stream['user_name'],
                "platform": "twitch",
                "id": stream['user_login'],
                "brand": "Fr0zen_Waffle"
            })
        return new_streamers
    except: return []

def discover_trending_youtube(youtube_client):
    if not youtube_client: return []
    print("🔎 Searching for trending YouTube Gaming content...")
    try:
        request = youtube_client.videos().list(
            part="snippet",
            chart="mostPopular",
            videoCategoryId="20", # Gaming category
            maxResults=5,
            regionCode="US"
        )
        response = request.execute()
        new_youtubers = []
        for item in response.get('items', []):
            new_youtubers.append({
                "name": item['snippet']['channelTitle'],
                "platform": "youtube",
                "id": item['snippet']['channelId'],
                "brand": "Fr0zen_Waffle"
            })
        return new_youtubers
    except: return []

def discover_trending_kick():
    print("🔎 Searching for trending Kick streamers...")
    url = "https://kick.com/api/v1/channels" 
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        new_kickers = []
        for channel in data.get('data', [])[:5]:
            new_kickers.append({
                "name": channel['user']['username'],
                "platform": "kick",
                "id": channel['user']['username'],
                "brand": "Fr0zen_Waffle"
            })
        return new_kickers
    except: return []

def update_accounts_json(new_accounts):
    filename = 'accounts.json'
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            existing = json.load(f)
    else:
        existing = []
    
    existing_ids = {a.get('id') for a in existing}
    added = 0
    for acc in new_accounts:
        if acc['id'] not in existing_ids:
            existing.append(acc)
            existing_ids.add(acc['id'])
            added += 1
            
    if added > 0:
        with open(filename, 'w') as f:
            json.dump(existing, f, indent=4)
        print(f"✅ Added {added} new trending streamers to your list!")

# --- LIVE CHECK MODULES ---

def check_youtube_live_free(channel_id):
    url = f"https://www.youtube.com/channel/{channel_id}/live"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, allow_redirects=True)
        if "watch?v=" in response.url and ("isLiveNow" in response.text or "isLiveBroadcast" in response.text):
            return response.url.split("v=")[1].split("&")[0]
    except: pass
    return None

def get_twitch_token(client_id, client_secret):
    try:
        auth_url = f"https://id.twitch.tv/oauth2/token?client_id={client_id}&client_secret={client_secret}&grant_type=client_credentials"
        return requests.post(auth_url).json().get('access_token')
    except: return None

def check_twitch(username, client_id, token):
    if not token: return None
    try:
        headers = {'Client-ID': client_id, 'Authorization': f'Bearer {token}'}
        url = f"https://api.twitch.tv/helix/streams?user_login={username}"
        response = requests.get(url, headers=headers).json()
        if response.get('data'): return str(response['data'][0]['id'])
    except: return None

def check_kick(username):
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        url = f"https://kick.com/api/v1/channels/{username}"
        data = requests.get(url, headers=headers).json()
        if data.get('livestream'): return str(data['livestream']['id'])
    except: return None

# --- MAIN ENGINE ---

def main():
    # 1. Setup API Clients
    yt_key = os.environ.get('YT_API_KEY')
    youtube = build('youtube', 'v3', developerKey=yt_key) if yt_key else None
    t_id = os.environ.get('TWITCH_CLIENT_ID')
    t_sec = os.environ.get('TWITCH_CLIENT_SECRET')
    t_token = get_twitch_token(t_id, t_sec) if t_id else None

    # 2. DISCOVERY: Find trending content
    trend_t = discover_trending_twitch(t_id, t_token) if t_token else []
    trend_y = discover_trending_youtube(youtube)
    trend_k = discover_trending_kick()
    update_accounts_json(trend_t + trend_y + trend_k)

    # 3. LOAD: Refresh the expanded list
    with open('accounts.json', 'r') as f:
        streamers = json.load(f)
    
    memory_file = 'tracked_videos.json'
    tracked = json.load(open(memory_file, 'r')) if os.path.exists(memory_file) else {}
    updated_memory = False

    # 4. SCOUT: Check status of all targets
    for streamer in streamers:
        name = streamer.get('name')
        platform = streamer.get('platform', 'youtube').lower()
        acc_id = streamer.get('id')
        brand = streamer.get('brand', 'Fr0zen_Waffle')
        
        latest_id, link, is_live = None, "", False

        try:
            if platform == "youtube":
                latest_id = check_youtube_live_free(acc_id)
                if latest_id:
                    is_live = True
                    link = f"https://www.youtube.com/watch?v={latest_id}"
            elif platform == "twitch" and t_token:
                latest_id = check_twitch(acc_id, t_id, t_token)
                if latest_id:
                    is_live, link = True, f"https://www.twitch.tv/{acc_id}"
            elif platform == "kick":
                latest_id = check_kick(acc_id)
                if latest_id:
                    is_live, link = True, f"https://kick.com/{acc_id}"
        except: continue

        if latest_id:
            history = tracked.get(name, [])
            if latest_id not in history:
                print(f"🔥 Processing {name} on {platform}...")
                send_telegram_alert(name, link, brand, platform, is_live)
                history.append(latest_id)
                tracked[name] = history[-10:]
                updated_memory = True

    if updated_memory:
        with open(memory_file, 'w') as f:
            json.dump(tracked, f, indent=4)

if __name__ == "__main__":
    main()
