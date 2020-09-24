#!/usr/bin/env python3

import argparse

def run(args=None):
    game = args.game
    days_ago = args.days_ago
    num_clips = args.num_clips
    oauth = get_twitch_oauth()
    game_id = get_game_id(game, oauth)
    clips = []
    slugs = []
    if(num_clips is None):
        clips, slugs = manual_get_clips(game_id, oauth, days_ago)
    else:
        clips, slugs = auto_get_clips(game_id, oauth, num_clips, days_ago)
    videos = download_clips(clips)
    timestamps = concatenate_clips(videos)
    upload_video(game_id, timestamps, slugs)
    delete_mp4s(videos)

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