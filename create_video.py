#!/usr/bin/env python3

import argparse, requests, json, pickle, os, time, random, http.client, httplib2, datetime
from moviepy.editor import VideoFileClip, concatenate_videoclips
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request

TWITCH_CS_FILENAME = 'twitch_client_secret.json'
YOUTUBE_CS_FILENAME = 'yt_client_secret.json'
GAME_IDS_FILENAME = 'game_ids.json'


def run(args=None):
    game = args.game
    number = args.number
    days_ago = args.days_ago
    oauth = get_twitch_oauth()
    game_id = get_game_id(game, oauth)
    clips, slugs = get_clips(game_id, oauth, number, days_ago)
    videos = download_clips(clips)
    durations = concatenate_clips(videos)
    delete_clips(videos)
    upload_video(game_id, durations, slugs)




def get_twitch_oauth():
    global TWITCH_CS
    TWITCH_CS = read_json(TWITCH_CS_FILENAME)
    response = requests.post('https://id.twitch.tv/oauth2/token?', TWITCH_CS).text
    return json.loads(response)["access_token"]




def read_json(filename):
    try:
        with open(filename, "r") as f:
            return json.loads(f.read())
    except json.decoder.JSONDecodeError:
        write_json({}, filename)
        return read_json(filename)



def write_json(json_dict, filename):
    with open(filename, "wt") as f:
        json.dump(json_dict, f)




def get_game_id(game, oauth):
    game_ids = read_json(GAME_IDS_FILENAME)
    if game.lower() in game_ids: return game_ids[game.lower()]

    url = 'https://api.twitch.tv/helix/games?name=' + game.title()
    headers = {"Authorization":"Bearer " + oauth, "Client-Id":TWITCH_CS["client_id"]}
    response = json.loads(requests.get(url, headers=headers).text)
    if response["data"] == []:
        official_name = input("Could not find "+game+". What is the official game name on Twitch? ")
        id = get_game_id(official_name, oauth)
        game_ids = read_json(GAME_IDS_FILENAME)
        game_ids[game.lower()] = id
        write_json(game_ids, GAME_IDS_FILENAME)
    else:
        id = response["data"][0]["id"]
        game_ids[game.lower()] = id
    write_json(game_ids, GAME_IDS_FILENAME)
    return game_ids[game.lower()]




def get_clips(game_id, oauth, number, days_ago):
    today = datetime.date.today()
    week_ago = (today - datetime.timedelta(days=days_ago)).strftime("%Y-%m-%d")
    start_date = week_ago + "T00:00:00.00Z"
    url = 'https://api.twitch.tv/helix/clips?'
    params = {"game_id":game_id, "first":number, "started_at":start_date}
    headers = {"Authorization":"Bearer " + oauth, "Client-Id":TWITCH_CS["client_id"]}
    response = json.loads(requests.get(url, params, headers=headers).text)
    clips = []
    slugs = []
    for data in response["data"]:
        # get download links
        url = data["thumbnail_url"]
        splice_index = url.index("-preview")
        clips.append(url[:splice_index] + ".mp4")
        # get public clip links (i.e., slugs)
        url = data["url"]
        slugs.append(url)
    return clips, slugs




