from unittest import TestCase
from main import find_refs_in_comment


class Test(TestCase):
    def test_find_refs_in_comment(self):
        self.assertEqual(
            find_refs_in_comment("<a href=\"https:&#x2F;&#x2F;developers.facebook.com&#x2F;docs&#x2F;marketing-api&#x2F;app"
            "-event-api&#x2F;\" rel=\"nofollow\">https:&#x2F;&#x2F;developers.facebook.com&#x2F;docs&#x2F;marketing"
            "-api&#x2F;app-event...</a>"),
            {'https://developers.facebook.com/docs/marketing-api/app-event-api/'},
            'link in text'
        )

        self.assertEqual(
            find_refs_in_comment("At the risk of pointing to the documentation,<p>graph-facebook-com&#x2F;app&#x2F;activities is an "
            "endpoint used by 3rd party developers working with Facebook SDKs to send app analytic data for "
            "insights.<p><a href=\"https:&#x2F;&#x2F;developers.facebook.com&#x2F;docs&#x2F;marketing-api&#x2F;app"
            "-event-api&#x2F;\" rel=\"nofollow\">https:&#x2F;&#x2F;developers.facebook.com&#x2F;docs&#x2F;marketing"
            "-api&#x2F;app-event...</a>\n<a href=\"http:&#x2F;&#x2F;www.facebook.com&#x2F;analytics\" "
            "rel=\"nofollow\">http:&#x2F;&#x2F;www.facebook.com&#x2F;analytics</a>\n<a "
            "href=\"https:&#x2F;&#x2F;business.facebook.com&#x2F;events_manager&#x2F;app&#x2F;events\" "
            "rel=\"nofollow\">https:&#x2F;&#x2F;business.facebook.com&#x2F;events_manager&#x2F;app&#x2F;events</a><p"
            ">This is what a URL can look like.<p>graph-facebook-com&#x2F;1106907002683888&#x2F;activities?method"
            "=POST&amp;event=MOBILE_APP_INSTALL&amp;anon_id=1&amp;advertiser_tracking_enabled=1&amp"
            ";application_tracking_enabled=1&amp;custom_events=[{%22_eventName%22:%22fb_mobile_purchase%22,"
            "}]<p>If you click the above you&#x27;ll litter my analytics feed for my app 1106907002683888 with junk "
            "data.<p>Just in case, someone was looking for the specific call talked about because I couldn&#x27;t "
            "find it linked in Vice&#x27;s article. "),
            {'http://www.facebook.com/analytics', 'https://developers.facebook.com/docs/marketing-api/app-event-api/',
             'https://business.facebook.com/events_manager/app/events'},
            '3 links in text'
        )

