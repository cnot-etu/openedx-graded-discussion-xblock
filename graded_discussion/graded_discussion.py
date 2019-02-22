"""TO-DO: Write a description of what this XBlock is."""

import pkg_resources

from django.utils.translation import ugettext_lazy as _

from xblock.core import XBlock
from xblock.fields import Scope, String, Float, DateTime
from xblock.fragment import Fragment
from xblock.validation import ValidationMessage

from xblockutils.resources import ResourceLoader
from xblockutils.studio_editable import StudioEditableXBlockMixin


LOADER = ResourceLoader(__name__)


class GradedDiscussionXBlock(XBlock, StudioEditableXBlockMixin):
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

    discussion_topics = String(
        display_name=_("Discussion Topic"),
        scope=Scope.content,
        help=_("Select the topic that you want to use for grading."),
        values_provider=lambda self: ["topic_1", "topic_2", "topic_3"],
    )

    # Possible editable fields
    editable_fields = (
        "display_name",
        "points",
        "rubric",
        "grading_message",
        "start_date",
        "end_date",
        "discussion_topics",
    )

    def is_course_staff(self):
        """
         Check if user is course staff.
        """
        return getattr(self.xmodule_runtime, 'user_is_staff', False)

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
        context = {"staff": self.is_course_staff()}
        frag = Fragment(LOADER.render_template("static/html/graded_discussion.html", context))
        frag.add_css(self.resource_string("static/css/graded_discussion.css"))
        frag.add_javascript(self.resource_string("static/js/src/graded_discussion.js"))
        frag.initialize_js('GradedDiscussionXBlock')
        return frag

    def validate_field_data(self, validation, data):
        """
        This method validates the data from studio before it is saved
        """
        start_date = data.start_date
        end_date = data.end_date

        if start_date and end_date and end_date <= start_date:
            validation.add(ValidationMessage(ValidationMessage.ERROR, u"The start date must be before the end date"))

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