def download_clips(clips):
    videos = []
    for i in range(len(clips)):
        r = requests.get(clips[i], stream=True)
        name = str(i) + ".mp4"
        with open(name, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        videos.append(name)
    return videos




def delete_clips(videos):
    for video in videos:
        os.remove(video)




def concatenate_clips(videos):
    vfcs = []
    durations = []
    for video in videos:
        vfc = VideoFileClip(video, target_resolution=(1080, 1920))
        vfcs.append(vfc)
        if video is not videos[-1]:
            durations.append(vfc.duration)
    final_clip = concatenate_videoclips(vfcs)
    final_clip.write_videofile("final.mp4", temp_audiofile="temp-audio.m4a", remove_temp=True, audio_codec="aac")
    return durations




def Create_Service(client_secret_file, api_name, api_version, *scopes):
    CLIENT_SECRET_FILE = client_secret_file
    API_SERVICE_NAME = api_name
    API_VERSION = api_version
    SCOPES = [scope for scope in scopes[0]]

    cred = None

    pickle_file = f'token_{API_SERVICE_NAME}_{API_VERSION}.pickle'

    if os.path.exists(pickle_file):
        with open(pickle_file, 'rb') as token:
            cred = pickle.load(token)

    if not cred or not cred.valid:
        if cred and cred.expired and cred.refresh_token:
            cred.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            cred = flow.run_local_server()

        with open(pickle_file, 'wb') as token:
            pickle.dump(cred, token)

    try:
        service = build(API_SERVICE_NAME, API_VERSION, credentials=cred)
        print(API_SERVICE_NAME, 'service created successfully')
        return service
    except Exception as e:
        print('Unable to connect.')
        print(e)
        return None




def generate_title(playlist_title, video_count):
    return playlist_title +  " #" + str(video_count+1)




def generate_description(durations, slugs):
    description = "00:00 - " + slugs[0] + "\n"
    for i in range(len(durations)):
        seconds = 0
        for d in range(i+1):
            seconds += durations[i]
        timestamp = time.strftime("%M:%S", time.gmtime(seconds))
        description += timestamp + " - " + slugs[i+1] + "\n"
    return description




def upload_video(game_id, durations, slugs):
    API_NAME = 'youtube'
    API_VERSION = 'v3'
    SCOPES = ['https://www.googleapis.com/auth/youtube']

    service = Create_Service(YOUTUBE_CS_FILENAME, API_NAME, API_VERSION, SCOPES)

    # Get playlist ID, title, and video count
    playlist_id, playlist_title, video_count = get_playlist(game_id, service)

    upload_request_body = {
        'snippet': {
            'categoryId': 20,
            'title': generate_title(playlist_title, video_count),
            'description': generate_description(durations, slugs),
            'tags': ['Test', 'multiple', 'tags']
        },
        'status': {
            'privacyStatus': 'private',
            'selfDeclaredMadeForKids': False
        }
    }

    mediaFile = MediaFileUpload('final.mp4', chunksize=-1, resumable=True)

    response_upload = service.videos().insert(
        part='snippet,status',
        body=upload_request_body,
        media_body=mediaFile
    )

    # Explicitly tell the underlying HTTP transport library not to retry, since
    # we are handling retry logic ourselves.
    httplib2.RETRIES = 1

    # Maximum number of times to retry before giving up.
    MAX_RETRIES = 10

    # Always retry when these exceptions are raised.
    RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
        http.client.IncompleteRead, http.client.ImproperConnectionState,
        http.client.CannotSendRequest, http.client.CannotSendHeader,
        http.client.ResponseNotReady, http.client.BadStatusLine)

    # Always retry when an apiclient.errors.HttpError with one of these status
    # codes is raised.
    RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

    # Upload the video... finally.
    response = None
    error = None
    retry = 0
    video_id = ''
    while response is None:
        try:
            print("Uploading file...")
            status, response = response_upload.next_chunk()
            if response is not None:
                if 'id' in response:
                    video_id = response['id']
                    print("Video id '%s' was successfully uploaded." % response['id'])
            else:
                exit("The upload failed with an unexpected response: %s" % response)
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status,e.content)
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = "A retriable error occurred: %s" % e

        if error is not None:
            print(error)
            retry += 1
            if retry > MAX_RETRIES:
                exit("No longer attempting to retry.")

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            print("Sleeping %f seconds and then retrying..." % sleep_seconds)
            time.sleep(sleep_seconds)

    insert_to_playlist(service, playlist_id, video_id)




def get_playlist(game_id, service, pToken=None, playlist=None):
    # Check if playlist_id exists for game_id
    playlist_ids = read_json("playlist_ids.json")
    if game_id in playlist_ids: return playlist_ids[game_id]

    # If not, get list of playlists on channel
    playlist_list_request = service.playlists().list(
        part="snippet,id,contentDetails",
        mine=True,
        pageToken=pToken
    )
    playlist_list_response = playlist_list_request.execute()

    # Ask user for name of playlist
    if playlist is None:
        playlist = input("Game not yet attributed to a playlist. What is the full name of the playlist? ")

    # Find the playlist that our video belongs in
    playlist_id = '0'
    video_count = 0
    if playlist_list_response is None:
        exit("The playlist request failed with an unexpected response: %s" % response)

    for item in playlist_list_response['items']:
        playlist_title = item['snippet']['title']
        if playlist.lower() in playlist_title.lower():
            playlist_id = item['id']
            count = item['contentDetails']['itemCount']
            playlist_ids[game_id] = playlist_id, playlist_title, video_count
            write_json(playlist_ids, "playlist_ids.json")
            return playlist_id, playlist_title, video_count
    if playlist_id == '0':
        if 'nextPageToken' in playlist_list_response:
            nextPageToken = playlist_list_response['nextPageToken']
            return get_playlist(game_id, service, nextPageToken, playlist)
        else:
            exit("No playlist for the name given exists.")




def insert_to_playlist(service, playlist_id, video_id):
    playlist_insert_request = service.playlistItems().insert(
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
    playlist_insert_response = playlist_insert_request.execute()




def main():
    parser=argparse.ArgumentParser(description="Download, concatenate, and upload the 10 most viewed Twitch clips of the specified game in the past week")
    parser.add_argument("-g",help="Game name",dest="game",type=str,required=True)
    parser.add_argument("-n",help="Number of clips to use",dest="number",type=str,default="10")
    parser.add_argument("-d",help="Number of days ago that clips started",dest="days_ago",type=int,default=7)
    parser.set_defaults(func=run)
    args=parser.parse_args()
    args.func(args)




if __name__ == '__main__':
    main()
