#!/usr/bin/env python3

import argparse
from sys import exit as sys_exit

import constants
import twitch
import utils
import yt


def run(args=None):
    game = args.game
    num_clips = args.num_clips
    days_ago = args.days_ago
    yt_upload = args.youtube

    # Communicate with Twitch API
    twitch_secret = utils.read_json(constants.TWITCH_SECRET_PATH)
    oauth = twitch.request_oauth(twitch_secret)
    twitch_headers = {  # Headers for all Twitch API requests
        "Authorization": f"Bearer {oauth}",
        "Client-Id": twitch_secret["client_id"],
    }
    game_id = twitch.get_game_id(game, twitch_headers)
    clips, slugs, names = twitch.get_clips_data(
        game_id, twitch_headers, num_clips, days_ago
    )

    # If user decided not to include any clips, exit
    if not clips:
        print("No clips included. Exiting...")
        sys_exit()

    # Get clips and prepare video
    utils.download_clips(clips)
    timestamps = utils.concatenate_clips(names)

    # Upload video to YouTube
    if yt_upload:
        yt.upload_video(game_id, timestamps, slugs, names)
        utils.delete_mp4s()

    print("\n      DONE\n")


def main():
    parser = argparse.ArgumentParser(
        description="Download, concatenate, and upload Twitch clips"
    )
    parser.add_argument("game", help="Game name", type=str)
    parser.add_argument(
        "-n",
        "--num-clips",
        help="Number of clips to download (default: 0). If 0, script will download, play, and require inclusion or exclusion of each clip matching given arguments one by one",
        type=int,
        default=0,
    )
    parser.add_argument(
        "-d",
        "--days-ago",
        help="Number of days ago that clips started (default: 7). In other words, a value of 7 would return clips within the last week",
        type=int,
        default=7,
    )
    parser.add_argument(
        "-yt", "--youtube", help="Whether to upload to YouTube", action="store_true"
    )
    parser.set_defaults(func=run)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
