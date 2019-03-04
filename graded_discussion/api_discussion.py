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
        self.cache_block = cache.get(key, {})
        self.api_path = "{}/api/discussion/v1/course_topics/{}".format(server_url, course)

        headers = self.cache_block.get("headers")

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

    def get_user_contributions(self, user, topic_id=None):
        """
        This returns all the contributions for a given user as a list
        """
        topics = self._fetch_topics()
        threads = []
        comments = []
        contributions = []
        thread_dict = {}

        if topic_id:
            topic = self._find_topic_by_id(topics, topic_id)
            threads = self._fetch_content(topic.get("thread_list_url"))
        else:
            for topic in topics:
                threads += self._fetch_content(topic.get("thread_list_url"))

        for thread in threads:
            thread_dict.update({thread["id"]: {"name": thread["title"], "author": thread["author"]}})

            if thread["author"] == user:
                contributions.append({
                    "author": user,
                    "contribution": thread["raw_body"],
                    "created_at": thread["created_at"],
                    "kind": "thread",
                })

            comments += self._fetch_content(thread["comment_list_url"])

        contributions += [{
            "author": user,
            "contribution": comment["raw_body"],
            "created_at": comment["created_at"],
            "parent": thread_dict[comment["thread_id"]],
            "kind": "comment",
        } for comment in comments if comment["author"] == user]

        return contributions

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

        content = self.cache_block.get(content_url)

        if not content:

            response = self._handle_response(self.session.get(content_url))

            if response:
                content = response.get("results", [])
                content += self._fetch_content(response.get("pagination", {}).get("next"))
                self.cache_block[content_url] = content
                cache.set(self.cache_key, self.cache_block, CACHE_TIME)
            else:
                content = []

        return content

    def _fetch_topics(self):
        """
        """
        topics = self.cache_block.get("topics")

        if topics:
            return topics

        response = self._handle_response(self.session.get(self.api_path))

        if response:
            topics = response.get("courseware_topics")
            topics += response.get("non_courseware_topics")
            self.cache_block["topics"] = topics
            cache.set(self.cache_key, self.cache_block, CACHE_TIME)
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
