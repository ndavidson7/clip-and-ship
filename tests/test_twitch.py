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
def test_request_oauth_raises_http_error():
    responses.add(
        responses.POST,
        constants.OAUTH_URL,
        body="",
        status=400,
        content_type="application/json",
    )

    with pytest.raises(requests.exceptions.HTTPError):
        twitch.request_oauth(example_twitch_secret)


def test_read_game_id_from_cache_not_none():
    game = "rust"  # included by default in game_ids.json

    assert twitch.__read_game_id_from_cache(game)


def test_read_game_id_from_cache_none():
    game = "not_a_game"

    assert not twitch.__read_game_id_from_cache(game)


def test_write_game_id_to_cache():
    game = "not_a_game"
    game_id = "123456"

    twitch.__write_game_id_to_cache(game, game_id)

    assert twitch.__read_game_id_from_cache(game) == game_id
