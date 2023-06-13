import json
import os
import sys
import requests
import shutil
import subprocess
from moviepy.editor import *

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
TMP_DIR = os.path.join(SCRIPT_DIR, "tmp")

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

def download_clips(clip_urls):
    print("Downloading clips...")
    
    # Make tmp directory for clips
    try:
        os.mkdir(TMP_DIR)
    except FileExistsError:
        # tmp directory already exists, so delete any existing clips
        for file in os.listdir(TMP_DIR):
            os.remove(os.path.join(TMP_DIR, file))

    for i, url in enumerate(clip_urls):
        try:
            # Download clip
            r = requests.get(url, stream=True)
            r.raise_for_status()
            filename = f"{i}.mp4"
            clip_path = os.path.join(TMP_DIR, filename)
            with open(clip_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
        except requests.exceptions.HTTPError as e:
            print(f"{url} returned HTTP Error")
            print(e.args[0])
        except requests.exceptions.Timeout:
            print(f"{url} timed out")
        except requests.exceptions.ConnectionError:
            print(f"Error connecting to {url}")
        except requests.exceptions.RequestException:
            print(f"{url} caused a catastrophic error")

    print("Clips downloaded.")

def concatenate_clips(videos, names):
    vfcs = []
    txts = []
    cvcs = []
    timestamps = [0]
    twitch = ImageClip("twitch.jpg")
    twitch = twitch.resize(0.15).set_position(("left", "top"))
    for i in range(len(videos)):
        vfc = VideoFileClip(videos[i], target_resolution=(1080, 1920))
        vfcs.append(vfc)

        txt = TextClip(txt=names[i], font='Helvetica-Bold', fontsize=50, color='black')
        txt = txt.on_color(size=(txt.w+8,twitch.h),color=(255,255,255)).set_position((twitch.w,"top")).set_duration(vfc.duration)
        txts.append(txt)

        twitch = twitch.set_duration(vfc.duration)
        cvc = CompositeVideoClip([vfc, twitch, txt])
        cvcs.append(cvc)
        # No need for last clip's duration
        if videos[i] is not videos[-1]:
            # Add most recent timestamp to current clip's duration for next timestamp
            timestamps.append(timestamps[-1] + vfc.duration)
    final_clip = concatenate_videoclips(cvcs)
    final_clip.write_videofile("final.mp4", temp_audiofile="temp-audio.m4a", remove_temp=True, audio_codec="aac")
    print("Final video created.")
    # Apparently these need to be closed like a file
    twitch.close()
    for vfc in vfcs:
        vfc.close()
    for txt in txts:
        txt.close()
    for cvc in cvcs:
        cvc.close()
    return timestamps

def open_video(filename):
    if sys.platform == "win32":
        os.startfile(filename)
    else:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.call([opener, filename])

def delete_mp4s():
    shutil.rmtree(TMP_DIR)
    if os.path.exists(file := os.path.join(SCRIPT_DIR, 'final.mp4')):
        os.remove(file)
    print("Clips and final video deleted.")
