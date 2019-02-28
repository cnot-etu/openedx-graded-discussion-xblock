import logging
import requests

from api_interface import ApiInterface

from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

LOG = logging.getLogger(__name__)


class ApiDiscussion(ApiInterface):
    """This class makes request to get the discussion's information"""
    def __init__(self, server_url, course, client_id, client_secret):
        self.api_path = "{}/api/discussion/v1/course_topics/{}".format(server_url, course)

        oauth = OAuth2Session(client=BackendApplicationClient(client_id=client_id))

        token = oauth.fetch_token(
            token_url="{}/oauth2/access_token/".format(server_url),
            client_id=client_id,
            client_secret=client_secret
        )

        headers = {"Authorization": "{} {}".format("Bearer", token['access_token'])}
        session = requests.Session()
        session.headers.update(headers)
        self.session = session

    def get_user_contributions(self, user, topic_id=None):
        """
        This returns all the contributions for a given user as a list
        """
        topics = self._fetch_topics()
        threads = []
        comments = []

        if topic_id:
            topic = self._find_topic_by_id(topics, topic_id)
            threads = self._fetch_content(topic.get("thread_list_url"))
        else:
            for topic in topics:
                threads += self._fetch_content(topic.get("thread_list_url"))

        for thread in threads:
            comments += self._fetch_content(thread["comment_list_url"])

        return [comment for comment in comments if comment["author"] == user]

    def get_topics_names(self):
        """
        """
        topics = self._fetch_topics()
        return self._get_names(topics)

    def _fetch_content(self, content_url=None):
        """
        """
        if not content_url:
            return []

        response = self._handle_response(self.session.get(content_url))

        if response:
            content = response.get("results", [])
            content += self._fetch_content(response.get("pagination", {}).get("next"))
            return content

        return []

    def _fetch_topics(self):
        """
        """
        response = self._handle_response(self.session.get(self.api_path))

        if response:
            topics = response.get("courseware_topics")
            topics += response.get("non_courseware_topics")
            return topics

        return None

    def _get_names(self, topics):
        """
        """
        result = []
        for topic in topics:
            children = topic.get("children", [])
            if len(children) == 0:
                result.append(topic.get("name"))
            else:
                result += self._get_names(children)

        return result

    def _handle_response(self, response):
        """
        """
        if response.status_code == 200:
            return response.json()
        LOG.info("The request gets a response with status code = %s", response.status_code)
        return None

    def _find_topic_by_id(self, topics, topic_id):
        """
        This return the topic for a given id
        """
        for topic in topics:
            topic_child = self._find_topic_by_id(topic.get("children", []), topic_id)
            if topic_child:
                return topic_child
            elif topic_id == topic.get("id"):
                return topic
