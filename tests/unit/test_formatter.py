import unittest

from app.notifications.formatter import split_message


class FormatterTestCase(unittest.TestCase):
    def test_split_message_respects_limit(self) -> None:
        body = "line-1\nline-2\nline-3\n"

        segments = split_message(body, max_length=10)

        self.assertEqual(segments, ["line-1", "line-2", "line-3"])


if __name__ == "__main__":
    unittest.main()
