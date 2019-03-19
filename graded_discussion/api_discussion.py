import logging
import requests

from api_interface import ApiInterface

from django.core.cache import cache
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

LOG = logging.getLogger(__name__)
CACHE_TIME = 3600


class ApiDiscussion(ApiInterface):
    """This class makes request to get the discussion's information"""

    def __init__(self, server_url, course, client_id, client_secret, key="api_discussion"):

        self.cache_key = key
        self.course = course
        cache_block = cache.get(key, {})
        self.server_url = server_url
        self.api_path = "{}/api/discussion/v1/course_topics/{}".format(server_url, course)

        headers = cache_block.get("headers")

        if not headers:
            oauth = OAuth2Session(client=BackendApplicationClient(client_id=client_id))

            token = oauth.fetch_token(
                token_url="{}/oauth2/access_token/".format(server_url),
                client_id=client_id,
                client_secret=client_secret
            )

            headers = {"Authorization": "{} {}".format("Bearer", token['access_token'])}
            cache_block["headers"] = headers
            cache.set(self.cache_key, cache_block, CACHE_TIME)

        session = requests.Session()
        session.headers.update(headers)
        self.session = session

    def get_contributions(self, topic_id=None):
        """
        This returns all the contributions for a given user as a list
        """
        key = "{}-{}".format(self.cache_key, "contributions")
        contributions = cache.get(key)

        if contributions:
            return contributions

        comments = []
        contributions = []
        thread_dict = {}

        for thread in self._get_threads(topic_id):
            thread_dict.update({thread["id"]: {"name": thread["title"], "author": thread["author"]}})

            contributions.append({
                "author": thread["author"],
                "contribution": thread["raw_body"],
                "created_at": thread["created_at"],
                "parent": {"name": thread["title"], "author": thread["author"]},
                "kind": "thread",
            })

            comments += self._get_comments(thread)

        for comment in comments:
            if comment.get("child_count") > 0:
                url = "{}/api/discussion/v1/comments/{}".format(self.server_url, comment["id"])
                comments += self._fetch_content(url)

        contributions += [{
            "author": comment["author"],
            "contribution": comment["raw_body"],
            "created_at": comment["created_at"],
            "parent": thread_dict[comment["thread_id"]],
            "kind": "comment",
        } for comment in comments]

        cache.set(key, contributions, CACHE_TIME)

        return contributions

    def get_topics_names(self):
        """
        """
        topics = self._fetch_topics()
        return self._get_names(topics)

    def get_topic_id(self, name):
        """
        """
        topics = self._fetch_topics()
        return self._get_id(topics, name)

    def _fetch_content(self, content_url=None, payload=None):
        """
        """
        if not content_url:
            return []

        response = self._handle_response(self.session.get(content_url, params=payload))

        if response:
            content = response.get("results", [])
            content += self._fetch_content(response.get("pagination", {}).get("next"))
        else:
            content = []

        return content

    def _fetch_topics(self, topic_id=None):
        """
        """

        payload = {"topic_id": topic_id} if topic_id else None

        response = self._handle_response(self.session.get(self.api_path, params=payload))

        if response:
            topics = response.get("courseware_topics")
            topics += response.get("non_courseware_topics")
            return topics

        return []

    def _get_comments(self, thread):
        """
        """
        comments = []
        payload = {"page_size": 100}

        if thread["comment_count"] > 0 and thread["type"] == "discussion":
            comments += self._fetch_content(thread["comment_list_url"], payload)

        elif thread["comment_count"] > 0 and thread["type"] == "question":
            if thread["has_endorsed"]:
                comments += self._fetch_content(thread["endorsed_comment_list_url"], payload)
            comments += self._fetch_content(thread["non_endorsed_comment_list_url"], payload)

        return comments

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

    def _get_id(self, topics, name):
        """
        """
        for topic in topics:
            children = topic.get("children", [])
            if len(children) == 0 and topic.get("name") == name:
                return topic.get("id")
            elif len(children) > 0:
                topic_id = self._get_id(children, name)

                if topic_id:
                    return topic_id

        return None

    def _get_threads(self, topic_id):
        """
        """
        url = "{}/api/discussion/v1/threads/".format(self.server_url)

        payload = {"course_id": self.course, "topic_id": topic_id, "page_size": 100}

        return self._fetch_content(content_url=url, payload=payload)

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
