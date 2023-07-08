import json

import pytest
import requests.exceptions
import responses

import constants
import twitch

example_twitch_secret = {
    "client_id": "x" * 30,
    "client_secret": "x" * 30,
    "grant_type": "client_credentials",
}

example_request_oauth_response = {
    "access_token": "x" * 30,
    "expires_in": 1234567,
    "token_type": "bearer",
}


@responses.activate
def test_request_oauth_returns_token():
    responses.add(
        responses.POST,
        constants.OAUTH_URL,
        body=json.dumps(example_request_oauth_response),
        status=200,
        content_type="application/json",
    )

    assert twitch.request_oauth(example_twitch_secret)


@responses.activate
def test_request_oauth_raises_error():
    responses.add(
        responses.POST,
        constants.OAUTH_URL,
        body="",
        status=400,
        content_type="application/json",
    )

    with pytest.raises(ValueError):
        twitch.request_oauth(example_twitch_secret)


def test_get_game_id_from_cache():
    game = "game"
    game_id = "12345"
    game_ids = {game.lower(): game_id}

    with open(constants.GAME_IDS_PATH, "w") as f:
        json.dump(game_ids, f)

    assert twitch.get_game_id(game, {}) == game_id
