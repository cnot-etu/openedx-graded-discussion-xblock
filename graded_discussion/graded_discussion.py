"""TO-DO: Write a description of what this XBlock is."""

import json
import pkg_resources

from dateutil.parser import parse

from api_discussion import ApiDiscussion
from api_teams import ApiTeams

from courseware.courses import get_course_by_id
from courseware.models import StudentModule
from student.models import (
    CourseEnrollmentManager,
    user_by_anonymous_id,
    get_user_by_username_or_email,
    anonymous_id_for_user
)
from submissions import api as submissions_api
from submissions.models import StudentItem

from openedx.core.djangoapps.course_groups.cohorts import get_cohort_names, get_cohort_id
from openedx.core.djangoapps.user_api.accounts.image_helpers import get_profile_image_urls_for_user

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
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
    has_score = True

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
        default=100,
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
        default="All topics",
        scope=Scope.settings,
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
            client_id = settings.XBLOCK_SETTINGS["client_id"]
            client_secret = settings.XBLOCK_SETTINGS["client_secret"]
        except KeyError:
            raise

        return ApiDiscussion(settings.LMS_ROOT_URL, unicode(self.course_id), client_id, client_secret, self.location)

    @cached_property
    def api_teams(self):
        """
        Returns an instance of ApiTeams
        """
        try:
            client_id = settings.XBLOCK_SETTINGS["client_id"]
            client_secret = settings.XBLOCK_SETTINGS["client_secret"]
        except KeyError:
            raise

        return ApiTeams(settings.LMS_ROOT_URL, client_id, client_secret, self.location)

    @XBlock.handler
    def enter_grade(self, request, suffix=''):
        """
        """
        require(self.is_course_staff())
        user = get_user_by_username_or_email(request.params.get('user'))

        score = request.params.get('score')
        comment = request.params.get('comment')

        if not score:
            return Response(
                json_body={"error": "Enter a valid grade"},
                status_code=400,
            )

        try:
            score = int(score)
        except ValueError:
            return Response(
                json_body={"error": "Enter a valid grade"},
                status_code=400,
            )

        submission_id = self.get_submission_id(user)

        submission = submissions_api.create_submission(submission_id, {'comment': comment})

        submissions_api.set_score(submission['uuid'], score, self.max_score())

        self.get_or_create_student_module(user, score, comment)

        return Response(json_body={"success": "success"})

    @cached_property
    def contributions(self):

        return self.api_discussion.get_contributions(self.topic_id)

    def get_comment(self):
        """
        """
        submissions = submissions_api.get_submissions(self.submission_id)
        if submissions:
            return submissions[0]['answer']['comment']

    def get_discussion_topics(self):
        """
        """
        topics = self.api_discussion.get_topics_names()
        topics.append("All topics")
        return topics

    def get_or_create_student_module(self, user, score, comment):
        """
        """
        state = {"score": score, "comment": comment}
        student_module, created = StudentModule.objects.get_or_create(
            course_id=self.course_id,
            module_state_key=self.location,
            student=user,
            defaults={
                'state': json.dumps(state),
            }
        )
        return student_module

    def get_score(self, user):
        """
        Return student's current score.
        """
        score = submissions_api.get_score(self.get_submission_id(user))
        if score:
            return score['points_earned']

    def get_student_list(self):
        """
        """
        users = CourseEnrollmentManager().users_enrolled_in(self.course_id)
        graded_students = self._get_graded_students()

        return [
            dict(
                username=user.username,
                fullname=user.first_name + ' ' +user.last_name,
                image_url=self._get_image_url(user),
                last_post=self._get_last_date_on_post(self._get_contributions(user.username)),
                cohort_id=get_cohort_id(user, self.course_id),
                team=self.api_teams.get_user_team(unicode(self.course_id), user.username),
                contributions=json.dumps(self._get_contributions(user.username)),
            )
            for user in users if not user.is_staff and user not in graded_students
        ]

    def get_submission_id(self, user):
        """
        """
        return dict(
            item_id=unicode(self.location),
            item_type='graded_discussion',
            course_id=unicode(self.course_id),
            student_id=anonymous_id_for_user(user, self.course_id)
        )

    def is_course_staff(self):
        """
         Check if user is course staff.
        """
        return getattr(self.xmodule_runtime, "user_is_staff", False)

    def max_score(self):
        """
        Return the maximum score possible.
        """
        return self.points

    @XBlock.json_handler
    def get_contributions(self, data, suffix=""):
        """
        """
        require(self.is_course_staff())
        users = data.get("users")
        self._delete_cache(users)
        contributions = {user: json.dumps(self._get_contributions(user)) for user in users}
        return Response(json=contributions)

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    @cached_property
    def score(self):
        """
        """
        user = get_user_by_username_or_email(self.username)
        return self.get_score(user)

    @cached_property
    def submission_id(self):
        """
        """
        user = get_user_by_username_or_email(self.username)
        return self.get_submission_id(user)

    # TO-DO: change this view to display your data your own way.
    def student_view(self, context=None):
        """
        The primary view of the GradedDiscussionXBlock, shown to students
        when viewing courses.
        """
        frag = Fragment(LOADER.render_django_template("static/html/graded_discussion.html", self._get_context()))
        frag.add_css_url("https://cdnjs.cloudflare.com/ajax/libs/jquery-modal/0.9.1/jquery.modal.min.css")
        frag.add_css(self.resource_string("static/css/graded_discussion.css"))
        frag.add_javascript_url("https://cdnjs.cloudflare.com/ajax/libs/jquery-modal/0.9.1/jquery.modal.min.js")
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

    @cached_property
    def topic_id(self):
        """
        """
        if self.discussion_topic == "All topics":
            return None
        return self.api_discussion.get_topic_id(self.discussion_topic)

    def validate_field_data(self, validation, data):
        """
        This method validates the data from studio before it is saved
        """
        start_date = data.start_date
        end_date = data.end_date

        if start_date and end_date and end_date <= start_date:
            validation.add(ValidationMessage(ValidationMessage.ERROR, u"The start date must be before the end date"))

    def _delete_cache(self, users):
        cache.delete(self.location)
        for user in users:
            key = "{}-{}".format(self.location, user)
            cache.delete(key)

        key = "{}-{}".format(self.location, "contributions")
        cache.delete(key)

    def _filter_by_date(self, contributions):
        """
        """
        if self.start_date and self.end_date:
            return [
                contribution
                for contribution in contributions
                if parse(contribution["created_at"]) >= self.start_date and parse(contribution["created_at"]) <= self.end_date
            ]
        elif self.start_date:
            return [
                contribution
                for contribution in contributions
                if parse(contribution["created_at"]) >= self.start_date
            ]
        elif self.end_date:
            return [
                contribution
                for contribution in contributions
                if parse(contribution["created_at"]) <= self.end_date
            ]
        return contributions

    def _get_context(self):
        """
        """
        if self.is_course_staff():
            return dict(
                user_is_staff=True,
                rubric=self.rubric,
                users=self.get_student_list(),
                reload_url=self.runtime.local_resource_url(self, 'public/img/reload-icon.png'),
                cohorts=get_cohort_names(get_course_by_id(self.course_id)),
                teams=self.api_teams.get_course_teams(unicode(self.course_id)),
                grading_message=self.grading_message,
            )

        comment = self.get_comment()
        return dict(
            user_is_staff=False,
            grading_message=comment if comment and self.score else self.grading_message,
            score=self.score,
            max_score=self.points
        )

    def _get_contributions(self, username):
        """
        This returns the contributions for a given username
        """
        key = "{}-{}".format(self.location, username)
        contributions = cache.get(key)
        if contributions:
            return contributions

        contributions = [contribution for contribution in self.contributions if contribution["author"] == username]

        contributions = self._filter_by_date(contributions)

        cache.set(key, contributions)

        return contributions

    def _get_graded_students(self):
        """
        """
        students = StudentItem.objects.filter(
            course_id=self.course_id,
            item_id=unicode(self.location)
        )
        result = []
        for student in students:
            user = user_by_anonymous_id(student.student_id)
            if self.get_score(user):
                result.append(user)
        return result

    def _get_image_url(self, user):
        """
        """
        profile_image_url = get_profile_image_urls_for_user(user)["full"]

        if profile_image_url.startswith("http"):
            return profile_image_url

        base_url = settings.LMS_ROOT_URL
        image_url = "{}{}".format(base_url, profile_image_url)
        return image_url

    def _get_last_date_on_post(self, contributions):
        """
        """
        contributions.sort(key=lambda item: item["created_at"])
        try:
            return contributions[0].get("created_at")
        except IndexError:
            return ""

    def _get_topic_id(self, name):
        """
        """
        return self.api_discussion.get_topic_id(name)

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


def require(assertion):
    """
    Raises PermissionDenied if assertion is not true.
    """
    if not assertion:
        raise PermissionDenied
