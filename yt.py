import pickle
import os
import datetime
import utils
import httplib2
import http.client
import random
import time
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request

YOUTUBE_CS_FILENAME = 'yt_client_secret.json'

def create_service(client_secret_file, api_name, api_version, *scopes):
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
        print(API_SERVICE_NAME.title(), 'service created successfully')
        return service
    except Exception as e:
        print('Unable to connect.')
        print(e)
        return None

def generate_title(playlist_title, video_count):
    return playlist_title +  " #" + str(video_count+1)

def generate_description(timestamps, slugs):
    description = "Join our Discord to submit clips! https://discord.gg/Th55ADV \n"
    for i in range(len(timestamps)):
        timestamp = str(datetime.timedelta(seconds=round(timestamps[i])))
        description += "\n" + timestamp + " - " + slugs[i]
    return description

def generate_tags(game_id, names):
    all_tags = utils.read_json("tags.json")
    game_tags = all_tags[game_id]
    game_tags.extend([name.lower() for name in names])
    video_tags = list(set(game_tags))
    return video_tags

def upload_video(game_id, timestamps, slugs, names):
    API_NAME = 'youtube'
    API_VERSION = 'v3'
    SCOPES = ['https://www.googleapis.com/auth/youtube']

    service = create_service(YOUTUBE_CS_FILENAME, API_NAME, API_VERSION, SCOPES)

    # Get playlist ID, title, and video count
    playlist_id, playlist_title, video_count = get_playlist(game_id, service)

    upload_request_body = {
        'snippet': {
            'categoryId': 20,
            'title': generate_title(playlist_title, video_count),
            'description': generate_description(timestamps, slugs),
            'tags': generate_tags(game_id, names)
        },
        'status': {
            'privacyStatus': 'private',
            'selfDeclaredMadeForKids': False
        }
    }

    mediaFile = MediaFileUpload('final.mp4', chunksize=-1, resumable=True)

    video_insert_request = service.videos().insert(
        part="snippet,status",
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
            print("Uploading video...")
            status, response = video_insert_request.next_chunk()
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

    # Wait for YouTube to process the upload
    time.sleep(60)
    # Insert video into playlist and update local playlist info
    insert_to_playlist(service, game_id, playlist_id, video_id)

def get_playlist(game_id, service, pToken=None, playlist=None):
    # Check if playlist_id exists for game_id
    playlist_ids = utils.read_json("playlist_ids.json")
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
            utils.write_json(playlist_ids, "playlist_ids.json")
            return playlist_id, playlist_title, video_count
    if playlist_id == '0':
        if 'nextPageToken' in playlist_list_response:
            nextPageToken = playlist_list_response['nextPageToken']
            return get_playlist(game_id, service, nextPageToken, playlist)
        else:
            exit("No playlist for the name given exists.")

def insert_to_playlist(service, game_id, playlist_id, video_id):
    # Insert video into playlist
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
    try:
        playlist_insert_response = playlist_insert_request.execute()
    except HttpError:
        print("Video added to playlist.")
        pass

    # Increment local playlist video count
    playlist_ids = utils.read_json("playlist_ids.json")
    playlist_ids[game_id][2] += 1
    utils.write_json(playlist_ids, "playlist_ids.json")
