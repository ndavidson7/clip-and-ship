#!/usr/bin/env python3

import argparse, requests, json, pickle, os, time, random, http.client, httplib2, datetime
from moviepy.editor import VideoFileClip, concatenate_videoclips
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request



def run(args=None):
    game = args.game
    number = args.number
    days_ago = args.days_ago
    # oauth = get_oauth()
    # game_id = get_game_id(game, oauth)
    # clips, slugs = get_clips(game_id, oauth, number, days_ago)
    # videos = download_clips(clips)
    # durations = concatenate_clips(videos)
    # delete_clips(videos)
    print(upload_video(game)) # (durations, slugs)




def get_oauth():
    url = 'https://id.twitch.tv/oauth2/token?'
    params = {"client_id":"mxnht2zsdidy2roz676lo8qmmv8q8o", "client_secret":"541lihcbx8mrmznmsbh2ip7tj27uwo", "grant_type":"client_credentials"}
    response = requests.post(url, params).text
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
    game_ids = read_json("game_ids.json")
    if game.lower() in game_ids: return game_ids[game.lower()]

    url = 'https://api.twitch.tv/helix/games?name=' + game.title()
    headers = {"Authorization":"Bearer " + oauth, "Client-Id":"mxnht2zsdidy2roz676lo8qmmv8q8o"}
    response = requests.get(url, headers=headers).text
    response_json = json.loads(response)
    if response_json["data"] == []:
        official_name = input("Could not find "+game+". What is the official game name on Twitch? ")
        id = get_game_id(official_name, oauth)
        game_ids = read_json("game_ids.json")
        game_ids[game.lower()] = id
        write_json(game_ids, "game_ids.json")
    else:
        id = response_json["data"][0]["id"]
        game_ids[game.lower()] = id
    write_json(game_ids, "game_ids.json")
    return game_ids[game.lower()]




def get_clips(game_id, oauth, number, days_ago):
    today = datetime.date.today()
    week_ago = (today - datetime.timedelta(days=days_ago)).strftime("%Y-%m-%d")
    start_date = week_ago + "T00:00:00.00Z"
    url = 'https://api.twitch.tv/helix/clips?'
    params = {"game_id":game_id, "first":number, "started_at":start_date}
    headers = {"Authorization":"Bearer " + oauth, "Client-Id":"mxnht2zsdidy2roz676lo8qmmv8q8o"}
    response = requests.get(url, params, headers=headers).text
    response_json = json.loads(response)
    clips = []
    slugs = []
    for data in response_json["data"]:
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
    # print(client_secret_file, api_name, api_version, scopes, sep='-')
    CLIENT_SECRET_FILE = client_secret_file
    API_SERVICE_NAME = api_name
    API_VERSION = api_version
    SCOPES = [scope for scope in scopes[0]]
    # print(SCOPES)

    cred = None

    pickle_file = f'token_{API_SERVICE_NAME}_{API_VERSION}.pickle'
    # print(pickle_file)

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




def generate_description(durations, slugs):
    description = "00:00 - " + slugs[0] + "\n"
    for i in range(len(durations)):
        seconds = 0
        for d in range(i+1):
            seconds += durations[i]
        timestamp = time.strftime("%M:%S", time.gmtime(seconds))
        description += timestamp + " - " + slugs[i+1] + "\n"
    return description




def upload_video(game): # (durations, slugs)
    CLIENT_SECRET_FILE = 'client_secret.json'
    API_NAME = 'youtube'
    API_VERSION = 'v3'
    SCOPES = [
        'https://www.googleapis.com/auth/youtube.upload',
        'https://www.googleapis.com/auth/youtube.force-ssl',
        'https://www.googleapis.com/auth/youtube.readonly'
    ]

    service = Create_Service(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)

    # upload_request_body = {
    #     'snippet': {
    #         'categoryId': 20,
    #         'title': 'Test upload',
    #         'description': generate_description(durations, slugs),
    #         'tags': ['Test', 'multiple', 'tags']
    #     },
    #     'status': {
    #         'privacyStatus': 'private',
    #         'selfDeclaredMadeForKids': False
    #     }
    # }
    #
    # mediaFile = MediaFileUpload('final.mp4', chunksize=-1, resumable=True)
    #
    # response_upload = service.videos().insert(
    #     part='snippet,status',
    #     body=upload_request_body,
    #     media_body=mediaFile
    # )
    #
    # # Explicitly tell the underlying HTTP transport library not to retry, since
    # # we are handling retry logic ourselves.
    # httplib2.RETRIES = 1
    #
    # # Maximum number of times to retry before giving up.
    # MAX_RETRIES = 10
    #
    # # Always retry when these exceptions are raised.
    # RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
    #     http.client.IncompleteRead, http.client.ImproperConnectionState,
    #     http.client.CannotSendRequest, http.client.CannotSendHeader,
    #     http.client.ResponseNotReady, http.client.BadStatusLine)
    #
    # # Always retry when an apiclient.errors.HttpError with one of these status
    # # codes is raised.
    # RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
    #
    # # Upload the video... finally.
    # response = None
    # error = None
    # retry = 0
    # while response is None:
    #     try:
    #         print("Uploading file...")
    #         status, response = response_upload.next_chunk()
    #         if response is not None:
    #             if 'id' in response:
    #                 print("Video id '%s' was successfully uploaded." % response['id'])
    #         else:
    #             exit("The upload failed with an unexpected response: %s" % response)
    #     except HttpError as e:
    #         if e.resp.status in RETRIABLE_STATUS_CODES:
    #             error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status,e.content)
    #         else:
    #             raise
    #     except RETRIABLE_EXCEPTIONS as e:
    #         error = "A retriable error occurred: %s" % e
    #
    #     if error is not None:
    #         print(error)
    #         retry += 1
    #         if retry > MAX_RETRIES:
    #             exit("No longer attempting to retry.")
    #
    #         max_sleep = 2 ** retry
    #         sleep_seconds = random.random() * max_sleep
    #         print("Sleeping %f seconds and then retrying..." % sleep_seconds)
    #         time.sleep(sleep_seconds)

    # Get playlist ID
    playlist_id = get_playlist(game, service)
    return playlist_id




def get_playlist(game, service, pToken=None):
    game_ids = read_json()
    if game.lower() in game_ids: return game_ids[game.lower()]
    response_json = json.loads(response)
    if response_json["data"] == []:
        official_name = input("Could not find "+game+". What is the official game name on Twitch? ")
        id = get_game_id(official_name, oauth)
        game_ids = read_json()
        game_ids[game.lower()] = id
        write_json(game_ids)
    else:
        id = response_json["data"][0]["id"]
        game_ids[game.lower()] = id
    write_json(game_ids)
    return game_ids[game.lower()]


    # Get list of playlists on channel
    playlist_list_request = service.playlists().list(
        part="snippet,id",
        mine=True,
        pageToken=pToken
    )
    playlist_list_response = playlist_list_request.execute()

    # Find the playlist that our video belongs in
    playlist_id = '0'
    if playlist_list_response is not None:
        for item in playlist_list_response['items']:
            if game.lower() in item['snippet']['title'].lower():
                playlist_id = item['id']
                return playlist_id
        if playlist_id == '0':
            if 'nextPageToken' in playlist_list_response:
                nextPageToken = playlist_list_response['nextPageToken']
                playlist_id = get_playlist(service, nextPageToken)
            else:
                exit("No playlist found for " + game.title())




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
