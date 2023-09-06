import datetime
import json
import os
import shutil

import psutil
import requests
from moviepy.editor import (
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
)

import constants


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
        os.mkdir(constants.TMP_DIR)
    except FileExistsError:
        # tmp directory already exists, so delete any existing clips
        for file in os.listdir(constants.TMP_DIR):
            os.remove(os.path.join(constants.TMP_DIR, file))

    for i, url in enumerate(clip_urls):
        try:
            # Download clip
            response = requests.get(url, stream=True, timeout=5)
            response.raise_for_status()
            filename = f"{i}.mp4"
            clip_path = os.path.join(constants.TMP_DIR, filename)
            with open(clip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
        except requests.exceptions.HTTPError as err:
            print(f"{url} returned HTTP Error")
            print(err.args[0])
        except requests.exceptions.Timeout:
            print(f"{url} timed out")
        except requests.exceptions.ConnectionError:
            print(f"Error connecting to {url}")
        except requests.exceptions.RequestException:
            print(f"{url} caused a catastrophic error")

    print("Clips downloaded.")


def concatenate_clips(names):
    vfcs = []  # VideoFileClips
    txts = []  # TextClips
    cvcs = []  # CompositeVideoClips
    timestamps = [0]

    twitch_img = ImageClip("twitch.jpg").resize(0.15).set_position(("left", "top"))

    clips = sorted(
        [
            os.path.join(constants.TMP_DIR, file)
            for file in os.listdir(constants.TMP_DIR)
        ]
    )
    for i, clip in enumerate(clips):
        vfc = VideoFileClip(clip, target_resolution=(1080, 1920))
        vfcs.append(vfc)

        txt = TextClip(txt=names[i], font="Helvetica-Bold", fontsize=50, color="black")
        txt = (
            txt.on_color(size=(txt.w + 8, twitch_img.h), color=(255, 255, 255))
            .set_position((twitch_img.w, "top"))
            .set_duration(vfc.duration)
        )
        txts.append(txt)

        twitch_img = twitch_img.set_duration(vfc.duration)

        cvc = CompositeVideoClip([vfc, twitch_img, txt])
        cvcs.append(cvc)

        if clip is not clips[-1]:  # No need for last clip's duration
            # Add most recent timestamp to current clip's duration for next timestamp
            timestamps.append(timestamps[-1] + vfc.duration)

    final_clip = concatenate_videoclips(cvcs)
    final_clip.write_videofile(
        "final.mp4",
        temp_audiofile="temp-audio.m4a",
        remove_temp=True,
        audio_codec="aac",
        threads=psutil.cpu_count(),
    )
    print("Final video created.")

    # Close all MoviePy objects
    twitch_img.close()
    for vfc in vfcs:
        vfc.close()
    for txt in txts:
        txt.close()
    for cvc in cvcs:
        cvc.close()

    return timestamps


def delete_videos(include_final=False):
    shutil.rmtree(constants.TMP_DIR)
    if include_final and os.path.exists(
        file := os.path.join(constants.SCRIPT_DIR, "final.mp4")
    ):
        os.remove(file)
    print("Videos deleted.")


def get_past_datetime(days_ago):
    # In Twitch API, time is in ISO 8601 format
    return (datetime.date.today() - datetime.timedelta(days=days_ago)).strftime(
        "%Y-%m-%d"
    ) + "T00:00:00.00Z"
