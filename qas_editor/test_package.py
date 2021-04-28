from typing import OrderedDict
import unittest
from .quiz import Quiz
from xml.etree import ElementTree as et

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
        self.assertTrue(control == data)

    # def get_xml_diff(elem1: et.Element, elem2: et.Element, diffs: dict) -> None:
    #     diffs[elem1.tag] = {}
    #     if elem1.attrib != elem2.attrib:
    #         if len(elem1.attrib) > len(elem2.attrib):
    #             diffs[elem1.tag] = set(elem1.attrib) - set(elem2.attrib)
    #         elif len(elem1.attrib) < len(elem2.attrib):
    #             diffs[elem1.tag] = set(elem2.attrib) - set(elem1.attrib)
    #         else:
    #             diffs[elem1.tag] = "<<Wolfs>>"
    #     felem = elem1 if len(elem1) > len(elem2) else elem2
    #     selem = elem1 if len(elem1) < len(elem2) else elem2
    #     for f in felem:
    #         for s in selem
        
        
def run_tests() -> None:
    unittest.main()