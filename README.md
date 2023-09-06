# Clip and Ship

Clip and Ship is a Python script that automates the downloading, editing, concatenating, and uploading of Twitch clips using FFmpeg and MoviePy.

## Installation

1. Clone the repository.
1. Make sure you have Python 3 and pip installed by running the following in your terminal: \
   `python -V` or `py -V` \
   `pip --version`
1. Open clip-and-ship in your terminal and follow [this guide](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/#installing-packages-using-pip-and-virtual-environments) to create a virtual environment.
1. After activating the virtual environment, run `pip install -r requirements.txt`.
1. Install ImageMagick following the [official instructions](https://imagemagick.org/script/download.php). If you are on Windows, use the top-most recommended installer.
1. Verify ImageMagick is registered in your PATH by running `magick -version`. You may have to restart your terminal first.

## Configuration

### Twitch

To communicate with the Twitch API, you'll need an access token.

1. Follow [this guide](https://dev.twitch.tv/docs/authentication/register-app/) to register a Twitch Developer app. \
   Note: OAuth Redirect URLs should be "http://localhost".
1. Copy the client ID and a new client secret to `twitch_client_secret.json.example` and remove `.example` from the file name.

### YouTube (WIP)

Skip this step if you don't intend to automate uploading to YouTube.

## Running

`./main.py -h` to show argument options. If you encounter permission errors, run `chmod +x main.py`.

Simplest usage is `./main.py [game name]`, for example, `./main.py Minecraft`. Use double quotes for games with spaces or special characters: `./main.py "World of Warcraft"`.
