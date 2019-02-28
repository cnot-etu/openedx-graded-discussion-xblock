import abc


class ApiInterface(object):
    """This class contains all the necessary methods to get the chat or discussion information"""
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_user_contributions(self, user, topic_id=None):
        """
        This returns all the contributions for a given user as a list
        """
        pass
