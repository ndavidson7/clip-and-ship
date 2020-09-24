import json
import os
import sys
import requests
import subprocess
from moviepy.editor import VideoFileClip, concatenate_videoclips

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

def download_clips(clips):
    print("Downloading clips...")
    videos = []
    for i in range(len(clips)):
        r = requests.get(clips[i], stream=True)
        name = str(i) + ".mp4"
        with open(name, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        videos.append(name)

    print("Clips downloaded.")
    return videos

def concatenate_clips(videos):
    vfcs = []
    timestamps = [0]
    for video in videos:
        vfc = VideoFileClip(video, target_resolution=(1080, 1920))
        vfcs.append(vfc)
        # No need for last clip's duration
        if video is not videos[-1]:
            # Add most recent timestamp to current clip's duration for next timestamp
            timestamps.append(timestamps[-1] + vfc.duration)
    final_clip = concatenate_videoclips(vfcs)
    final_clip.write_videofile("final.mp4", temp_audiofile="temp-audio.m4a", remove_temp=True, audio_codec="aac")
    print("Final video created.")
    # Apparently these need to be closed like a file
    for vfc in vfcs:
        vfc.close()
    return timestamps

def open_video(filename):
    if sys.platform == "win32":
        os.startfile(filename)
    else:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.call([opener, filename])

def delete_mp4s(videos):
    for video in videos:
        os.remove(video)
    if os.path.exists('final.mp4'):
        os.remove('final.mp4')
    print("Videos deleted.")