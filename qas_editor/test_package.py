import unittest
from .quiz import Quiz
import pprint

class TestIO(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.XML_EXAMPLE = "./testcases/moodle.xml"
        cls.XML_TEST = "./testcases/moodle_2.xml"
        
    def test_xml(self):
        data = Quiz.read_xml(self.XML_EXAMPLE)
        data.write_xml(self.XML_TEST, True)
        with open(self.XML_EXAMPLE, 'r') as infile:
            control = infile.read()
        with open(self.XML_TEST, 'r') as infile:
            data = infile.read()
        self.assertEqual(control, data)

def run_tests() -> None:
    unittest.main()