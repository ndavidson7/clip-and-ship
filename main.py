#!/usr/bin/env python3

import argparse
import twitch
import utils
import yt

def run(args=None):
    game = args.game
    days_ago = args.days_ago
    num_clips = args.num_clips
    oauth = twitch.request_oauth()
    game_id = twitch.get_id(game, oauth)
    clips = []
    slugs = []
    names = []

    if(num_clips is None):
        clips, slugs, names = twitch.manual_get_clips(game_id, oauth, days_ago)
    else:
        clips, slugs, names = twitch.auto_get_clips(game_id, oauth, num_clips, days_ago)
    videos = utils.download_clips(clips)
    timestamps = utils.concatenate_clips(videos, names)
    yt.upload_video(game_id, timestamps, slugs, names)
    utils.delete_mp4s(videos)
    print("----- DONE -----")

def main():
    parser=argparse.ArgumentParser(description="Download, concatenate, and upload Twitch clips")
    parser.add_argument("-g",help="Game name",dest="game",type=str,required=True)
    parser.add_argument("-n",help="Number of clips to download",dest="num_clips",type=str,default=None)
    parser.add_argument("-d",help="Number of days ago that clips started",dest="days_ago",type=int,default=7)
    parser.set_defaults(func=run)
    args=parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
