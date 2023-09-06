import os

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
TMP_DIR = os.path.join(SCRIPT_DIR, "tmp")
TWITCH_SECRET_PATH = os.path.join(SCRIPT_DIR, "twitch_client_secret.json")
YOUTUBE_SECRET_PATH = os.path.join(SCRIPT_DIR, "yt_client_secret.json")
GAME_IDS_PATH = os.path.join(SCRIPT_DIR, "game_ids.json")

TWITCH_OAUTH_URL = "https://id.twitch.tv/oauth2/token"
BASE_HELIX_URL = "https://api.twitch.tv/helix"
