""" Tests for the Calendar Sync .ics methods """

from datetime import datetime, timedelta

import pytz
from django.test import RequestFactory, TestCase
from freezegun import freeze_time
from mock import patch

from lms.djangoapps.courseware.courses import _Assignment
from openedx.core.djangoapps.content.course_overviews.tests.factories import CourseOverviewFactory
from openedx.core.djangoapps.site_configuration.tests.factories import SiteFactory
from openedx.features.calendar_sync import get_calendar_event_id
from openedx.features.calendar_sync.ics import generate_ics_for_user_course
from student.tests.factories import UserFactory


class TestIcsGeneration(TestCase):
    """ Test icalendar file generator """
    def setUp(self):
        super().setUp()

        freezer = freeze_time(datetime(2013, 10, 3, 8, 24, 55, tzinfo=pytz.utc))
        self.addCleanup(freezer.stop)
        freezer.start()

        self.course = CourseOverviewFactory()

        self.user = UserFactory()
        self.request = RequestFactory().request()
        self.request.site = SiteFactory()
        self.request.user = self.user

    def make_assigment(self, block_key=None, title=None, url=None, date=None, requires_file_access=False):
        """ Bundles given info into a namedtupled like get_course_assignments returns """
        return _Assignment(block_key, title, url, date, requires_file_access)

    def expected_ics(self, *assignments):
        """ Returns hardcoded expected ics strings for given assignments """
        template = '''BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Open edX//calendar_sync//EN
METHOD:REQUEST
BEGIN:VEVENT
SUMMARY:{summary}
DTSTART;VALUE=DATE-TIME:{timedue}
DURATION:P0D
DTSTAMP;VALUE=DATE-TIME:20131003T082455Z
UID:{uid}
DESCRIPTION:{summary} is due for {course}.
ORGANIZER;CN=édX:mailto:registration@example.com
TRANSP:TRANSPARENT
END:VEVENT
END:VCALENDAR
'''
        return (
            template.format(
                summary=assignment.title,
                course=self.course.display_name_with_default,
                timedue=assignment.date.strftime('%Y%m%dT%H%M%SZ'),
                uid=get_calendar_event_id(self.user, str(assignment.block_key), 'due', self.request.site.domain),
            )
            for assignment in assignments
        )

    def generate_ics(self, *assignments):
        """ Uses generate_ics_for_user_course to create ics files for the given assignments """
        with patch('openedx.features.calendar_sync.ics.get_course_assignments') as mock_get_assignments:
            mock_get_assignments.return_value = assignments
            return generate_ics_for_user_course(self.course, self.user, self.request)

    def assert_ics(self, *assignments):
        """ Asserts that the generated and expected ics for the given assignments are equal """
        generated = [ics.decode('utf8').replace('\r\n', '\n') for ics in self.generate_ics(*assignments)]
        self.assertEqual(len(generated), len(assignments))
        self.assertListEqual(generated, list(self.expected_ics(*assignments)))

    def test_generate_ics_for_user_course(self):
        """ Tests that a simple sample set of course assignments is generated correctly """
        now = datetime.now(pytz.utc)
        day1 = now + timedelta(1)
        day2 = now + timedelta(1)

        self.assert_ics(
            self.make_assigment(
                block_key='block1',
                title='Block1',
                url='https://example.com/block1',
                date=day1,
            ),
            self.make_assigment(
                block_key='block2',
                title='Block2',
                url='https://example.com/block2',
                date=day2,
            ),
        )
