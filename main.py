#!/usr/bin/env python3

import argparse
import twitch
import utils
import yt

def run(args=None):
    game = args.game
    num_clips = args.num_clips
    days_ago = args.days_ago

    # Communicate with Twitch API
    twitch_handler = twitch.TwitchHandler(game, num_clips, days_ago)
    twitch_handler.run()

    # Get clips and prepare video
    utils.download_clips(twitch_handler.clips)
    timestamps = utils.concatenate_clips(twitch_handler.names)

    # Upload video to YouTube
    yt.upload_video(game_id, timestamps, slugs, names)

    utils.delete_mp4s()
    print('----- DONE -----')

def main():
    parser = argparse.ArgumentParser(description='Download, concatenate, and upload Twitch clips')
    parser.add_argument('game', help='Game name', type=str)
    parser.add_argument('-n', '--num-clips', help='Number of clips to download (default: 0). If 0, script will download, play, and require inclusion or exclusion of each clip matching given arguments one by one', type=int, default=0)
    parser.add_argument('-d', '--days-ago', help='Number of days ago that clips started (default: 7). In other words, a value of 7 would return clips within the last week', type=int, default=7)
    parser.set_defaults(func=run)
    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
