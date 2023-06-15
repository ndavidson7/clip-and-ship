import utils
import constants
import requests
import json
import datetime
import webbrowser

class TwitchHandler:

    def __init__(self, game: str, num_clips: int, days_ago: int) -> None:
        self.game = game
        self.num_clips = num_clips
        self.days_ago = days_ago
        self.oauth = self.request_oauth()
        self.twitch_secret = utils.read_json(constants.TWITCH_SECRET_PATH)
        self.endpoint_headers = { # Headers for all Twitch API requests
            "Authorization": f"Bearer {self.oauth}",
            "Client-Id": self.twitch_secret["client_id"],
        }
    
    def run(self) -> None:
        self.game_id = self.get_game_id(self.game)
        self.clips, self.slugs, self.names = self.get_clips_data()

    def request_oauth(self) -> str:
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        response = requests.post('https://id.twitch.tv/oauth2/token', headers=headers, data=self.twitch_secret).text

        if (oauth := json.loads(response)["access_token"]) is not None:
            print("Twitch OAuth received.")
            return oauth
        else:
            raise Exception(f"Twitch OAuth could not be received.\n{response}")

    def get_game_id(self) -> str:
        # Check if game ID is already stored
        game_ids = utils.read_json(constants.GAME_IDS_PATH)
        if self.game.lower() in game_ids:
            print("Game ID retrieved.")
            return game_ids[self.game.lower()]

        # If not, request game ID from Twitch
        url = 'https://api.twitch.tv/helix/games'
        params = {
            "name": self.game.title(),
        }

        # Loop until response data is not empty
        while not (data := json.loads(requests.get(url, params=params, headers=self.endpoint_headers).text)["data"]):
            # If data is empty, the name was wrong. Try again with another name.
            # Note that self.game is not changed, so the informal name is saved in the game_ids file for easier future use.
            game = input(f'Could not find "{self.game}." What is the game\'s full name on Twitch? ')
            params["name"] = game.title()

        id = data[0]["id"]
        game_ids[self.game.lower()] = id
        utils.write_json(game_ids, constants.GAME_IDS_PATH)
        print("Game ID retrieved.")
        return id

    def get_clips_data(self, cursor: str = None, video_length: int = 0) -> tuple[list[str], list[str], list[str]]:
        # Whether to manually choose clips one-by-one or simply get the top num_clips clips
        manual_mode = self.num_clips <= 0

        # Get date and time from days_ago days ago (in Twitch's format)
        started_at = utils.get_past_datetime(self.days_ago)

        # Request clips from Twitch
        print("Requesting clips...")
        url = 'https://api.twitch.tv/helix/clips'
        params = {
            "game_id": self.game_id,
            "first": 20 if manual_mode else self.num_clips,
            "started_at": started_at,
            "after": cursor,
        }
        response = json.loads(requests.get(url, params=params, headers=self.endpoint_headers).text)

        clips = [] # download URLs
        slugs = [] # public Twitch clip URLs
        names = [] # streamer names
        for data in response["data"]:
            if manual_mode:
                # Open clip in browser
                webbrowser.open(data["url"])

                print(f"Current length of video: {datetime.timedelta(seconds=video_length)}\n \
                        With current clip:       {datetime.timedelta(seconds=video_length+data['duration'])}")
                
                choice = input("Include this clip in the video? (y, yf, n, nf): ").lower()
                while choice != 'y' and choice != 'n' and choice != 'yf' and choice != 'nf':
                    print("Invalid choice.")
                    choice = input("Include this clip in the video? (y, yf, n, nf): ").lower()
                if 'y' in choice:
                    # update video length
                    video_length += data['duration']

                    # Append data to lists
                    self.save_clip_data(data, clips, slugs, names)
                if 'f' in choice:
                    print("Clips chosen.")
                    return clips, slugs, names
            else:
                # Append data to lists
                self.save_clip_data(data, clips, slugs, names)

        if manual_mode or len(clips) < self.num_clips:
            # If we're in manual mode and haven't finished ('f' in choice) OR we're in automatic mode and the response did not include all clips, make another request
            # I don't like that this is recursive... maybe I'll revisit it later
            cursor = response['pagination']['cursor']
            self.num_clips -= len(clips)
            new_clips, new_slugs, new_names = self.get_clips_data(cursor, video_length)
            clips.extend(new_clips)
            slugs.extend(new_slugs)
            names.extend(new_names)

            return clips, slugs, names

        print("Clips received.")
        return clips, slugs, names

    def save_clip_data(self, data, clips, slugs, names):
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

        # Don't need to return anything because lists are mutable and because Python is pass by assignment?
        return