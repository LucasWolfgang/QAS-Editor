""""
Question and Answer Sheet Editor <https://github.com/LucasWolfgang/QAS-Editor>
Copyright (C) 2022  Lucas Wolfgang

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from __future__ import annotations
import re
import logging
from xml.etree import ElementTree as et
from typing import TYPE_CHECKING
from .wrappers import B64File, CombinedFeedback, Dataset, FText, MultipleTries,\
                    SelectOption, Subquestion, Unit, Tags, UnitHandling
from .utils import Serializable
from .enums import Format, ResponseFormat, Status, Distribution, Numbering
from .answer import Answer, ClozeItem, NumericalAnswer, DragText, \
                    CrossWord, CalculatedAnswer, DropZone, DragItem
# import markdown
# import latex2mathml
if TYPE_CHECKING:
    from typing import List, Dict
    from .enums import Direction
LOG = logging.getLogger(__name__)
QNAME: Dict[str, Question] = {}
QTYPE: Dict[str, Question] = {}

class Question(Serializable):
    """
    This is an abstract class Question used as a parent for specific
    types of Questions.
    """
    _type = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        QNAME[cls.__name__] = cls
        QTYPE[cls._type] = cls

    def __init__(self, name: str, question_text: FText = None,
                 default_grade: float = 1.0, general_feedback: FText = None,
                 id_number: int = None, shuffle: bool = False,
                 tags: Tags = None, solution: FText = None) -> None:
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
        self.question_text = question_text if question_text is not None else \
                             FText("questiontext", "", Format.AUTO, None)
        self.default_grade = default_grade
        self.general_feedback = general_feedback if general_feedback is not None else \
                                FText("generalfeedback", "", Format.AUTO, None)
        self.id_number = id_number
        self.shuffle = shuffle
        self.solution = solution
        self.tags = tags if tags is not None else Tags()
        self.__parent = None

    @property
    def parent(self):
        """_summary_

        Returns:
            Quiz: _description_
        """
        return self.__parent

    @parent.setter
    def parent(self, value):
        if (self.__parent is None and value is not None and\
                self not in value.questions) or (self.__parent is not None and\
                value is None and self in self.__parent.questions):
            raise ValueError("This attribute can't be assigned directly. Use "+
                             "parent's add/rem_question functions instead.")
        self.__parent = value

    @classmethod
    def from_json(cls, data) -> "Question":
        data["question_text"] = FText.from_json(data["question_text"])
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "Question":
        tags["name"] = (str, "name")
        tags["questiontext"] = (FText.from_xml, "question_text")
        tags["generalfeedback"] = (FText.from_xml, "general_feedback")
        tags["defaultgrade"] = (float, "default_grade")
        tags["idnumber"] = (int, "id_number")
        tags["shuffleanswers"] = (bool, "shuffle")
        tags["tags"] = (Tags.from_xml, "tags")
        tags["solution"] = (FText.from_xml, "solution")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        """
        This method converts current object to Moodle XML.
        """
        question = et.SubElement(root, "question", {"type": self._type})
        name = et.SubElement(question, "name")
        et.SubElement(name, "text").text = self.name
        self.question_text.to_xml(question, strict)
        if self.general_feedback:
            self.general_feedback.to_xml(question, strict)
        et.SubElement(question, "defaultgrade").text = str(self.default_grade)
        et.SubElement(question, "hidden").text = "0"
        if self.id_number is not None:
            et.SubElement(question, "idnumber").text = str(self.id_number)
        if self.shuffle:
            et.SubElement(question, "shuffleanswers").text = "true"
        if self.tags:
            question.append(self.tags.to_xml(question, strict))
        if not strict and self.solution:
            self.solution.to_xml(question, strict)
        return question

# ------------------------------------------------------------------------------

class QCalculated(Question):
    """Represents a "Calculated"q question, in which a numberical result should
    be provided.
    """
    _type = "calculated"

    def __init__(self, synchronize: int = 0, single: bool = False,
                 unit_handling: UnitHandling = None, units: List[Unit] = None,
                 datasets: List[Dataset] = None,
                 answers: List[CalculatedAnswer] = None,
                 multiple_tries: MultipleTries = None, **kwargs):
        """[summary]

        Args:
            synchronize (int): [description]
            single (bool, optional): [description]. Defaults to False.
            unit_handling (UnitHandling, optional): [description]. Defaults to None.
            units (List[Unit], optional): [description]. Defaults to None.
            datasets (List[Dataset], optional): [description]. Defaults to None.
            answers (List[CalculatedAnswer], optional): [description]. Defaults to None.
        """
        super().__init__(**kwargs)
        self.synchronize = synchronize
        self.single = single
        self.unit_handling = unit_handling
        self.multiple_tries = multiple_tries
        self.units = units if units is not None else []
        self.datasets = datasets if datasets is not None else []
        self.answers = answers if answers is not None else []

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
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "QCalculated":
        tags["synchronize"] = (bool, "synchronize")
        tags["single"] = (bool, "single")
        UnitHandling._add_xml(tags, "unit_handling")
        MultipleTries._add_xml(tags, "multiple_tries")
        tags["units"] = (Unit.from_xml, "units", True)
        tags["dataset_definitions"] = (Dataset.from_xml_list, "datasets")
        tags["answer"] = (CalculatedAnswer.from_xml, "answers", True)
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        question = super().to_xml(root, strict)
        if self.synchronize:
            et.SubElement(question, "synchronize")
        if self.single:
            et.SubElement(question, "single")
        for answer in self.answers:
            answer.to_xml(question, strict)
        self.unit_handling.to_xml(question, strict)
        self.multiple_tries.to_xml(question, strict)
        if self.units:
            units = et.SubElement(question, "units")
            for unit in self.units:
                unit.to_xml(units, strict)
        if self.datasets:
            dataset_definitions = et.SubElement(question, "dataset_definitions")
            for dataset in self.datasets:
                dataset.to_xml(dataset_definitions, strict)
        return question

# ------------------------------------------------------------------------------

class QCalculatedSimple(QCalculated):
    """Same as QCalculated. Implemented only for compatibility with the moodle
    XML format.
    """
    _type = "calculatedsimple"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

# ------------------------------------------------------------------------------

class QCalculatedMultichoice(Question):
    """Represents a "Calculated" question with multiple choices, behaving like
    a multichoice question where the answers are calculated using equations and
    datasets.
    """
    _type = "calculatedmulti"

    def __init__(self, synchronize: int = 0, single: bool = False,
                 numbering: Numbering = Numbering.ALF_LR,
                 combined_feedback: CombinedFeedback = None,
                 multiple_tries: MultipleTries = None,
                 datasets: List[Dataset] = None,
                 answers: List[CalculatedAnswer] = None, **kwargs):
        super().__init__(**kwargs)
        self.synchronize = synchronize
        self.single = single
        self.numbering = numbering
        self.combined_feedback = combined_feedback
        self.multiple_tries = multiple_tries
        self.datasets = datasets if datasets is not None else []
        self.answers = answers if answers is not None else []

    def add_dataset(self, status: Status, name: str, dist: Distribution, minim: float,
                    maxim: float, dec: int) -> None:
        """_summary_

        Args:
            status (Status): _description_
            name (str): _description_
            dist (Distribution): _description_
            minim (float): _description_
            maxim (float): _description_
            dec (int): _description_
        """
        self.datasets.append(Dataset(status, name, "calculated", dist, minim, maxim, dec))

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
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "Question":
        tags["synchronize"] = (bool, "synchronize")
        tags["single"] = (bool, "single")
        tags["answernumbering"] = (Numbering, "numbering")
        CombinedFeedback._add_xml(tags, "combined_feedback")
        MultipleTries._add_xml(tags, "multiple_tries")
        tags["dataset_definitions"] = (Dataset.from_xml_list, "datasets")
        tags["answer"] = (CalculatedAnswer.from_xml, "answers", True)
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        question = super().to_xml(root, strict)
        if self.synchronize:
            et.SubElement(question, "synchronize")
        if self.single:
            et.SubElement(question, "single")
        et.SubElement(question, "answernumbering").text = self.numbering.value
        self.combined_feedback.to_xml(question, strict)
        self.multiple_tries.to_xml(question, strict)
        for answer in self.answers:
            answer.to_xml(question, strict)
        dataset_definitions = et.SubElement(question, "dataset_definitions")
        for dataset in self.datasets:
            dataset.to_xml(dataset_definitions, strict)
        return question

# ------------------------------------------------------------------------------

class QCloze(Question):
    """This is a very simples class that hold cloze data. All data is compressed
    inside the question text, so no further implementation is necessary.
    """
    _type = "cloze"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.answers = []
        self._update_text()

    @classmethod
    def from_cloze(cls, buffer) -> "QCloze":
        """_summary_

        Args:
            buffer (_type_): _description_

        Returns:
            QCloze: _description_
        """
        data = buffer.read()
        name, text = data.split("\n", 1)
        ftext = FText("questiontext", text, Format.HTML, None)
        return cls(name=name, question_text=ftext)

    @classmethod
    def from_json(cls, data: dict) -> "QCloze":
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "QCloze":
        return super().from_xml(root, tags, attrs)

    def _update_text(self):
        pattern = re.compile(r"(?!\\)\{(\d+)?(?:\:(.*?)\:)(.*?(?!\\)\})")
        for match in pattern.finditer(self.question_text.text):
            item = ClozeItem.from_cloze(match)
            self.answers.append(item)

# ------------------------------------------------------------------------------

class QDescription(Question):
    """Represents a simple description. This is not a question. It has the same
    extructure as Question class and was add for compatiblity with the moodle
    XML format.
    """
    _type = "description"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    @classmethod
    def from_gift(cls, header: list) -> "QDescription":
        """_summary_

        Args:
            header (list): _description_

        Returns:
            QDescription: _description_
        """
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        return cls(name=header[1],
                   question_text=FText("questiontext", header[3], formatting, None))

# ------------------------------------------------------------------------------

class QDragAndDropText(Question):
    """
    This class represents a drag and drop text onto image question.
    It inherits from abstract class Question.
    """
    _type = "ddwtos"

    def __init__(self, combined_feedback: CombinedFeedback = None,
                 multiple_tries: MultipleTries = None,
                 answers: List[DragText] = None, **kwargs):
        """
        Currently not implemented.
        """
        super().__init__(**kwargs)
        self.combined_feedback = combined_feedback
        self.multiple_tries = multiple_tries
        self.answers = answers if answers is not None else []

    @classmethod
    def from_json(cls, data) -> "QDragAndDropText":
        data["combined_feedback"] = CombinedFeedback.from_json(data["combined_feedback"])
        data["multiple_tries"] = MultipleTries.from_json(data["multiple_tries"])
        for i in range(len(data["answers"])):
            data["answers"][i] = DragText.from_json(data["answers"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "QDragAndDropText":
        CombinedFeedback._add_xml(tags, "combined_feedback")
        MultipleTries._add_xml(tags, "multiple_tries")
        tags["dragbox"] = (DragText.from_xml, "answers", True)
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        question = super().to_xml(root, strict)
        self.multiple_tries.to_xml(question, strict)
        self.combined_feedback.to_xml(question, strict)
        for choice in self.answers:
            choice.to_xml(question, strict)
        return question

# ----------------------------------------------------------------------------------------

class QDragAndDropImage(Question):
    """This class represents a drag and drop onto image question.
    It inherits from abstract class Question.
    """
    _type = "ddimageortext"

    def __init__(self, background: B64File = None,
                 combined_feedback: CombinedFeedback = None,
                 dragitems: List[DragItem] = None,
                 dropzones: List[DropZone] = None, **kwargs) -> None:
        """Creates an drag and drop onto image type of question.

        Args:
            background (str): Filepath to the background image.
        """
        super().__init__(**kwargs)
        self.background = background
        self.combined_feedback = combined_feedback
        self._dragitems: List[DragItem] = dragitems if dragitems is not None else []
        self._dropzones: List[DropZone] = dropzones if dropzones is not None else []

    def add_dragimage(self, text: str, group: int, file: str, unlimited: bool = False) -> None:
        """Adds new DragItem with assigned DropZones.

        Args:
            file (str): path to image to be used as a drag image;
            text (str, optional): text of the drag text.
            group (int, optional): group.
            unlimited (bool, optional): if item is allowed to be used again.
                Defaults to False.
        """
        dragimage = DragItem(len(self._dragitems) + 1, text, unlimited, group,
                             image=file)
        self._dragitems.append(dragimage)

    def add_dragtext(self, text: str, group: str, unlimited: bool = False) -> None:
        """Adds new DragText with assigned DropZones.

        Args:
            text (str): text of the drag text.
            group (str): group.
            unlimited (bool, optional): if item is allowed to be used again.
                Defaults to False.
        """
        dragitem = DragItem(len(self._dragitems) + 1, text, unlimited, group)
        self._dragitems.append(dragitem)

    def add_dropzone(self, coord_x: int, coord_y: int, text: str, choice: int) -> None:
        """[summary]

        Args:
            x (int): [description]
            y (int): [description]
            text (str): [description]
            choice (int): [description]
        """
        self._dropzones.append(DropZone(coord_x, coord_y, text, choice,
                                        len(self._dropzones) + 1))

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
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "QDragAndDropImage":
        CombinedFeedback._add_xml(tags, "combined_feedback")
        tags["file"] = (B64File.from_xml, "background")
        tags["drag"] = (DragItem.from_xml, "dragitems", True)
        tags["drop"] = (DropZone.from_xml, "dropzones", True)
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool):
        question = super().to_xml(root, strict)
        self.combined_feedback.to_xml(question, strict)
        if self.background:
            self.background.to_xml(question, strict)
        for dragitem in self._dragitems:
            dragitem.to_xml(question, strict)
        for dropzone in self._dropzones:
            dropzone.to_xml(question, strict)
        return question

# ------------------------------------------------------------------------------

class QDragAndDropMarker(Question):
    """Represents a Drag and Drop question where the items are markers.
    """
    _type = "ddmarker"

    def __init__(self, background: B64File = None,
                 combined_feedback: CombinedFeedback = None,
                 multiple_tries: MultipleTries = None,
                 dragitems: List[DragItem] = None,
                 dropzones: List[DropZone] = None,
                 highlight_empty: bool = False, **kwargs):
        """Creates an drag and drop onto image type of question.

        Args:
            background (str): Filepath to the background image.
        """
        super().__init__(**kwargs)
        self.background = background
        self.combined_feedback = combined_feedback
        self.multiple_tries = multiple_tries
        self.highlight_empty = highlight_empty
        self._dragitems = dragitems if dragitems is not None else []
        self._dropzones = dropzones if dropzones is not None else []

    def add_dragmarker(self, text: str, no_of_drags: str, unlimited: bool = False):
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
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "QDragAndDropMarker":
        CombinedFeedback._add_xml(tags, "combined_feedback")
        MultipleTries._add_xml(tags, "multiple_tries")
        tags["file"] = (B64File.from_xml, "background")
        tags["showmisplaced"] = (bool, "highlight_empty")
        tags["drag"] = (DragItem.from_xml, "dragitems", True)
        tags["drop"] = (DropZone.from_xml, "dropzones", True)
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool):
        question = super().to_xml(root, strict)
        if self.highlight_empty:
            et.SubElement(question, "showmisplaced")
        self.multiple_tries.to_xml(question, strict)
        self.combined_feedback.to_xml(question, strict)
        for dragitem in self._dragitems:
            dragitem.to_xml(question, strict)
        for dropzone in self._dropzones:
            dropzone.to_xml(question, strict)
        if self.background:
            self.background.to_xml(question, strict)
        return question

# ------------------------------------------------------------------------------

class QEssay(Question):
    """Represents an essay question, in which the answer is written as an essay
    and need to be submitted for review (no automatic correct/answer feedback
    provided).
    """
    _type = "essay"

    def __init__(self, response_format: ResponseFormat = ResponseFormat.HTML,
                 response_required: bool = True, lines: int = 10, attachments: int = 1,
                 attachments_required: bool = False, maxbytes: int = None,
                 filetypes_list: str = None, grader_info: FText = None,
                 response_template: FText = None, **kwargs) -> None:
        super().__init__(**kwargs)
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
    def from_gift(cls, header: list) -> "QEssay":
        """_summary_

        Args:
            header (list): _description_

        Returns:
            QEssay: _description_
        """
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        return cls(name=header[1],
                   question_text=FText("questiontext", header[3], formatting, None))

    @classmethod
    def from_json(cls, data) -> "QEssay":
        data["response_format"] = ResponseFormat(data["response_format"])
        data["grader_info"] = FText.from_json(data["grader_info"])
        data["response_template"] = FText.from_json(data["response_template"])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "QEssay":
        tags["responseformat"] = (ResponseFormat, "response_format")
        tags["responserequired"] = (bool, "response_required")
        tags["responsefieldlines"] = (int, "lines")
        tags["attachments"] = (int, "attachments")
        tags["attachmentsrequired"] = (bool, "attachments_required")
        tags["maxbytes"] = (int, "maxbytes")
        tags["filetypeslist"] = (str, "filetypes_list")
        tags["graderinfo"] = (FText.from_xml, "grader_info")
        tags["responsetemplate"] = (FText.from_xml, "response_template")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        question = super().to_xml(root, strict)
        et.SubElement(question, "responseformat").text = self.response_format.value
        if self.response_required:
            et.SubElement(question, "responserequired")
        et.SubElement(question, "responsefieldlines").text = str(self.responsefield_lines)
        et.SubElement(question, "attachments").text = str(self.attachments)
        if self.attachments_required:
            et.SubElement(question, "attachmentsrequired")
        if self.maxbytes:
            et.SubElement(question, "maxbytes").text = str(self.maxbytes)
        if self.filetypes_list:
            et.SubElement(question, "filetypeslist").text = self.filetypes_list
        if self.grader_info:
            self.grader_info.to_xml(question, strict)
        if self.response_template:
            self.response_template.to_xml(question, strict)
        return question

# ------------------------------------------------------------------------------

class QMatching(Question):
    """Represents a Matching question, in which the goal is to find matchs.
    """
    _type = "matching"

    def __init__(self, combined_feedback: CombinedFeedback = None,
                 subquestions: List[Subquestion] = None, **kwargs):
        super().__init__(**kwargs)
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
        """_summary_

        Args:
            header (list): _description_
            answer (list): _description_

        Returns:
            QMatching: _description_
        """
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(name=header[1],
                  question_text=FText("questiontext", header[3], formatting, None))
        for ans in answer:
            if ans[0] == "=":
                rgx = re.match(r"(.*?)(?<!\\)->(.*)", ans[2])
                qst.subquestions.append(Subquestion(formatting, rgx[1].strip(),
                                                    rgx[2].strip()))
            elif ans[0] == "####":
                qst.general_feedback = FText("generalfeedback", ans[2],
                                             formatting, None)
        return qst

    @classmethod
    def from_json(cls, data) -> "QMatching":
        data["combined_feedback"] = CombinedFeedback.from_json(data["combined_feedback"])
        for i in range(len(data["subquestions"])):
            data["subquestions"][i] = Subquestion.from_json(data["subquestions"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "QMatching":
        CombinedFeedback._add_xml(tags, "combined_feedback")
        tags["subquestion"] = (Subquestion.from_xml, "subquestions", True)
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        question = super().to_xml(root, strict)
        if self.combined_feedback:
            self.combined_feedback.to_xml(question, strict)
        for sub in self.subquestions:
            sub.to_xml(question, strict)
        return question

# ------------------------------------------------------------------------------

class QRandomMatching(Question):
    """Represents a Random match question.
    """
    _type = "randomsamatch"

    def __init__(self, choose: int = 0, subcats: bool = False,
                 combined_feedback: CombinedFeedback = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.combined_feedback = combined_feedback
        self.choose = choose
        self.subcats = subcats

    @classmethod
    def from_json(cls, data) -> "QRandomMatching":
        data["combined_feedback"] = CombinedFeedback.from_json(data["combined_feedback"])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "QRandomMatching":
        CombinedFeedback._add_xml(tags, "combined_feedback")
        tags["choose"] = (str, "choose")
        tags["subcats"] = (str, "subcats")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        question = super().to_xml(root, strict)
        self.combined_feedback.to_xml(question, strict)
        et.SubElement(question, "choose").text = self.choose
        et.SubElement(question, "subcats").text = self.subcats
        return question

# ------------------------------------------------------------------------------

class QMissingWord(Question):
    """ Represents a "Missing Word" question.
    """
    _type = "gapselect"

    def __init__(self, combined_feedback: CombinedFeedback = None,
                 options: List[SelectOption] = None, **kwargs):
        super().__init__(**kwargs)
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
        """_summary_

        Args:
            header (list): _description_
            answer (list): _description_

        Returns:
            QMissingWord: _description_
        """
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(name=header[1], question_text=FText("questiontext", header[3],
                                                      formatting, None))
        correct = None
        for i in answer:
            if i[0] == "=":
                correct = SelectOption(i[2], 1)
            else:
                qst.options.append(SelectOption(i[2], 1))
        qst.options.insert(0, correct)
        return qst

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "QMissingWord":
        CombinedFeedback._add_xml(tags, "combined_feedback")
        tags["selectoption"] = (SelectOption.from_xml, "options", True)
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        question = super().to_xml(root, strict)
        if self.combined_feedback:
            self.combined_feedback.to_xml(question, strict)
        for opt in self.options:
            opt.to_xml(question, strict)
        return question

# ------------------------------------------------------------------------------

class QMultichoice(Question):
    """This class represents 'Multiple choice' question.
    """
    _type = "multichoice"

    def __init__(self, single: bool = True, show_instruction: bool = False,
                 answer_numbering: Numbering = Numbering.ALF_LR,
                 multiple_tries: MultipleTries = None,
                 combined_feedback: CombinedFeedback = None,
                 answers: List[Answer] = None, **kwargs):
        super().__init__(**kwargs)
        self.single = single
        self.show_instruction = show_instruction
        self.combined_feedback = combined_feedback
        self.multiple_tries = multiple_tries
        if isinstance(answer_numbering, Numbering):
            self.answer_numbering = answer_numbering
        elif isinstance(answer_numbering, str):
            self.answer_numbering = Numbering(answer_numbering)
        else:
            raise TypeError("answer_numbering should be of type Numbering "+
                            f"or str, not {type(answer_numbering)}")
        self.answers = answers if answers is not None else []

    def add_answer(self, fraction: float, text: str, feedback: str = None) -> None:
        """
        Adds an answer to this question.

        Args:
            fraction (float): Percentage of the grade
            text (str): text of the anwser
            feedback (str, optional): feedback shown when this answer is submitted.
                Defaults to None.
        """
        self.answers.append(Answer(fraction, text, feedback, Format.AUTO))

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
        """_summary_

        Args:
            buffer (LineBuffer): _description_
            name (str): _description_

        Returns:
            QMultichoice: _description_
        """
        header = buffer.read(True)
        answers = []
        while buffer.read() and "ANSWER:" not in buffer.read()[:7]:
            ans = re.match(r"[A-Z]+\) (.+)", buffer.read(True))
            if ans:
                answers.append(Answer(0.0, ans[1], None, Format.PLAIN))
        try:
            answers[ord(buffer.read(True)[8].upper())-65].fraction = 100.0
        except IndexError:
            LOG.exception(f"Failed to set correct answer in question {name}.")
        return cls(name=name, answers=answers,
                   question_text=FText("questiontext", header, Format.PLAIN, None))

    @classmethod
    def from_gift(cls, header: list, answer: list) -> "QMultichoice":
        """_summary_

        Args:
            header (list): _description_
            answer (list): _description_

        Returns:
            QMultichoice: _description_
        """
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(name=header[1], question_text=FText("questiontext", header[3],
                                                      formatting, None))
        prev_answer = None
        for ans in answer:
            txt = ans[2]
            if ans[0] == "~": # Wrong or partially correct answer
                fraction = 0 if not ans[1] else float(ans[1][1:-1])
                prev_answer = Answer(fraction, txt, None, formatting)
                qst.answers.append(prev_answer)
            elif ans[0] == "=": # Correct answer
                prev_answer = Answer(100, txt, None, formatting)
                qst.answers.append(prev_answer)
            elif ans[0] == "#": # Answer feedback
                prev_answer.feedback = FText("feedback", ans[2],
                                             formatting, None)
        return qst

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "QMultichoice":
        tags["single"] = (bool, "single")
        tags["showstandardinstruction"] = (bool, "show_instruction")
        tags["answernumbering"] = (Numbering, "answer_numbering")
        tags["answer"] = (Answer.from_xml, "answers", True)
        CombinedFeedback._add_xml(tags, "combined_feedback")
        MultipleTries._add_xml(tags, "multiple_tries")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        question = super().to_xml(root, strict)
        self.multiple_tries.to_xml(question, strict)
        if self.combined_feedback:
            self.combined_feedback.to_xml(question, strict)
        et.SubElement(question, "answernumbering").text = self.answer_numbering.value
        if self.single:
            et.SubElement(question, "single")
        for answer in self.answers:
            answer.to_xml(question, strict)
        return question

    @staticmethod
    def from_markdown(lines: list, answer_mkr: str, question_mkr: str,
                      name: str = "mkquestion") -> "QMultichoice":
        """[summary]

        Returns:
            [type]: [description]
        """
        data = ""
        match = re.match(answer_mkr, lines[-1])
        while lines and match is None:
            data += lines.pop().strip()
            match = re.match(answer_mkr, lines[-1])
        question = QMultichoice(name=name,
                                question_text=FText("questiontext", data, Format.MD, None))
        regex_exp = f"({question_mkr})|({answer_mkr})"
        while lines:
            match = re.match(regex_exp, lines.pop())
            if match and match[3]:
                ans = Answer(100.0 if match[4] is not None else 0.0, match[5],
                             None, Format.HTML)
                question.answers.append(ans)
            else:
                break
        return question

# ------------------------------------------------------------------------------

class QNumerical(Question):
    """
    This class represents 'Numerical Question' moodle question type.
    Units are currently not implemented, only numerical answer, which
    are specified as text and absolute tolerance value are implemented
    """
    _type = "numerical"

    def __init__(self, unit_handling: UnitHandling = None,
                 units: List[Unit] = None,
                 answers: List[NumericalAnswer] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.unit_handling = unit_handling
        self.units = units if units is not None else []
        self.answers = answers if answers is not None else []

    def add_answer(self, tol: float, fraction: float, text: str,
                   feedback: str = None) -> None:
        """_summary_

        Args:
            tol (float): _description_
            fraction (float): _description_
            text (str): _description_
            feedback (str, optional): _description_. Defaults to None.
        """
        self.answers.append(NumericalAnswer(tol, fraction=fraction, text=text,
                                            formatting=feedback))

    @classmethod
    def from_json(cls, data) -> "QNumerical":
        data["unit_handling"] = UnitHandling.from_json(data["unit_handling"])
        for i in range(len(data["units"])):
            data["units"][i] = Unit.from_json(data["units"][i])
        for i in range(len(data["answers"])):
            data["answers"][i] = NumericalAnswer.from_json(data["answers"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "QNumerical":
        tags["unit_handling"] = (UnitHandling.from_xml, "unit_handling")
        tags["answer"] = (NumericalAnswer.from_xml, "answers", True)
        tags["units"] = (Unit.from_xml, "units", True)
        return super().from_xml(root, tags, attrs)

    @classmethod
    def from_gift(cls, header: list, answer: list) -> "QNumerical":
        """_summary_

        Args:
            header (list): _description_
            answer (list): _description_

        Returns:
            QNumerical: _description_
        """
        def _extract(data: str) -> tuple:
            rgx = re.match(r"(.+?)(:|(?:\.\.))(.+)", data)
            if rgx[2] == "..": # Converts min/max to value +- tol
                txt = (float(rgx[1]) + float(rgx[3]))/2
                tol = txt - float(rgx[1])
                txt = str(txt)
            else:
                txt = rgx[1]
                tol = float(rgx[3])
            return txt, tol
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(name=header[1], question_text=FText("questiontext", header[3],
                                                      formatting, None))
        if len(answer) == 1:
            txt, tol = _extract(answer[0][2])
            qst.answers.append(NumericalAnswer(tol, fraction=100, text=txt,
                                               formatting=Format.AUTO))
        elif len(answer) > 1:
            for ans in answer[1:]:
                if ans[0] == "=":   # Happens first, thus nans is always defined
                    txt, tol = _extract(ans[2])
                    fraction = float(ans[1][1:-1]) if ans[0] == "=" else 0
                    nans = NumericalAnswer(tol, fraction=fraction, text=txt,
                                           formatting=Format.AUTO)
                    qst.answers.append(nans)
                elif ans[0] == "~":
                    nans = NumericalAnswer(0, fraction=0, text="",
                                           formatting=Format.AUTO)
                elif ans[0] == "#":
                    nans.feedback = FText("feedback", ans[2], formatting, None)
        return qst

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        question = super().to_xml(root, strict)
        for answer in self.answers:
            answer.to_xml(question, strict)
        if self.unit_handling:
            self.unit_handling.to_xml(question, strict)
        if len(self.units) > 0:
            units = et.SubElement(question, "units")
            for unit in self.units:
                unit.to_xml(units, strict)
        return question

# ------------------------------------------------------------------------------

class QShortAnswer(Question):
    """
    This class represents 'Short answer' question.
    """
    _type = "shortanswer"

    def __init__(self, use_case: bool = False, answers: List[Answer] = None,
                 **kwargs) -> None:
        super().__init__(**kwargs)
        self.use_case = use_case
        self.answers = answers if answers is not None else []

    def add_answer(self, fraction: float, text: str, feedback: str = None):
        """Adds an answer to this question.

        Args:
            fraction (float): Percentage of the grade
            text (str): text of the anwser
            feedback (str, optional): feedback shown when this answer is submitted.
                Defaults to None.
        """
        self.answers.append(Answer(fraction, text, feedback, Format.AUTO))

    @classmethod
    def from_json(cls, data) -> "QShortAnswer":
        for i in range(len(data["answers"])):
            data["answers"][i] = Answer.from_json(data["answers"][i])
        return super().from_json(data)

    @classmethod
    def from_gift(cls, header: list, answer: list) -> "QShortAnswer":
        """_summary_

        Args:
            header (list): _description_
            answer (list): _description_

        Returns:
            QShortAnswer: _description_
        """
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(False, name=header[1],
                  question_text=FText("questiontext", header[3], formatting, None))
        for ans in answer:
            fraction = 100 if not ans[1] else float(ans[1][1:-1])
            qst.answers.append(Answer(fraction, ans[2], formatting, Format.AUTO))
        return qst

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "QShortAnswer":
        tags["usecase"] = (str, "use_case")
        tags["answer"] = (Answer.from_xml, "answers", True)
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        question = super().to_xml(root, strict)
        et.SubElement(question, "usecase").text = self.use_case
        for answer in self.answers:
            answer.to_xml(question, strict)
        return question

# ------------------------------------------------------------------------------

class QTrueFalse(Question):
    """
    This class represents true/false question.
    """
    _type = "truefalse"

    def __init__(self, answers: List[Answer], **kwargs) -> None:
        super().__init__(**kwargs)
        self.__true = None
        self.__false = None
        self.__correct = None
        if len(answers) != 2:
            raise ValueError()
        for answer in answers:
            if answer.text.lower() == "true":
                self.__true = answer
                self.__correct = answer.fraction == 100
            elif answer.text.lower() == "false":
                self.__false = answer

    def set_feedbacks(self, correct: FText, incorrect: FText):
        """_summary_

        Args:
            correct (FText): _description_
            incorrect (FText): _description_
        """
        self.__true.feedback = correct if self.correct_answer else incorrect
        self.__false.feedback = correct if not self.correct_answer else incorrect

    @property
    def correct_answer(self) -> bool:
        """_summary_

        Returns:
            bool: _description_
        """
        return self.__correct

    @correct_answer.setter
    def correct_answer(self, value: bool) -> None:
        """_summary_

        Args:
            value (bool): _description_
        """
        self.__true.fraction = 100 if value else 0
        self.__false.fraction = 100 if not value else 0
        self.__correct = value

    @classmethod
    def from_json(cls, data) -> "QTrueFalse":
        data["answers"] = [Answer.from_json(data["_QTrueFalse__true"]),
                           Answer.from_json(data["_QTrueFalse__false"])]
        return super().from_json(data)

    @classmethod
    def from_gift(cls, header: list, answer: list) -> "QTrueFalse":
        """_summary_

        Args:
            header (list): _description_
            answer (list): _description_

        Returns:
            QTrueFalse: _description_
        """
        correct = answer.pop(0)[0].lower() in ["true", "t"]
        true_ans = Answer(100 if correct else 0, "true", None, Format.AUTO)
        false_ans = Answer(0 if correct else 100, "false", None, Format.AUTO)
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(answers=[true_ans, false_ans], name=header[1],
                  question_text=FText("questiontext", header[3], formatting, None))
        for ans in answer:
            if ans[0] == "####":
                qst.general_feedback = FText("generalfeedback", ans[2],
                                             Format(header[2][1:-1]), None)
            elif false_ans.feedback is None:
                false_ans.feedback = FText("feedback", ans[2],
                                           Format(header[2][1:-1]), None)
            else:
                true_ans = FText("feedback", ans[2], Format(header[2][1:-1]), None)
        return qst

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "Question":
        tags["answer"] = (Answer.from_xml, "answers", True)
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        question = super().to_xml(root, strict)
        self.__true.to_xml(question, strict)
        self.__false.to_xml(question, strict)
        return question

# ------------------------------------------------------------------------------

class QFreeDrawing(Question):
    """Represents a question where the use is free to make any drawing. The
    result is submited for review (there is no automatic correct/wrong feedback).
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

