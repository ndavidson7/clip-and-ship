# Clip and Ship

Clip and Ship is a Python script that automates the downloading, editing, concatenating, and uploading of Twitch clips using FFmpeg and MoviePy.

## Installation

1. Clone the repository.
1. Make sure you have Python3 and pip3 installed by running the following in your terminal:
   `python -V` or `py -V` depending on OS and configuration, hereby referred to as "python"
   `pip --version`
1. Open clip-and-ship in your terminal and follow [this guide](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/#installing-packages-using-pip-and-virtual-environments) to create a virtual environment. This step is technically optional but highly recommended. If you don't know what a virtual environment is, don't worry. The guide is simple and explains the purpose of virtual environments.
1. After activating the virtual environment, run `pip install -r requirements.txt`.
1. Install ImageMagick following the [official instructions](https://imagemagick.org/script/download.php). If you are on Windows, use the top-most recommended installer.
1. Verify ImageMagick is registered in your PATH by running `magick -version`. You may have to restart your terminal first.
