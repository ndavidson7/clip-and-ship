import datetime
import webbrowser
from sys import exit as sys_exit

import requests

import constants
import utils


def request_oauth(twitch_secret: dict, num_fails: int = 0) -> str:
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    try:
        response = requests.post(
            constants.TWITCH_OAUTH_URL,
            headers=headers,
            data=twitch_secret,
            timeout=5,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(
            f"OAuth request returned HTTP Error. User credentials are likely invalid.\n\n{err}\n\n{response.text}"
        )
        raise
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as err:
        print(f"Twitch OAuth request error {err}.")

        num_fails += 1
        if num_fails > 3:
            print("Twitch OAuth request failed 3 times. Exiting...")
            sys_exit(1)

        print("Trying again...")
        return request_oauth(twitch_secret)

    if response.status_code == 200:
        print("Twitch OAuth received.")
        return response.json()["access_token"]

    print(f"Unhandled exception occurred: {response.status_code=}\n\n{response.text=}")
    sys_exit(1)


def get_game_id(game: str, headers: dict) -> str:
    # Check if game ID is already stored
    if game_id := __read_game_id_from_cache(game):
        print("Game ID retrieved.")
        return game_id

    # If not, request game ID from Twitch
    url = f"{constants.BASE_HELIX_URL}/games"
    params = {
        "name": game.title(),
    }

    # Loop until response data is not empty
    while not (
        data := requests.get(url, params=params, headers=headers).json()["data"]
    ):
        # If data is empty, the name was wrong. Try again with another name.
        # Note that game is not changed, so the informal name is saved in the game_ids file for easier future use.
        game = input(
            f'Could not find "{game}." What is the game\'s full name on Twitch? '
        )
        params["name"] = game.title()

    game_id = data[0]["id"]
    print("Game ID retrieved.")

    __write_game_id_to_cache(game, game_id)

    return game_id


def get_clips_data(
    game_id: str,
    headers: dict,
    num_clips: int,
    days_ago: int,
    cursor: str = None,
    video_length: int = 0,
) -> tuple[list[str], list[str], list[str]]:
    # Whether to manually choose clips one-by-one or simply get the top num_clips clips
    manual_mode = num_clips <= 0

    # Get date and time from days_ago days ago (in Twitch's format)
    started_at = utils.get_past_datetime(days_ago)

    # Request clips from Twitch
    print("Requesting clips...")
    url = f"{constants.BASE_HELIX_URL}/clips"
    params = {
        "game_id": game_id,
        "first": 20 if manual_mode else num_clips,
        "started_at": started_at,
        "after": cursor,
    }
    response = requests.get(url, params=params, headers=headers).json()

    clips = []  # download URLs
    slugs = []  # public Twitch clip URLs
    names = []  # streamer names
    for data in response["data"]:
        if manual_mode:
            # Open clip in browser
            webbrowser.open(data["url"])

            print(
                f"Current length of video: {datetime.timedelta(seconds=video_length)}\n"
                f'With current clip:       {datetime.timedelta(seconds=video_length+data["duration"])}'
            )

            choice = input("Include this clip in the video? (y, yf, n, nf): ").lower()
            while choice not in {"y", "n", "yf", "nf"}:
                print("Invalid choice.")
                choice = input(
                    "Include this clip in the video? (y, yf, n, nf): "
                ).lower()
            if "y" in choice:
                # update video length
                video_length += data["duration"]

                # Append data to lists
                __save_clip_data(data, clips, slugs, names)
            if "f" in choice:
                print("Clips chosen.")
                return clips, slugs, names
        else:
            # Append data to lists
            __save_clip_data(data, clips, slugs, names)

    if manual_mode or len(clips) < num_clips:
        # If we're in manual mode and haven't finished ('f' in choice) OR we're in automatic mode and the response did not include all clips, make another request
        # I don't like that this is recursive... maybe I'll revisit it later
        cursor = response["pagination"]["cursor"]
        num_clips -= len(clips)
        new_clips, new_slugs, new_names = get_clips_data(
            game_id, headers, num_clips, days_ago, cursor, video_length
        )
        clips.extend(new_clips)
        slugs.extend(new_slugs)
        names.extend(new_names)

        return clips, slugs, names

    print("Clips received.")
    return clips, slugs, names


def __save_clip_data(data, clips, slugs, names):
    # Get download url
    url = data["thumbnail_url"]
    splice_index = url.index("-preview")
    url = url[:splice_index] + ".mp4"

    # Save download url
    clips.append(url)

    # Save public clip url (a.k.a. slug)
    slugs.append(data["url"])

    # Save broadcaster name
    names.append(data["broadcaster_name"])


def __read_game_id_from_cache(game: str) -> str | None:
    game_ids = utils.read_json(constants.GAME_IDS_PATH)
    return game_ids.get(game.lower())


def __write_game_id_to_cache(game: str, game_id: str):
    game_ids = utils.read_json(constants.GAME_IDS_PATH)
    game_ids[game.lower()] = game_id
    utils.write_json(game_ids, constants.GAME_IDS_PATH)
