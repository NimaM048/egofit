from __future__ import annotations

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from home.utils import normalize_search_query
from home.validators import normalize_phone_number, validate_phone_number
from home.video_streaming import parse_http_range


class HomeUtilityTests(SimpleTestCase):
    def test_normalize_search_query_normalizes_arabic_characters_and_whitespace(self):
        self.assertEqual(
            normalize_search_query("  \u0643\u064a\u0643  \u0639\u0631\u0628\u064a  "),
            "\u06a9\u06cc\u06a9 \u0639\u0631\u0628\u06cc",
        )

    def test_normalize_phone_number_strips_common_separators(self):
        self.assertEqual(normalize_phone_number("+98 (912) 123-4567"), "989121234567")

    def test_validate_phone_number_rejects_invalid_number(self):
        with self.assertRaises(ValidationError) as context:
            validate_phone_number("12-34")
        self.assertIn("\u0634\u0645\u0627\u0631\u0647 \u062a\u0645\u0627\u0633 \u0645\u0639\u062a\u0628\u0631 \u0646\u06cc\u0633\u062a.", context.exception.messages)


class VideoStreamingTests(SimpleTestCase):
    def test_parse_http_range_supports_standard_byte_range(self):
        self.assertEqual(parse_http_range("bytes=10-19", 100), (10, 19))

    def test_parse_http_range_supports_suffix_byte_range(self):
        self.assertEqual(parse_http_range("bytes=-20", 100), (80, 99))

    def test_parse_http_range_rejects_invalid_range(self):
        self.assertIsNone(parse_http_range("bytes=200-100", 100))
