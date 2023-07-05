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
            "https://id.twitch.tv/oauth2/token",
            headers=headers,
            data=twitch_secret,
            timeout=5,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print("OAuth request returned HTTP Error")
        print(err.args[0])
    except requests.exceptions.Timeout:
        print("Twitch OAuth request timed out. Trying again...")
        return request_oauth(twitch_secret)
    except requests.exceptions.ConnectionError:
        num_fails += 1
        if num_fails <= 3:
            print(f"Twitch OAuth request failed {num_fails} times." f"Trying again...")
            return request_oauth(num_fails)
        print("Twitch OAuth request failed 3 times. Exiting...")
        sys_exit()
    except requests.exceptions.RequestException:
        print("OAuth request caused a catastrophic error")

    if (oauth := response.json()["access_token"]) is not None:
        print("Twitch OAuth received.")
        return oauth

    raise ValueError(
        f"Twitch OAuth could not be retrieved. User credentials are likely invalid.\n{response.text}"
    )


def get_game_id(game: str, headers: dict) -> str:
    # Check if game ID is already stored
    game_ids = utils.read_json(constants.GAME_IDS_PATH)
    if game.lower() in game_ids:
        print("Game ID retrieved.")
        return game_ids[game.lower()]

    # If not, request game ID from Twitch
    url = "https://api.twitch.tv/helix/games"
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
    game_ids[game.lower()] = game_id
    utils.write_json(game_ids, constants.GAME_IDS_PATH)
    print("Game ID retrieved.")
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
    url = "https://api.twitch.tv/helix/clips"
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