# ------------------------------------------------------------------------------

class QLineDrawing(Question):
    """Represents a question where the user should draw line either to complete
    an image or to draw a new one. The result is submited for review (there is
    no automatic correct/wrong feedback).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

# ------------------------------------------------------------------------------

class QCrossWord(Question):
    """Represents a Crossword question.
    """

    def __init__(self, x_grid: int = 0, y_grid: int = 0,
                 words: List[CrossWord] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.x_grid = x_grid
        self.y_grid = y_grid
        self.words = words if words else []      # The class only checks grid

    def add_word(self, word: str, coord_x: int, coord_y: int,
                 direction: Direction, clue: str) -> None:
        """_summary_

        Args:
            word (str): _description_
            coord_x (int): _description_
            coord_y (int): _description_
            direction (Direction): _description_
            clue (str): _description_

        Raises:
            ValueError: _description_
        """
        if coord_x < 0 or coord_x > self.x_grid+len(word) or \
                coord_y < 0 or coord_y > self.y_grid+len(word):
            raise ValueError("New word does not fit in the current grid")
        self.words.append(CrossWord(word, coord_x, coord_y, direction, clue))

    def get_solution(self) -> bool:
        """
        Iterate over the object list to verify if it is valid.
        """
        solution: Dict[int, Dict[int, str]] = {}
        for word in self.words:
            if word.coord_x not in solution:
                solution[word.x] = {}
            if word.coord_y not in solution:
                solution[word.coord_x][word.coord_y] = {}

    @classmethod
    def from_json(cls, data) -> "QCrossWord":
        for i in range(len(data["words"])):
            data["words"][i] = CrossWord.from_json(data["words"][i])
        return super().from_json(data)

# ------------------------------------------------------------------------------
