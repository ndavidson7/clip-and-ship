import utils
import constants
import requests
import json
import datetime
import webbrowser

TWITCH_SECRET = utils.read_json(constants.TWITCH_SECRET_PATH)

def request_oauth():
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    response = requests.post('https://id.twitch.tv/oauth2/token', headers=headers, data=TWITCH_SECRET).text

    if (oauth := json.loads(response)["access_token"]) is not None:
        print("Twitch OAuth received.")
        return oauth
    else:
        raise Exception(f"Twitch OAuth could not be received.\n{response}")

def get_id(game, oauth):
    # Check if game ID is already stored
    game_ids = utils.read_json(constants.GAME_IDS_PATH)
    if game.lower() in game_ids:
        print("Game ID retrieved.")
        return game_ids[game.lower()]

    # If not, request game ID from Twitch
    url = 'https://api.twitch.tv/helix/games'
    params = {
        "name": game.title(),
    }
    headers = {
        "Authorization": f"Bearer {oauth}",
        "Client-Id": TWITCH_SECRET["client_id"],
    }

    # Loop until response data is not empty
    while not (data := json.loads(requests.get(url, params=params, headers=headers).text)["data"]):
        # If data is empty, the name was wrong. Try again with another name.
        game = input(f'Could not find "{game}." What is the official game name on Twitch? ')
        params["name"] = game.title()

    id = data[0]["id"]
    game_ids[game.lower()] = id
    utils.write_json(game_ids, constants.GAME_IDS_PATH)
    print("Game ID retrieved.")
    return id

def manual_get_clips(game_id, oauth, days_ago, cursor=None, video_length=0):
    # Get date and time from days_ago days ago (in Twitch's format)
    started_at = utils.get_past_datetime(days_ago)

    # Request clips from Twitch
    print("Requesting clips...")
    url = 'https://api.twitch.tv/helix/clips'
    params = {
        "game_id": game_id,
        "first": "20",
        "started_at": started_at,
        "after": cursor,
    }
    headers = {
        "Authorization": f"Bearer {oauth}",
        "Client-Id": TWITCH_SECRET["client_id"],
    }
    response = json.loads(requests.get(url, params=params, headers=headers).text)

    clips = [] # download URLs
    slugs = [] # public Twitch clip URLs
    names = [] # streamer names
    for data in response["data"]:
        # Open clip in browser
        webbrowser.open(data["url"])

        print(f"Current length of video: {datetime.timedelta(seconds=video_length)}; length of video with current clip included: {datetime.timedelta(seconds=video_length+data['duration'])}")
        choice = input("Include this clip in the video? (y, yf, n, nf): ").lower()
        while choice != 'y' and choice != 'n' and choice != 'yf' and choice != 'nf':
            print("Invalid choice.")
            choice = input("Include this clip in the video? (y, yf, n, nf): ").lower()
        if 'y' in choice:
            # update video length
            video_length += data['duration']

            # get download url
            url = data["thumbnail_url"]
            splice_index = url.index("-preview")
            url = url[:splice_index] + ".mp4"

            # save download url
            clips.append(url)

            # save public clip url (a.k.a. slug)
            slugs.append(data["url"])

            # save broadcaster name
            names.append(data["broadcaster_name"])
        if 'f' in choice:
            print("Clips chosen.")
            return clips, slugs, names

    # If we haven't finished ('f' in choice), make another request
    # I don't like that this is recursive... maybe I'll revisit it later
    cursor = response['pagination']['cursor']
    new_clips, new_slugs, new_names = manual_get_clips(game_id, oauth, days_ago, cursor, video_length)
    clips.extend(new_clips)
    slugs.extend(new_slugs)
    names.extend(new_names)

    return clips, slugs, names

def auto_get_clips(game_id, oauth, num_clips, days_ago, cursor=None):
    # Get date and time from days_ago days ago (in Twitch's format)
    started_at = utils.get_past_datetime(days_ago)

    # Request clips from Twitch
    print("Requesting clips...")
    url = 'https://api.twitch.tv/helix/clips'
    params = {
        "game_id": game_id,
        "first": num_clips,
        "started_at": started_at,
        "after": cursor,
    }
    headers = {
        "Authorization": f"Bearer {oauth}",
        "Client-Id": TWITCH_SECRET["client_id"]
    }
    response = json.loads(requests.get(url, params=params, headers=headers).text)

    clips = [] # download URLs
    slugs = [] # public Twitch clip URLs
    names = [] # streamer names
    for data in response["data"]:
        # get download url
        url = data["thumbnail_url"]
        splice_index = url.index("-preview")
        url = url[:splice_index] + ".mp4"

        # save download url
        clips.append(url)

        # save public clip url (a.k.a. slug)
        slugs.append(data["url"])

        # save broadcaster name
        names.append(data["broadcaster_name"])
    # If response does not include all clips, request until all clips are returned
    if len(clips) < num_clips:
        cursor = response['pagination']['cursor']
        new_clips, new_slugs, new_names = auto_get_clips(game_id, oauth, num_clips-len(clips), days_ago, cursor)
        clips.extend(new_clips)
        slugs.extend(new_slugs)
        names.extend(new_names)

    print("Clips received.")
    return clips, slugs, names
