import unittest
from slug import slugify

class SlugTest(unittest.TestCase):
    def test_spaces(self):
        self.assertEqual(slugify("Hello World"), "hello-world")

    def test_punctuation_removed(self):
        self.assertEqual(slugify("Ready, set: go!"), "ready-set-go")

if __name__ == "__main__":
    unittest.main()
