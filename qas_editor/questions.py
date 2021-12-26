from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import List, Dict
    from .enums import Direction
from .quiz import Quiz
from xml.etree import ElementTree as et
from .wrappers import B64File, CombinedFeedback, Dataset, FText, MultipleTries, \
                    SelectOption, Subquestion, Unit, Tags, UnitHandling
from .utils import extract
from .enums import Format, ResponseFormat, Status, Distribution, Numbering
from .answer import Answer, ClozeItem, ClozeItem, NumericalAnswer, DragText, \
                    CrossWord, CalculatedAnswer, DropZone, DragItem
import re
import logging
log = logging.getLogger(__name__)
# import markdown
# import latex2mathml

class Question():
    """
    This is an abstract class Question used as a parent for specific types of Questions.
    """
    _type=None

    def __init__(self, name: str, question_text: FText=None, default_grade: float=1.0, 
                general_feedback: FText=None, id_number: int=None, shuffle: bool=False,
                tags: Tags=None, solution: str=None, *args, **kwargs) -> None:
        """
        [summary]

        Args:
            name (str): name of the question
            question_text (FText): text of the question
            default_grade (float): the default mark
            general_feedback (str, optional): general feedback. Defaults to None.
            id_number (int, optional): id number. Defaults to None.
            shuffle (bool, optional): shuffle answers. Defaults to False.
        """
        self.name = name
        self.question_text = question_text
        self.default_grade = default_grade
        self.general_feedback = general_feedback
        self.id_number = id_number
        self.shuffle = shuffle
        self.solution = solution
        self.tags = tags
        self.__parent: Quiz = None

    def __repr__(self):
        """ 
        Change string representation.
        """
        return f"Type: {self.__class__.__name__}, name: \'{self.name}\'."

    @property
    def parent(self):
        return self.__parent

    @parent.getter
    def parent(self):
        return self.__parent

    @parent.setter
    def parent(self, value: Quiz):
        if self.__parent:
            self.__parent._questions.remove(self)
        if isinstance(value, Quiz):
            self.__parent = value
            self.__parent._questions.append(self)

    @classmethod
    def from_json(cls, data) -> "Question":
        data["question_text"] = FText.from_json(data["question_text"])
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, **kwargs) -> "Question":
        data = {x.tag: x for x in root}
        res = {}
        res["name"] = data['name'][0].text
        res["question_text"] = FText.from_xml(data['questiontext'])
        res["general_feedback"] = FText.from_xml(data.get('generalfeedback'))
        extract(data, "defaultgrade"  , res, "default_grade", float)
        extract(data, "idnumber"      , res, "id_number"    , int)
        extract(data, "shuffleanswers", res, "shuffle"      , bool)
        res["tags"] = Tags.from_xml(data.get("tags"))
        question = cls(**kwargs, **res)
        return question

    def to_xml(self) -> et.Element:
        """
        This method converts current object to Moodle XML.
        """
        question = et.Element("question")
        question.set("type", self._type)
        name = et.SubElement(question, "name")
        et.SubElement(name, "text").text = str(self.name)
        self.question_text.to_xml(question, "questiontext")
        if self.general_feedback:
            self.general_feedback.to_xml(question, "generalfeedback")
        et.SubElement(question, "defaultgrade").text = str(self.default_grade)
        et.SubElement(question, "hidden").text = "0"
        if self.id_number is not None:
            et.SubElement(question, "idnumber").text = str(self.id_number)
        if self.shuffle:
            et.SubElement(question, "shuffleanswers").text = "true"
        if self.tags:
            question.append(self.tags.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class QCalculated(Question):
    _type = "calculated"

    def __init__(self, synchronize: int=0, single: bool=False, unit_handling: UnitHandling=None, 
                units: List[Unit]=None, datasets: List[Dataset]=None, 
                answers: List[CalculatedAnswer]=None, multiple_tries: MultipleTries=None, 
                *args, **kwargs):
        """[summary]

        Args:
            synchronize (int): [description]
            single (bool, optional): [description]. Defaults to False.
            unit_handling (UnitHandling, optional): [description]. Defaults to None.
            units (List[Unit], optional): [description]. Defaults to None.
            datasets (List[Dataset], optional): [description]. Defaults to None.
            answers (List[CalculatedAnswer], optional): [description]. Defaults to None.
        """
        super().__init__(*args, **kwargs)
        self.synchronize = synchronize
        self.single = single
        self.unit_handling = unit_handling
        self.multiple_tries = multiple_tries
        self.units: List[Unit] = units if units is not None else []
        self.datasets: List[Dataset] = datasets if datasets is not None else []
        self.answers: List[CalculatedAnswer] = answers if answers is not None else []

    def add_answer(self, fraction: float, text: str, **kwargs) -> None:
        self.answers.append(CalculatedAnswer(fraction=fraction, text=text, **kwargs))

    def add_dataset(self, status: Status, name: str, dist: Distribution, minim: float,
                    maxim: float, dec: int ) -> None:
        self.datasets.append(Dataset(status, name, dist, minim, maxim, dec))

    def add_unit(self, name: str, multiplier: float) -> None:
        self.units.append(Unit(name, multiplier))

    @classmethod
    def from_json(cls, data) -> "QCalculated":
        data["unit_handling"] = UnitHandling.from_json(data["unit_handling"])
        data["multiple_tries"] = MultipleTries.from_json(data["multiple_tries"])
        for i in range(len(data["units"])):
            data["units"][i] = Unit.from_json(data["units"][i])
        for i in range(len(data["datasets"])):
            data["datasets"][i] = Dataset.from_json(data["datasets"][i])
        for i in range(len(data["answers"])):
            data["answers"][i] = CalculatedAnswer.from_json(data["answers"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element) -> "QCalculated":
        data = {x.tag: x for x in root}
        res = {}
        extract(data, "synchronize", res, "synchronize", int)
        extract(data, "single"     , res, "single"     , bool)
        res["unit_handling"] = UnitHandling.from_xml(data)
        res["multiple_tries"] = MultipleTries.from_xml(data, root)
        question: "QCalculated" = super().from_xml(root, **res)
        for u in root.findall("units"):
            question.units.append(Unit.from_xml(u))
        for ds in data["dataset_definitions"]:
            question.datasets.append(Dataset.from_xml(ds))
        for ans in root.findall("answer"):
            question.answers.append(CalculatedAnswer.from_xml(ans))
        return question

    def to_xml(self) -> et.Element:
        question = super().to_xml()
        et.SubElement(question, "synchronize").text = self.synchronize
        et.SubElement(question, "single").text = self.single
        for answer in self.answers:
            question.append(answer.to_xml())
        self.unit_handling.to_xml(question)
        self.multiple_tries.to_xml(question)
        if self.units:
            units = et.SubElement(question, "units")
            for unit in self.units:
                units.append(unit.to_xml())
        if self.datasets:
            dataset_definitions = et.SubElement(question, "dataset_definitions")
            for dataset in self.datasets:
                dataset_definitions.append(dataset.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class QCalculatedSimple(QCalculated):
    _type = "calculatedsimple"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

# ----------------------------------------------------------------------------------------

class QCalculatedMultichoice(Question):
    _type = "calculatedmulti"

    def __init__(self, synchronize: int=0, single: bool=False, 
                numbering: Numbering=Numbering.ALF_LR, 
                combined_feedback: CombinedFeedback=None, multiple_tries: MultipleTries=None,
                datasets: List[Dataset]=None, answers: List[CalculatedAnswer]=None,
                *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.synchronize = synchronize
        self.single = single
        self.numbering = numbering
        self.combined_feedback = combined_feedback if combined_feedback else CombinedFeedback()
        self.multiple_tries = multiple_tries
        self.datasets: List[Dataset] = datasets if datasets is not None else []
        self.answers: List[CalculatedAnswer] = answers if answers is not None else []

    def add_answer(self, fraction: float, text: str, **kwargs) -> None:
        self.answers.append(CalculatedAnswer(fraction=fraction, text=text, **kwargs))

    def add_dataset(self, status: Status, name: str, dist: Distribution, minim: float,
                    maxim: float, dec: int ) -> None:
        self.datasets.append(Dataset(status, name, "calculated", dist, minim, maxim, dec))

    def add_unit(self, name: str, multiplier: float) -> None:
        self.units.append(Unit(name, multiplier))

    @classmethod
    def from_json(cls, data: dict) -> QCalculatedMultichoice:
        data["numbering"] = Numbering(data["numbering"])
        data["combined_feedback"] = CombinedFeedback.from_json(data["combined_feedback"])
        data["multiple_tries"] = MultipleTries.from_json(data["multiple_tries"])
        for i in range(len(data["datasets"])):
            data["datasets"][i] = Dataset.from_json(data["datasets"][i])
        for i in range(len(data["answers"])):
            data["answers"][i] = CalculatedAnswer.from_json(data["answers"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element) -> "Question":
        data = {x.tag: x for x in root}
        res = {}
        extract(data, "synchronize"    , res, "synchronize", int)
        extract(data, "single"         , res, "single"     , bool)
        res["numbering"] = Numbering(data["answernumbering"].text)
        res["combined_feedback"] = CombinedFeedback.from_xml(root)
        res["multiple_tries"] = MultipleTries.from_xml(data, root)
        question: "QCalculatedMultichoice" = super().from_xml(root, **res)
        for dataset in data["dataset_definitions"]:
            question.datasets.append(Dataset.from_xml(dataset))
        for answer in root.findall("answer"):
            question.answers.append(CalculatedAnswer.from_xml(answer))
        return question

    def to_xml(self) -> et.Element:
        question = super().to_xml()
        et.SubElement(question, "synchronize").text = str(self.synchronize)
        et.SubElement(question, "single").text = str(self.single).lower()
        et.SubElement(question, "answernumbering").text = self.numbering.value
        self.combined_feedback.to_xml(question)
        self.multiple_tries.to_xml(question)
        for answer in self.answers:
            question.append(answer.to_xml()) 
        dataset_definitions = et.SubElement(question, "dataset_definitions")
        for dataset in self.datasets:
            dataset_definitions.append(dataset.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class QCloze(Question):
    """This is a very simples class that hold cloze data. All data is compressed inside
    the question text, so no further implementation is necessary.
    """
    _type = "cloze"

    def __init__(self, answers: List[ClozeItem]=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.answers: List[ClozeItem] = answers if answers is not None else []
    
    @classmethod
    def from_json(cls, data: dict) -> "QCloze":
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element) -> "QCloze":
        return super().from_xml(root)

    @classmethod
    def from_cloze(cls, buffer) -> "QCloze":
        data = buffer.read()
        name, text = data.split("\n", 1)
        new_text = []
        index = 0
        answers: List[ClozeItem] = []
        pattern = re.compile(r"(?!\\)\{(\d+)?(?:\:(.*?)\:)(.*?(?!\\)\})")
        for n, a in enumerate(pattern.finditer(text)):
            item = ClozeItem.from_cloze(a)
            answers.append(item)
            new_text.append(text[index:item.start])
            new_text.append(f"<span style=\"background:red\">[[{n:02}]]</span>")
            index = a.end()
        ftext = FText("".join(new_text), Format.HTML)
        return cls(name=name, question_text=ftext, answers=answers)
    
    def to_xml(self) -> et.Element:
        text = [] 
        last = 0
        for answer in self.answers:
            text.append(self.question_text.text[last:answer.start])
            text.append(str(answer))
            last = answer.start + 42
        tmp = self.question_text.text
        self.question_text.text = "".join(text)
        result = super().to_xml()
        self.question_text.text = tmp
        return result

# ----------------------------------------------------------------------------------------

class QDescription(Question):
    _type = "description"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    @classmethod
    def from_json(cls, data: dict) -> "QCloze":
        return super().from_json(data)

    @classmethod
    def from_gift(cls, header: list) -> "QDescription":
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        return cls(name=header[1], question_text=FText(header[3], formatting))

    @classmethod
    def from_xml(cls, root: et.Element) -> "QCloze":
        return super().from_xml(root)

    def to_xml(self) -> et.Element:
        return super().to_xml()

# ----------------------------------------------------------------------------------------

class QDragAndDropText(Question):
    """
    This class represents a drag and drop text onto image question. 
    It inherits from abstract class Question.
    """
    _type = "ddwtos"

    def __init__(self, combined_feedback: CombinedFeedback=None, 
                multiple_tries: MultipleTries=None, answers: List[DragText]=None, *args, 
                **kwargs):
        """
        Currently not implemented.
        """
        super().__init__(*args, **kwargs)
        self.combined_feedback = combined_feedback
        self.multiple_tries = multiple_tries
        self.answers: List[DragText] = answers if answers is not None else []

    @classmethod
    def from_json(cls, data) -> "QDragAndDropText":
        data["combined_feedback"] = CombinedFeedback.from_json(data["combined_feedback"])
        data["multiple_tries"] = MultipleTries.from_json(data["multiple_tries"])
        for i in range(len(data["answers"])):
            data["answers"][i] = DragText.from_json(data["answers"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element) -> "QDragAndDropText":    
        res = {} 
        data = {x.tag: x for x in root}
        res["combined_feedback"] = CombinedFeedback.from_xml(root)
        res["multiple_tries"] = MultipleTries.from_xml(data, root)
        question: "QDragAndDropText" = super().from_xml(root, **res)
        for c in root.findall("dragbox"):
            question.answers.append(DragText.from_xml(c))
        return question

    def to_xml(self) -> et.Element:
        question = super().to_xml()
        self.multiple_tries.to_xml(question)
        self.combined_feedback.to_xml(question)
        for choice in self.answers:
            question.append(choice.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class QDragAndDropImage(Question):
    """
    This class represents a drag and drop onto image question. 
    It inherits from abstract class Question.
    """
    _type = "ddimageortext"

    def __init__(self, background: B64File=None, combined_feedback: CombinedFeedback=None, 
                dragitems: List[DragItem]=None, dropzones: List[DropZone]=None,
                *args, **kwargs) -> None:
        """Creates an drag and drop onto image type of question.

        Args:
            background (str): Filepath to the background image.
        """
        super().__init__(*args, **kwargs)
        self.background = background
        self.combined_feedback = combined_feedback
        self._dragitems: List[DragItem] = dragitems if dragitems is not None else []
        self._dropzones: List[DropZone] = dropzones if dropzones is not None else []

    def add_dragimage(self, text: str, group: int, file: str, unlimited: bool=False) -> None:
        """Adds new DragItem with assigned DropZones.

        Args:
            file (str): path to image to be used as a drag image;
            text (str, optional): text of the drag text.
            group (int, optional): group.
            unlimited (bool, optional): if item is allowed to be used again. Defaults to False.
        """
        dragimage = DragItem(len(self._dragitems) + 1, text, unlimited, group, file=file)
        self._dragitems.append(dragimage)

    def add_dragtext(self, text: str, group: str, unlimited: bool=False) -> None:
        """Adds new DragText with assigned DropZones.

        Args:
            text (str): text of the drag text. 
            group (str): group.
            unlimited (bool, optional): if item is allowed to be used again. Defaults to False.
        """
        dragitem = DragItem(len(self._dragitems) + 1, text, unlimited, group)
        self._dragitems.append(dragitem)

    def add_dropzone(self, x: int, y: int, text: str, choice: int) -> None:
        """[summary]

        Args:
            x (int): [description]
            y (int): [description]
            text (str): [description]
            choice (int): [description]
        """
        self._dropzones.append(DropZone(x, y, text, choice, len(self._dropzones) + 1))

    @classmethod
    def from_json(cls, data) -> "QDragAndDropImage":
        data["combined_feedback"] = CombinedFeedback.from_json(data["combined_feedback"])
        data["background"] = B64File.from_json(data["background"])
        for i in range(len(data["_dragitems"])):
            data["_dragitems"][i] = DragItem.from_json(data["_dragitems"][i])
        for i in range(len(data["_dropzones"])):
            data["_dropzones"][i] = DropZone.from_json(data["_dropzones"][i])   
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element) -> "QDragAndDropImage":
        data = {x.tag: x for x in root}
        res = {}
        res["combined_feedback"] = CombinedFeedback.from_xml(root)
        res["background"] = B64File.from_xml(data.get("file"))
        question: "QDragAndDropImage" = super().from_xml(root, **res)
        for dragitem in root.findall("drag"):
            question._dragitems.append(DragItem.from_xml(dragitem))
        for dropzone in root.findall("drop"):
            question._dropzones.append(DropZone.from_xml(dropzone))
        return question

    def to_xml(self):
        question = super().to_xml()
        self.combined_feedback.to_xml(question)
        if self.background:
            question.append(self.background.to_xml())
        for dragitem in self._dragitems:
            question.append(dragitem.to_xml())
        for dropzone in self._dropzones:
            question.append(dropzone.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class QDragAndDropMarker(Question):
    _type = "ddmarker"

    def __init__(self, background: B64File=None, combined_feedback: CombinedFeedback=None,
                multiple_tries: MultipleTries=None, dragitems: List[DragItem]=None, 
                dropzones: List[DropZone]=None, highlight_empty: bool=False, *args, **kwargs):
        """Creates an drag and drop onto image type of question.

        Args:
            background (str): Filepath to the background image.
        """
        super().__init__(*args, **kwargs)
        self.background = background
        self.combined_feedback = combined_feedback
        self.multiple_tries = multiple_tries
        self.highlight_empty = highlight_empty
        self._dragitems: List[DragItem] = dragitems if dragitems is not None else []
        self._dropzones: List[DropZone] = dropzones if dropzones is not None else []

    def add_dragmarker(self, text: str, no_of_drags: str, unlimited: bool=False):
        """[summary]

        Args:
            text (str): [description]
            no_of_drags (str): [description]
            unlimited (bool, optional): [description]. Defaults to False.
        """
        dragitem = DragItem(len(self._dragitems) + 1, text, unlimited, no_of_drags=no_of_drags)
        self._dragitems.append(dragitem)

    @classmethod
    def from_json(cls, data) -> "QDragAndDropMarker":
        data["multiple_tries"] = MultipleTries.from_json(data["multiple_tries"])
        data["combined_feedback"] = CombinedFeedback.from_json(data["combined_feedback"])
        data["background"] = B64File.from_json(data["background"])
        for i in range(len(data["_dragitems"])):
            data["_dragitems"][i] = DragItem.from_json(data["_dragitems"][i])
        for i in range(len(data["_dropzones"])):
            data["_dropzones"][i] = DropZone.from_json(data["_dropzones"][i])   
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element) -> "QDragAndDropMarker":
        data = {x.tag: x for x in root}
        res = {}
        res["background"] = B64File.from_xml(data.get("file"))
        extract(data, "showmisplaced", res, "highlight_empty", bool)
        res["combined_feedback"] = CombinedFeedback.from_xml(root)
        res["multiple_tries"] = MultipleTries.from_xml(data, root)
        question: "QDragAndDropMarker" = super().from_xml(root, **res)
        for dragitem in root.findall("drag"):
            question._dragitems.append(DragItem.from_xml(dragitem))
        for dropzone in root.findall("drop"):
            question._dropzones.append(DropZone.from_xml(dropzone))
        return question

    def to_xml(self):
        question = super().to_xml()
        if self.highlight_empty:
            et.SubElement(question, "showmisplaced")
        self.multiple_tries.to_xml(question)
        self.combined_feedback.to_xml(question)
        for dragitem in self._dragitems:
            question.append(dragitem.to_xml())
        for dropzone in self._dropzones:
            question.append(dropzone.to_xml())
        if self.background:
            question.append(self.background.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class QEssay(Question):
    _type = "essay"

    def __init__(self, response_format: ResponseFormat=ResponseFormat.HTML,         
                response_required: bool=True, lines: int=10, attachments: int=1, 
                attachments_required: bool=False, maxbytes: int=None, 
                filetypes_list: str=None, grader_info: FText=None, 
                response_template: FText=None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.response_format = response_format
        self.response_required = response_required
        self.responsefield_lines = lines
        self.attachments = attachments
        self.attachments_required = attachments_required
        self.maxbytes = maxbytes
        self.filetypes_list = filetypes_list
        self.grader_info = grader_info
        self.response_template = response_template

    @classmethod
    def from_gift(cls, header: list, answer: list) -> "QEssay":
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        return cls(name=header[1], question_text=FText(header[3], formatting))

    @classmethod
    def from_json(cls, data) -> "QEssay":
        data["response_format"] = ResponseFormat(data["response_format"])
        data["grader_info"] = FText.from_json(data["grader_info"])
        data["response_template"] = FText.from_json(data["response_template"])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element) -> "QEssay":
        data = {x.tag: x for x in root}
        res = {}
        res["response_format"] = ResponseFormat(data["responseformat"].text)
        extract(data, "responserequired"   , res, "response_required" , bool)
        extract(data, "responsefieldlines" , res, "lines"      , int)
        extract(data, "attachments"        , res, "attachments", int)
        extract(data, "attachmentsrequired", res, "attachments_required", bool)
        extract(data, "maxbytes"           , res, "maxbytes", int)
        extract(data, "filetypeslist"      , res, "filetypes_list", str)
        res["grader_info"] = FText.from_xml(data.get("graderinfo"))
        res["response_template"] = FText.from_xml(data.get("responsetemplate"))
        question = super().from_xml(root, **res)
        return question

    def to_xml(self) -> et.Element:
        question = super().to_xml()
        et.SubElement(question, "responseformat").text = self.response_format.value
        if self.response_required: et.SubElement(question, "responserequired")
        et.SubElement(question, "responsefieldlines").text = str(self.responsefield_lines)
        et.SubElement(question, "attachments").text = str(self.attachments)
        if self.attachments_required: et.SubElement(question, "attachmentsrequired")
        if self.maxbytes:
            et.SubElement(question, "maxbytes").text = str(self.maxbytes)
        if self.filetypes_list:
            et.SubElement(question, "filetypeslist").text = self.filetypes_list
        if self.grader_info:
            self.grader_info.to_xml(question, "graderinfo")
        if self.response_template:
            self.response_template.to_xml(question, "responsetemplate")
        return question

# ----------------------------------------------------------------------------------------

class QMatching(Question):
    IMPLEMENTED = False
    _type = "matching"

    def __init__(self, combined_feedback: CombinedFeedback=None, 
                subquestions: List[Subquestion]=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.combined_feedback = combined_feedback
        self.subquestions = subquestions if subquestions is not None else []

    def add_subquestion(self, text: str, answer: str) -> None:
        """[summary]

        Args:
            text (str): [description]
            answer (str): [description]
        """
        if isinstance(text, str) and isinstance(answer, str):
            self.subquestions.append((text, answer))

    @classmethod
    def from_gift(cls, header: list, answer: list) -> "QMatching":
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(name=header[1], question_text=FText(header[3], formatting))
        for a in answer:
            if a[0] == "=":
                g = re.match(r"(.*?)(?<!\\)->(.*)", a[2])
                qst.subquestions.append(Subquestion(formatting, g[1].strip(), g[2].strip()))
            elif a[0] == "####":
                qst.general_feedback = FText(a[2], formatting)
        return qst

    @classmethod
    def from_json(cls, data) -> "QMatching":
        data["combined_feedback"] = CombinedFeedback.from_json(data["combined_feedback"])
        for i in range(len(data["subquestions"])):
            data["subquestions"][i] = Subquestion.from_json(data["subquestions"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element) -> "QMatching":
        res = {}
        res["combined_feedback"] = CombinedFeedback.from_xml(root)
        question: "QMatching" = super().from_xml(root, **res)
        for sub in root.findall("subquestion"):
            question.subquestions.append(Subquestion.from_xml(sub))
        return question

    def to_xml(self) -> et.Element:
        question = super().to_xml()
        if self.combined_feedback:
            self.combined_feedback.to_xml(question)
        for sub in self.subquestions:
            question.append(sub.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class QRandomMatching(Question):
    _type = "randomsamatch"

    def __init__(self, choose: int=0, subcats: bool=False, 
                combined_feedback: CombinedFeedback=None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.combined_feedback = combined_feedback
        self.choose = choose
        self.subcats = subcats

    @classmethod
    def from_json(cls, data) -> "QRandomMatching":
        data["combined_feedback"] = CombinedFeedback.from_json(data["combined_feedback"])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element) -> "QRandomMatching":
        data = {x.tag: x for x in root}
        res = {}
        res["combined_feedback"] = CombinedFeedback.from_xml(root)
        res["choose"] = data["choose"].text
        res["subcats"] = data["subcats"].text
        question = super().from_xml(root, **res)
        return question

    def to_xml(self) -> et.Element:
        question = super().to_xml()
        self.combined_feedback.to_xml(question)
        et.SubElement(question, "choose").text = self.choose
        et.SubElement(question, "subcats").text = self.subcats
        return question

# ----------------------------------------------------------------------------------------

class QMissingWord(Question):
    _type = "gapselect"

    def __init__(self, combined_feedback: CombinedFeedback=None,
                options: List[SelectOption]=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.combined_feedback = combined_feedback
        self.options = options if options is not None else []

    @classmethod
    def from_json(cls, data) -> "QMissingWord":
        data["combined_feedback"] = CombinedFeedback.from_json(data["combined_feedback"])
        for i in range(len(data["options"])):
            data["options"][i] = SelectOption.from_json(data["options"][i])
        return super().from_json(data)

    @classmethod
    def from_gift(cls, header: list, answer: list) -> "QMissingWord":
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(name=header[1], question_text=FText(header[3], formatting))
        correct = None
        for i in answer:
            if i[0] == "=":
                correct = SelectOption(i[2], 1)
            else:
                qst.options.append(SelectOption(i[2], 1))
        qst.options.insert(0, correct)
        return qst

    @classmethod
    def from_xml(cls, root: et.Element) -> "QMissingWord":
        res = {}
        res["combined_feedback"] = CombinedFeedback.from_xml(root)
        question: "QMissingWord" = super().from_xml(root, **res)
        for option in root.findall("selectoption"):
            question.options.append(SelectOption.from_xml(option))
        return question

    def to_xml(self) -> et.Element:
        question = super().to_xml()
        if self.combined_feedback:
            self.combined_feedback.to_xml(question)
        for opt in self.options:
            question.append(opt.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class QMultichoice(Question):
    """
    This class represents 'Multiple choice' question.
    """
    _type = "multichoice"

    def __init__(self, single: bool=True, show_instruction: bool=False,
                answer_numbering: Numbering=Numbering.ALF_LR, 
                multiple_tries: MultipleTries=None,
                combined_feedback: CombinedFeedback=None, answers: List[Answer]=None,
                *args, **kwargs):
        """
        [summary]

        Args:
            answer_numbering (str, optional): [description]. Defaults to "abc".
        """
        super().__init__(*args, **kwargs)
        self.single = single
        self.show_instruction = show_instruction
        self.combined_feedback = combined_feedback
        self.multiple_tries = multiple_tries
        if isinstance(answer_numbering, Numbering):
           self.answer_numbering = answer_numbering
        elif isinstance(answer_numbering, str):
            self.answer_numbering = Numbering(answer_numbering)
        else:
            raise TypeError(f"answer_numbering should be of type Numbering or str, not {type(answer_numbering)}")
        self.answers = answers if answers is not None else []

    @classmethod
    def from_json(cls, data) -> "QMultichoice":
        data["answer_numbering"] = Numbering(data["answer_numbering"])
        data["multiple_tries"] = MultipleTries.from_json(data["multiple_tries"])
        data["combined_feedback"] = CombinedFeedback.from_json(data["combined_feedback"])
        for i in range(len(data["answers"])):
            data["answers"][i] = Answer.from_json(data["answers"][i])
        return super().from_json(data)

    @classmethod
    def from_aiken(cls, buffer, name) -> "QMultichoice":
        header = buffer.rd(True)
        answers = []
        while buffer.rd() and "ANSWER:" not in buffer.rd()[:7]:
            ans = re.match(r"[A-Z]+\) (.+)", buffer.rd(True))
            if ans: answers.append(Answer(fraction=0.0, text=ans[1], formatting=Format.PLAIN))
        try:        
            answers[ord(buffer.rd(True)[8].upper())-65].fraction = 100.0
        except IndexError: 
            log.exception(f"Failed to set correct answer in question {name} during Aiken import.")
        return cls(name=name, question_text=FText(header, Format.PLAIN), answers=answers)

    @classmethod
    def from_gift(cls, header: list, answer: list) -> "QMultichoice":
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(name=header[1], question_text=FText(header[3], formatting))
        prev_answer = None
        for a in answer:
            txt = a[2]
            if a[0] == "~": # Wrong or partially correct answer
                fraction = 0 if not a[1] else float(a[1][1:-1])
                prev_answer = Answer(fraction, txt, formatting=formatting)
                qst.answers.append(prev_answer)
            elif a[0] == "=": # Correct answer
                prev_answer = Answer(100, txt, formatting=formatting)
                qst.answers.append(prev_answer)
            elif a[0] == "#": # Answer feedback
                prev_answer.feedback = FText(a[2], formatting)
        return qst

    @classmethod
    def from_xml(cls, root: et.Element) -> "QMultichoice":
        data = {x.tag: x for x in root}
        res = {}
        extract(data, "single"                 , res, "single"          , bool)
        extract(data, "showstandardinstruction", res, "show_instruction", bool)
        res["answer_numbering"] = Numbering(data["answernumbering"].text)
        res["combined_feedback"] = CombinedFeedback.from_xml(root)
        res["multiple_tries"] = MultipleTries.from_xml(data, root)
        question: "QMultichoice" = super().from_xml(root, **res)
        for answer in root.findall("answer"):
            question.answers.append(Answer.from_xml(answer))
        return question

    def to_xml(self) -> et.Element:
        """[summary]

        Returns:
            [type]: [description]
        """
        question = super().to_xml()
        self.multiple_tries.to_xml(question)
        if self.combined_feedback:
            self.combined_feedback.to_xml(question)
        et.SubElement(question, "answernumbering").text = self.answer_numbering.value
        et.SubElement(question, "single").text = str(self.single).lower()
        for answer in self.answers:
            question.append(answer.to_xml())
        return question

    def add_answer(self, fraction: float, text: str, feedback :str=None) -> None:
        """
        Adds an answer to this question.

        Args:
            fraction (float): Percentage of the grade
            text (str): text of the anwser
            feedback (str, optional): feedback shown when this answer is submitted. Defaults to None.
        """
        self.answers.append(Answer(fraction, text, feedback))

    @staticmethod
    def from_markdown(lines: list, answer_mkr: str, question_mkr: str, 
                        answer_numbering: Numbering, shuffle_answers: bool, penalty: float, 
                        name: str="mkquestion") -> "QMultichoice":
        """[summary]

        Returns:
            [type]: [description]
        """
        data = ""
        match = re.match(answer_mkr, lines[-1])
        while lines and match is None:        
            data += lines.pop().strip()
            match = re.match(answer_mkr, lines[-1])
        question: Question = QMultichoice(answer_numbering, name=name, 
                                        question_text=FText(data, Format.MD), 
                                        shuffle=shuffle_answers, penalty=penalty)
        regex_exp = f"({question_mkr})|({answer_mkr})"
        while lines:
            match = re.match(regex_exp, lines.pop())
            if match and match[3]: 
                question.add_answer(100.0 if match[4] is not None else 0.0, match[5], "")
            else:
                break
        return question

# ----------------------------------------------------------------------------------------

class QNumerical(Question):
    """
    This class represents 'Numerical Question' moodle question type.
    Units are currently not implemented, only numerical answer, which
    are specified as text and absolute tolerance value are implemented
    """
    _type = "numerical"

    def __init__(self, unit_handling: UnitHandling=None, units: List[Unit]=None, 
                answers: List[NumericalAnswer]=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unit_handling = unit_handling
        self.units = units if units is not None else []
        self.answers = answers if answers is not None else []

    def add_answer(self, tol: float, fraction: float, text: str, feedback: str=None) -> None:
        self.answers.append(NumericalAnswer(tol, fraction, text, feedback))

    def add_unit(self, name: str, multiplier: float) -> None:
        self.units.append(Unit(name, multiplier))

    @classmethod
    def from_json(cls, data) -> "QNumerical":
        data["unit_handling"] = UnitHandling.from_json(data["unit_handling"])
        for i in range(len(data["units"])):
            data["units"][i] = Unit.from_json(data["units"][i])
        for i in range(len(data["answers"])):
            data["answers"][i] = NumericalAnswer.from_json(data["answers"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element) -> "QNumerical":
        data = {x.tag: x for x in root}
        res = {}
        if "unit_handling" in data:
            res["unit_handling"] = UnitHandling.from_xml(data)
        question: "QNumerical" = super().from_xml(root, **res)
        for answer in root.findall("answer"):
            question.answers.append(NumericalAnswer.from_xml(answer))
        return question

    @classmethod
    def from_gift(cls, header:list, answer:list) -> "QNumerical":
        def _extract(data: str) -> tuple:
            g = re.match(r"(.+?)(:|(?:\.\.))(.+)", data)
            if g[2] == "..":
                txt = (float(g[1]) + float(g[3]))/2     # Converts min/max to value +- tol
                tol = txt - float(g[1])
                txt = str(txt)
            else:
                txt = g[1]
                tol = float(g[3])
            return txt, tol
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(name=header[1], question_text=FText(header[3], formatting))
        if len(answer) == 1:
            txt, tol = _extract(answer[0][2])
            qst.answers.append(NumericalAnswer(tol, 100, txt))
        elif len(answer) > 1:
            for ans in answer[1:]:
                if ans[0] == "=":
                    txt, tol = _extract(ans[2])
                    fraction = float(ans[1][1:-1]) if ans[0] == "=" else 0
                    a = NumericalAnswer(tol, fraction, txt)
                    qst.answers.append(a)
                elif ans[0] == "~":
                    a = NumericalAnswer(0, 0, "")
                elif ans[0] == "#":
                    a.feedback = FText(ans[2], formatting)
        return qst

    def to_xml(self):
        question = super().to_xml()
        for answer in self.answers:
            question.append(answer.to_xml())
        if self.unit_handling:
            self.unit_handling.to_xml(question)
        if len(self.units) > 0:
            units = et.SubElement(question, "units")
            for unit in self.units:
                units.append(unit.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class QShortAnswer(Question):
    """
    This class represents 'Short answer' question.
    """
    _type = "shortanswer"

    def __init__(self, use_case: bool=False, answers: List[Answer]=None, *args, **kwargs) -> None:
        """[summary]

        Args:
            use_case (bool): [description]
        """
        super().__init__(*args, **kwargs)
        self.use_case = use_case
        self.answers = answers if answers is not None else []

    def add_answer(self, fraction: float, text: str, feedback: str=None):
        """Adds an answer to this question.

        Args:
            fraction (float): Percentage of the grade
            text (str): text of the anwser
            feedback (str, optional): feedback shown when this answer is submitted. Defaults to None.
        """
        self.answers.append(Answer(fraction, text, feedback))

    @classmethod
    def from_json(cls, data) -> "QShortAnswer":
        for i in range(len(data["answers"])):
            data["answers"][i] = Answer.from_json(data["answers"][i])
        return super().from_json(data)

    @classmethod
    def from_gift(cls, header: list, answer: list) -> "QShortAnswer":
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(False, name=header[1], question_text=FText(header[3], formatting))
        for a in answer:
            fraction = 100 if not a[1] else float(a[1][1:-1])
            qst.answers.append(Answer(fraction, a[2], formatting=formatting))
        return qst

    @classmethod
    def from_xml(cls, root: et.Element) -> "Question":
        data = {x.tag: x for x in root}
        res = {}
        res["use_case"] = data["usecase"].text
        question: "QShortAnswer" = super().from_xml(root, **res)
        for answer in root.findall("answer"):
            question.answers.append(Answer.from_xml(answer))
        return question

    def to_xml(self):
        question = super().to_xml()
        et.SubElement(question, "usecase").text = self.use_case
        for answer in self.answers:
            question.append(answer.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class QTrueFalse(Question):
    """
    This class represents true/false question.
    """
    _type = "truefalse"

    def __init__(self, correct_answer: bool=False, true_ans: Answer=None, 
                false_ans: Answer=None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.__answer_true = true_ans
        self.__answer_false = false_ans
        self.correct_answer = correct_answer

    def set_feedbacks(self, correct: FText, incorrect: FText):
        self.__answer_true.feedback = correct if self.correct_answer else incorrect
        self.__answer_false.feedback = correct if not self.correct_answer else incorrect

    @property
    def correct_answer(self) -> bool:
        return self.__correct_answer

    @correct_answer.setter
    def correct_answer(self, value: bool) -> None:
        self.__answer_true.fraction = 100 if value else 0
        self.__answer_false.fraction = 100 if not value else 0
        self.__correct_answer = value

    @classmethod
    def from_json(cls, data) -> "QTrueFalse":
        data["true_ans"] = Answer.from_json(data["_QTrueFalse__answer_true"])
        data["false_ans"] = Answer.from_json(data["_QTrueFalse__answer_false"])
        return super().from_json(data)

    @classmethod
    def from_gift(cls, header: list, answer: list) -> "QTrueFalse":
        correct = answer.pop(0)[0].lower() in ["true", "t"]
        true_ans = Answer(0, "true")
        false_ans = Answer(0, "false")
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(correct, true_ans, false_ans, name=header[1], 
                question_text=FText(header[3], formatting))
        for ans in answer:
            if ans[0] == "####":
                qst.general_feedback = FText(ans[2], Format(header[2][1:-1]))
            elif false_ans.feedback is None:
                false_ans.feedback = FText(ans[2], Format(header[2][1:-1]))
            else:
                true_ans = FText(ans[2], Format(header[2][1:-1]))
        return qst

    @classmethod
    def from_xml(cls, root: et.Element) -> "Question":
        res = {}
        res["true_ans"]  = None
        res["false_ans"] = None
        res["correct_answer"] = False
        for answer in root.findall("answer"):
            tmp = Answer.from_xml(answer)
            if tmp.text.lower() == "true":
                res["true_ans"] = tmp
                res["correct_answer"] = True if res["true_ans"].fraction == 100 else False
            elif tmp.text.lower() == "false":
                res["false_ans"] = tmp
        question = super().from_xml(root, **res)
        return question

    def to_xml(self) -> et.Element:
        question = super().to_xml()
        question.append(self.__answer_true.to_xml())
        question.append(self.__answer_false.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class QFreeDrawing(Question):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

# ----------------------------------------------------------------------------------------

class QLineDrawing(Question):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

# ----------------------------------------------------------------------------------------

class QCrossWord(Question):

    def __init__(self, x_grid: int=0, y_grid: int=0, words: List[CrossWord]=None, 
                *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.x_grid = x_grid
        self.y_grid = y_grid
        self.words = words      # The class only checks grid

    def add_word(self, word: str, x: int, y: int, direction: Direction, clue: str):
        if x < 0 or x > self.x_grid+len(word) or y < 0 or y > self.y_grid+len(word):
            raise ValueError("New word does not fit in the current grid")
        self.words.append(CrossWord(word, x, y, direction, clue))

    def get_solution(self) -> bool:
        """
        Iterate over the object list to verify if it is valid.
        """
        solution: Dict[int, Dict[int, str]] = {}
        for word in self.words:
            if word.x not in solution: solution[word.x] = {}
            if word.y not in solution: solution[word.x][word.y] = {}
            pass

    @classmethod
    def from_json(cls, data) -> "QCrossWord":
        for i in range(len(data["words"])):
            data["words"][i] = CrossWord.from_json(data["words"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element) -> "QCrossWord":
        raise NotImplementedError("This Class is not avaiable in a Moodle XML")

# ----------------------------------------------------------------------------------------

QTYPES = ['QCalculated', 'QCalculatedMultichoice', 'QCalculatedSimple', 'QCloze', 
        'QCrossWord', 'QDescription', 'QDragAndDropImage', 'QDragAndDropMarker',
        'QDragAndDropText', 'QEssay', 'QFreeDrawing', 'QLineDrawing', 'QMatching',
        'QMissingWord', 'QMultichoice', 'QNumerical', 'QRandomMatching', 
        'QShortAnswer', 'QTrueFalse']