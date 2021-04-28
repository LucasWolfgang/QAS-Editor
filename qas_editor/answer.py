from .utils import FText, cdata_str
from .enums import Format
from xml.etree import ElementTree as et

class Answer:
    """
    This is the basic class used to hold possible answers
    """

    def __init__(self, fraction: float, text: str, feedback: FText, 
                formatting: Format=None) -> None:
        self.fraction = fraction
        self.formatting = formatting
        self.text = text
        self.feedback = feedback

    @classmethod
    def from_xml(cls, root: et.Element, *args) -> "Answer":
        data = {x.tag: x for x in root}
        fraction = root.get("fraction")
        text = data["text"].text
        feedback = FText.from_xml(data.get("feedback"))
        formatting = Format.get(root.get("format"))
        return cls(*args, fraction, text, feedback, formatting)

    def to_xml(self) -> et.Element:
        answer = et.Element("answer", {"fraction": str(self.fraction)})  
        if self.formatting:
            answer.set("format", self.formatting.value)
        answer.set("fraction", str(self.fraction))
        et.SubElement(answer, "text").text = cdata_str(self.text)
        self.feedback.to_xml(answer, "feedback")
        return answer

# ----------------------------------------------------------------------------------------

class Choice:
    """[summary]
    """

    def __init__(self, text: str, group: int=1, unlimited: bool=False) -> None:
        self.text = text
        self.group = group
        self.unlimited = unlimited

    @classmethod
    def from_xml(cls, root: et.Element) -> "Choice":
        data = {x.tag: x for x in root}
        text = data["text"].text
        group = int(data["group"].text)
        unlimited = True if data.get("infinite") else False
        return cls(text, group, unlimited)

    def to_xml(self) -> et.Element:
        dragbox = et.Element("dragbox")
        et.SubElement(dragbox, "text").text = self.text
        et.SubElement(dragbox, "group").text = str(self.group)
        if self.unlimited:
           et.SubElement(dragbox, "infinite")
        return dragbox

# ----------------------------------------------------------------------------------------

class NumericalAnswer(Answer):
    """
    This class represents a numerical answer.
    This inherits the Answer class and the answer is still
    a string.

    This class additionally includes tolerance, currently only
    the absolute tolerance can be specified via tol method 
    when initializing.
    """

    def __init__(self, tol: float=0.1, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tolerance = tol

    @classmethod
    def from_xml(cls, root: et.Element, *args) -> "NumericalAnswer":
        data = {x.tag: x for x in root}
        tolerance = data["tolerance"].text
        answer = super().from_xml(root, *args, tolerance)
        return answer

    def to_xml(self) -> et.Element:
        answer = super().to_xml()
        tolerance = et.SubElement(answer, "tolerance")
        tolerance.text = str(self.tolerance)
        return answer

# ----------------------------------------------------------------------------------------

class CalculatedAnswer(NumericalAnswer):
    
    def __init__(self, tolerance_type: int=1, correct_answer_format: int=1, 
                correct_answer_length: int=1, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tolerance_type = tolerance_type
        self.correct_answer_format = correct_answer_format
        self.correct_answer_length = correct_answer_length

    @classmethod
    def from_xml(cls, root: et.Element) -> "CalculatedAnswer":
        data = {x.tag: x for x in root}
        tolerance_type = data["tolerancetype"].text
        correct_answer_format = data["correctanswerformat"].text
        correct_answer_length = data["correctanswerlength"].text
        answer: "CalculatedAnswer" = super().from_xml(root, tolerance_type, 
                                                    correct_answer_format, 
                                                    correct_answer_length)
        return answer

    def to_xml(self) -> et.Element:
        answer = super().to_xml()
        et.SubElement(answer, "tolerancetype").text = str(self.tolerance_type)
        et.SubElement(answer, "correctanswerformat").text = str(self.correct_answer_format)
        et.SubElement(answer, "correctanswerlength").text = str(self.correct_answer_length)
        return answer

