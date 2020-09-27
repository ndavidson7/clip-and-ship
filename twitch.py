import utils
import requests
import json
import datetime
from moviepy.editor import VideoFileClip, concatenate_videoclips

TWITCH_CS_FILENAME = 'twitch_client_secret.json'
GAME_IDS_FILENAME = 'game_ids.json'

def request_oauth():
    global TWITCH_CS
    TWITCH_CS = utils.read_json(TWITCH_CS_FILENAME)
    response = requests.post('https://id.twitch.tv/oauth2/token?', TWITCH_CS).text
    print("Twitch OAuth received.")
    return json.loads(response)["access_token"]

def get_id(game, oauth):
    game_ids = utils.read_json(GAME_IDS_FILENAME)
    if game.lower() in game_ids:
        print("Game ID retrieved.")
        return game_ids[game.lower()]

    url = 'https://api.twitch.tv/helix/games?name=' + game.title()
    headers = {"Authorization":"Bearer " + oauth, "Client-Id":TWITCH_CS["client_id"]}
    response = json.loads(requests.get(url, headers=headers).text)
    if response["data"] == []:
        official_name = input("Could not find "+game+". What is the official game name on Twitch? ")
        id = get_id(official_name, oauth)
        game_ids = utils.read_json(GAME_IDS_FILENAME)
        game_ids[game.lower()] = id
        utils.write_json(game_ids, GAME_IDS_FILENAME)
    else:
        id = response["data"][0]["id"]
        game_ids[game.lower()] = id
    utils.write_json(game_ids, GAME_IDS_FILENAME)
    print("Game ID retrieved.")
    return game_ids[game.lower()]

vid_length = 0

def manual_get_clips(game_id, oauth, days_ago, cursor=None):
    # Get date and time from days_ago days ago
    today = datetime.date.today()
    week_ago = (today - datetime.timedelta(days=days_ago)).strftime("%Y-%m-%d")
    start_date = week_ago + "T00:00:00.00Z"

    # Request clips from Twitch
    print("Requesting clips...")
    url = 'https://api.twitch.tv/helix/clips?'
    params = {"game_id":game_id, "first":"20", "started_at":start_date, "after":cursor}
    headers = {"Authorization":"Bearer " + oauth, "Client-Id":TWITCH_CS["client_id"]}
    response = json.loads(requests.get(url, params, headers=headers).text)

    clips = []
    slugs = []
    names = []
    temp_clips = []
    global vid_length
    for data in response["data"]:
        # get download link
        url = data["thumbnail_url"]
        splice_index = url.index("-preview")
        url = url[:splice_index] + ".mp4"
        temp_clips.append(url)

        video = utils.download_clips(temp_clips)

        utils.open_video("0.mp4")
        vfc = VideoFileClip("0.mp4")
        clip_duration = vfc.duration
        vfc.close()

        print("Current length of video: "+str(datetime.timedelta(seconds=vid_length))+"; length of video with current clip included: "+str(datetime.timedelta(seconds=(vid_length+clip_duration))))
        choice = input("Include this clip in the video? (y, yf, n, nf): ").lower()
        while(choice != 'y' and choice != 'n' and choice != 'yf' and choice != 'nf'):
            print("Invalid reponse")
            choice = input("Include this clip in the video? (y, yf, n, nf): ").lower()
        if('y' in choice):
            # update video length
            vid_length += clip_duration
            # save download link
            clips.append(url)
            # save public clip link (i.e., slug)
            slug = data["url"]
            slugs.append(slug)
            # save broadcaster name
            name = data["broadcaster_name"]
            names.append(name)
        if('f' in choice):
            utils.delete_mp4s(video)
            print("Clips chosen.")
            return clips, slugs, names

        utils.delete_mp4s(video)
        temp_clips = []

    # If we haven't finished ('f' in choice), make another request
    cursor = response['pagination']['cursor']
    new_clips, new_slugs, new_names = manual_get_clips(game_id, oauth, days_ago, cursor)
    clips.extend(new_clips)
    slugs.extend(new_slugs)
    names.extend(new_names)

    return clips, slugs, names

def auto_get_clips(game_id, oauth, num_clips, days_ago, cursor=None):
    # Get date and time from days_ago days ago
    today = datetime.date.today()
    week_ago = (today - datetime.timedelta(days=days_ago)).strftime("%Y-%m-%d")
    start_date = week_ago + "T00:00:00.00Z"

    # Request clips from Twitch
    print("Requesting clips...")
    url = 'https://api.twitch.tv/helix/clips?'
    params = {"game_id":game_id, "first":num_clips, "started_at":start_date, "after":cursor}
    headers = {"Authorization":"Bearer " + oauth, "Client-Id":TWITCH_CS["client_id"]}
    response = json.loads(requests.get(url, params, headers=headers).text)

    clips = []
    slugs = []
    names = []
    for data in response["data"]:
        # save download link
        url = data["thumbnail_url"]
        splice_index = url.index("-preview")
        clips.append(url[:splice_index] + ".mp4")
        # save public clip link (i.e., slug)
        url = data["url"]
        slugs.append(url)
        # save broadcaster name
        name = data["broadcaster_name"]
        names.append(name)
    # If response does not include all clips, request until all clips are returned
    if len(clips) < int(num_clips):
        cursor = response['pagination']['cursor']
        new_clips, new_slugs, new_names = auto_get_clips(game_id, oauth, str(int(num_clips)-len(clips)), days_ago, cursor)
        clips.extend(new_clips)
        slugs.extend(new_slugs)
        names.extend(new_names)

    print("Clips and slugs received.")
    return clips, slugs, names
