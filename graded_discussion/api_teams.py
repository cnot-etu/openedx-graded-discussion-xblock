import logging
import requests

from django.core.cache import cache
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

LOG = logging.getLogger(__name__)
CACHE_TIME = 3600


class ApiTeams(object):
    """This class makes request to get the team's data"""

    def __init__(self, server_url, client_id, client_secret, key="api_teams"):

        self.cache_key = key
        self.cache_block = cache.get(key, {})
        self.api_path = "{}/api/team/v0".format(server_url)

        headers = None

        if not headers:
            oauth = OAuth2Session(client=BackendApplicationClient(client_id=client_id))

            token = oauth.fetch_token(
                token_url="{}/oauth2/access_token/".format(server_url),
                client_id=client_id,
                client_secret=client_secret
            )

            headers = {"Authorization": "{} {}".format("Bearer", token['access_token'])}
            self.cache_block["headers"] = headers
            cache.set(self.cache_key, self.cache_block, CACHE_TIME)

        session = requests.Session()
        session.headers.update(headers)
        self.session = session

    def _call_api_get(self, url_path, key, payload=None):
        """This method return the response"""
        content = self.cache_block.get(key)

        if content:
            return content

        url = "/".join([self.api_path, url_path])
        response = self.session.get(url, params=payload)

        if response.status_code == 200:
            content = response.json()["results"]
            self.cache_block[key] = content
            cache.set(self.cache_key, self.cache_block, CACHE_TIME)
            return content

        LOG.error(
            "An error has ocurred trying to get team's data with status code = %s",
            content.status_code
        )

        return None

    def get_user_team(self, course_id, username):
        """Get the user's team"""
        key = "{}-{}".format(username, "teams")

        url_path = "teams"
        payload = {"course_id": course_id, "username": username}
        try:
            return self._call_api_get(url_path, key, payload)[0]
        except IndexError:
            return {}

    def get_course_teams(self, course_id):
        """Get the user's team"""
        key = "{}-{}".format(course_id, "teams")

        url_path = "teams"
        payload = {"course_id": course_id}
        return self._call_api_get(url_path, key, payload)
