"""TO-DO: Write a description of what this XBlock is."""

import pkg_resources

from api_discussion import ApiDiscussion

from django.conf import settings
from django.core.cache import cache
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from xblock.core import XBlock
from xblock.fields import Scope, String, Float, DateTime
from web_fragments.fragment import Fragment
from xblock.validation import ValidationMessage

from xblockutils.resources import ResourceLoader
from xblockutils.settings import XBlockWithSettingsMixin
from xblockutils.studio_editable import StudioEditableXBlockMixin

from webob.response import Response

LOADER = ResourceLoader(__name__)


@XBlock.wants("user")
@XBlock.wants("settings")
class GradedDiscussionXBlock(XBlock, StudioEditableXBlockMixin, XBlockWithSettingsMixin):
    """
    GradedDiscussionXBlock Class
    """
    display_name = String(
        display_name=_("Display Name"),
        help=_("Component Name."),
        scope=Scope.settings,
        default=_("Graded Discussion")
    )

    points = Float(
        display_name=_("Score"),
        help=_("Defines the number of points each problem is worth."),
        values={"min": 0, "step": .1},
        default=1,
        scope=Scope.settings
    )

    rubric = String(
        display_name=_("Rubric"),
        scope=Scope.settings,
        help=_("A list of criteria to grade the contribution."),
        default="",
        multiline_editor="html",
        resettable_editor=False
    )

    grading_message = String(
        display_name=_("Pre-Grading Message"),
        scope=Scope.settings,
        help=_("The message to show to learners before their score has been graded."),
        default="This discussion is staff graded. Your score will appear here when grading is complete.",
    )

    start_date = DateTime(
        display_name=_("Start Date"),
        default=None,
        scope=Scope.settings,
        help=_("Start date of this assignment.")
    )

    end_date = DateTime(
        display_name=_("End Date"),
        default=None,
        scope=Scope.settings,
        help=_("Due date of this assignment.")
    )

    discussion_topic = String(
        display_name=_("Discussion Topic"),
        default=None,
        scope=Scope.content,
        help=_("Select the topic that you want to use for grading."),
        values_provider=lambda self: self.get_discussion_topics(),
    )

    # Possible editable fields
    editable_fields = (
        "display_name",
        "points",
        "rubric",
        "grading_message",
        "start_date",
        "end_date",
        "discussion_topic",
    )

    @cached_property
    def api_discussion(self):
        """
        Returns an instance of ApiDiscussion
        """
        try:
            client_id = self.get_xblock_settings()["client_id"]
            client_secret = self.get_xblock_settings()["client_secret"]
        except KeyError:
            raise

        return ApiDiscussion(settings.LMS_ROOT_URL, unicode(self.course_id), client_id, client_secret, self.location)

    def get_discussion_topics(self):
        """
        """
        return self.api_discussion.get_topics_names()

    def is_course_staff(self):
        """
         Check if user is course staff.
        """
        return getattr(self.xmodule_runtime, "user_is_staff", False)

    @XBlock.handler
    def refresh_data(self, request, suffix=""):
        """
        """
        username = request.GET.get("user")
        cache.delete(self.location)
        contributions = self._get_contributions(username) if username else self._get_contributions(self.username)
        return Response(json=contributions)

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    # TO-DO: change this view to display your data your own way.
    def student_view(self, context=None):
        """
        The primary view of the GradedDiscussionXBlock, shown to students
        when viewing courses.
        """
        frag = Fragment(LOADER.render_django_template("static/html/graded_discussion.html", self._get_context()))
        frag.add_css(self.resource_string("static/css/graded_discussion.css"))
        frag.add_javascript(self.resource_string("static/js/src/graded_discussion.js"))
        frag.initialize_js('GradedDiscussionXBlock')
        return frag

    @cached_property
    def username(self):
        """
        Returns the username for the currently user
        """
        user = self.runtime.service(self, 'user').get_current_user()
        return user.opt_attrs['edx-platform.username']

    def validate_field_data(self, validation, data):
        """
        This method validates the data from studio before it is saved
        """
        start_date = data.start_date
        end_date = data.end_date

        if start_date and end_date and end_date <= start_date:
            validation.add(ValidationMessage(ValidationMessage.ERROR, u"The start date must be before the end date"))

    def _get_context(self):
        """
        """
        if self.is_course_staff():
            return dict(
                user_is_staff=True,
                rubric=self.rubric,
                users=[],
                reload_url=self.runtime.local_resource_url(self, 'public/img/reload-icon.png'),
            )

        return dict(
            user_is_staff=False,
            contributions=self._get_contributions(self.username),
            grading_message=self.grading_message,
            reload_url=self.runtime.local_resource_url(self, 'public/img/reload-icon.png'),
        )

    def _get_contributions(self, username):
        """
        This returns the contributions for a given username
        """
        cache_block = cache.get(self.location, {})
        contributions = cache_block.get(username)

        if contributions:
            return contributions

        if self.discussion_topic:
            contributions = self.api_discussion.get_user_contributions(username, self.discussion_topic)
        else:
            contributions = self.api_discussion.get_user_contributions(username)

        cache_block[username] = contributions
        cache.set(self.location, cache_block, 3600)
        return contributions

    # TO-DO: change this to create the scenarios you'd like to see in the
    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("GradedDiscussionXBlock",
             """<graded_discussion/>
             """),
            ("Multiple GradedDiscussionXBlock",
             """<vertical_demo>
                <graded_discussion/>
                <graded_discussion/>
                <graded_discussion/>
                </vertical_demo>
             """),
        ]
