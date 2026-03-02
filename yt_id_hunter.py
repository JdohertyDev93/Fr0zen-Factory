import os
import json
from googleapiclient.discovery import build

# --- CONFIGURATION ---
# The script will grab your key from the environment, or you can paste it directly here for local testing
YT_API_KEY = os.environ.get('YT_API_KEY', 'YOUR_YOUTUBE_API_KEY_HERE') 

def resolve_youtube_ids():
    if not YT_API_KEY or YT_API_KEY == 'YOUR_YOUTUBE_API_KEY_HERE':
        print("❌ ERROR: Please enter your YouTube API Key.")
        return

    youtube = build('youtube', 'v3', developerKey=YT_API_KEY)
    filename = 'accounts.json'
    
    if not os.path.exists(filename):
        print(f"❌ ERROR: {filename} not found.")
        return

    with open(filename, 'r') as f:
        accounts = json.load(f)

    updated_count = 0
    print("🔎 Initializing YouTube ID Hunter...")

    for acc in accounts:
        # Only target YouTube accounts that don't have a valid UC... ID
        if acc.get('platform') == 'youtube' and not acc.get('id', '').startswith('UC'):
            target_name = acc['name']
            print(f"🕵️‍♂️ Hunting ID for: {target_name}...")
            
            try:
                # We use the 'search' endpoint to find the channel by name
                request = youtube.search().list(
                    part="snippet",
                    type="channel",
                    q=target_name,
                    maxResults=1
                )
                response = request.execute()
                
                if response.get('items'):
                    real_id = response['items'][0]['snippet']['channelId']
                    acc['id'] = real_id
                    print(f"   ✅ Found! Updated to: {real_id}")
                    updated_count += 1
                else:
                    print(f"   ⚠️ Could not find a channel for '{target_name}'.")
            except Exception as e:
                print(f"   ❌ API Error for {target_name}: {e}")

    # Save the corrected list back to the file
    if updated_count > 0:
        with open(filename, 'w') as f:
            json.dump(accounts, f, indent=4)
        print(f"\n🎯 MISSION COMPLETE. Successfully locked in {updated_count} new YouTube IDs.")
    else:
        print("\n✨ All YouTube accounts already have valid UC... IDs. Factory is clean.")

if __name__ == "__main__":
    resolve_youtube_ids()
