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
from .wrappers import B64File, Dataset, FText, Hint, Tags, SelectOption,\
                      Subquestion, Unit
from .utils import Serializable
from .enums import Format, Grading, ResponseFormat, ShowUnits, Status,\
                   Distribution, Numbering, Synchronise
from .answer import Answer, ClozeItem, NumericalAnswer, DragText, \
                    CrossWord, CalculatedAnswer, DropZone, DragItem
# import markdown
# import latex2mathml
if TYPE_CHECKING:
    from typing import List, Dict
    from .enums import Direction
    from .quiz import Category
LOG = logging.getLogger(__name__)


QNAME: Dict[str, _Question] = {}
QTYPE: Dict[str, _Question] = {}
MARKER_STR = " &#9635; "
MARKER_INT = 9635

class _Question(Serializable):
    """
    This is an abstract class Question used as a parent for specific
    types of Questions.
    """
    MOODLE = None
    QNAME = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.QNAME is not None:
            QNAME[cls.QNAME] = cls
        if cls.MOODLE is not None:
            QTYPE[cls.MOODLE] = cls

    def __init__(self, name: str, default_grade=1.0, question: FText = None,
                 dbid: int = None, feedback: FText = None, tags: Tags = None):
        """
        [summary]

        Args:
            name (str): name of the question
            question (FText): text of the question
            default_grade (float): the default mark
            general_feedback (str, optional): general feedback.
            dbid (int, optional): id number.
        """
        self.name = name
        self.question = FText("questiontext") if question is None else question
        self.default_grade = default_grade
        self.feedback = FText("generalfeedback") if feedback \
                is None else feedback
        self.dbid = dbid
        self.tags = Tags() if tags is None else tags
        self.__parent = None

    def __str__(self) -> str:
        return f"{self.QNAME}: '{self.name}' @{hex(id(self))}"

    @property
    def parent(self) -> Category:
        """_summary_

        Returns:
            Quiz: _description_
        """
        return self.__parent

    @parent.setter
    def parent(self, value):
        if (self.__parent is not None and self in self.__parent.questions) or \
                (value is not None and self not in value.questions):
            raise ValueError("This attribute can't be assigned directly. Use "
                             "parent's add/pop_question functions instead.")
        self.__parent = value

    @classmethod
    def from_json(cls, data):
        data["question"] = FText.from_json(data["question"])
        data["feedback"] = FText.from_json(data["feedback"])
        data["tags"] = Tags.from_json(data["tags"])
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["name"] = (str, "name")
        tags["questiontext"] = (FText.from_xml, "question")
        tags["generalfeedback"] = (FText.from_xml, "feedback")
        tags["defaultgrade"] = (float, "default_grade")
        tags["idnumber"] = (int, "dbid")
        tags["tags"] = (Tags.from_xml, "tags")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool) -> et.Element:
        """
        This method converts current object to Moodle XML.
        """
        question = et.Element("question", {"type": self.MOODLE})
        name = et.SubElement(question, "name")
        et.SubElement(name, "text").text = self.name
        question.append(self.question.to_xml(strict))
        if self.feedback:
            question.append(self.feedback.to_xml(strict))
        et.SubElement(question, "defaultgrade").text = self.default_grade
        # et.SubElement(question, "hidden").text = "0"
        if self.dbid is not None:
            et.SubElement(question, "idnumber").text = self.dbid
        if self.tags:
            question.append(self.tags.to_xml(strict))
        return question


class _QuestionMT(_Question):

    def __init__(self, options: list = None, hints: List[Hint] = None,
                 penalty=0.5, **kwargs):
        super().__init__(**kwargs)
        self.penalty = penalty
        self.hints = [] if hints is None else hints
        self.options = [] if options is None else options

    @classmethod
    def from_json(cls, data: dict):
        for i in range(len(data["hints"])):
            data["hints"][i] = Hint.from_json(data["hints"][i])
        # Defintion of options reading should be done by children
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["hint"] = (Hint.from_xml, "hints", True)
        tags["penalty"] = (float, "penalty")
        # Defintion of options reading should be done by children
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool) -> et.Element:
        question = super().to_xml(strict)
        for hint in self.hints:
            question.append(hint.to_xml(strict))
        et.SubElement(question, "penalty").text = str(self.penalty)
        if hasattr(self, "options"):             # Workaround for
            for sub in self.options:             # QRandomMatching.
                elem = sub.to_xml(strict)        # If strict, some may
                if elem:                         # return None.
                    question.append(elem)
        return question


class _QuestionMTCS(_QuestionMT):
    """Represents classes that have both Multiple tries attributes and
    Combinated Feedbacks parameters. There are no classes that don't present
    all the 4 first attributes. Shuffle was added here too because it is
    also used by all the classes that uses the other 2 groups, except
    <code>QRandomMatching</code>. For now, this is the more efficient way to
    handle this. TODO: track future updates to shuffle attribute.
    """

    def __init__(self, if_correct: FText = None, if_incomplete: FText = None,
                 if_incorrect: FText = None, shuffle=False, show_num=False,
                 **kwargs):
        super().__init__(**kwargs)
        self.if_correct = FText("correctfeedback") \
            if if_correct is None else if_correct
        self.if_incomplete = FText("partiallycorrectfeedback") \
            if if_incomplete is None else if_incomplete
        self.if_incorrect = FText("incorrectfeedback") \
            if if_incorrect is None else if_incorrect
        self.show_num = show_num
        self.shuffle = shuffle

    @classmethod
    def from_json(cls, data: dict):
        data["if_correct"] = FText.from_json(data["if_correct"])
        data["if_incomplete"] = FText.from_json(data["if_incomplete"])
        data["if_incorrect"] = FText.from_json(data["if_incorrect"])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["correctfeedback"] = (FText.from_xml, "if_correct")
        tags["partiallycorrectfeedback"] = (FText.from_xml, "if_incomplete")
        tags["incorrectfeedback"] = (FText.from_xml, "if_incorrect")
        tags["shownumcorrect"] = (bool, "show_num")
        tags["shuffleanswers"] = (bool, "shuffle")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool) -> et.Element:
        question = super().to_xml(strict)
        question.append(self.if_correct.to_xml(strict))
        question.append(self.if_incomplete.to_xml(strict))
        question.append(self.if_incorrect.to_xml(strict))
        if self.show_num:
            et.SubElement(question, "shownumcorrect")
        if hasattr(self, "shuffle") and self.shuffle:    # Workaround for
            et.SubElement(question, "shuffleanswers")   # QRandomMatching
        return question


class _QuestionMTUH(_QuestionMT):
    """A
    """

    def __init__(self, grading_type=Grading.IGNORE, unit_penalty=0.0,
                 show_unit=ShowUnits.TEXT, left=False, **kwargs):
        super().__init__(**kwargs)
        self.grading_type = grading_type
        self.unit_penalty = unit_penalty
        self.show_unit = show_unit
        self.left = left

    @classmethod
    def from_json(cls, data: dict):
        data["grading_type"] = Grading(data["grading_type"])
        data["show_unit"] = ShowUnits(data["show_unit"])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["unitgradingtype"] = (Grading, "grading_type")
        tags["unitpenalty"] = (str, "unit_penalty")
        tags["unitsleft"] = (bool, "left")
        tags["showunits"] = (ShowUnits, "show_unit")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool) -> et.Element:
        question = super().to_xml(strict)
        et.SubElement(question, "unitgradingtype").text = self.grading_type.value
        et.SubElement(question, "unitpenalty").text = self.unit_penalty
        et.SubElement(question, "showunits").text = self.show_unit.value
        et.SubElement(question, "unitsleft").text = self.left
        return question


class QCalculated(_QuestionMTUH):
    """Represents a "Calculated"q question, in which a numberical result should
    be provided. Note that <code>single</code> tag may show up in Moodle
    xml document but this seems to be just a bug. Th class don't use it.
    """
    MOODLE = "calculated"
    QNAME = "Calculated"

    def __init__(self, synchronize: Synchronise = None, units: List[Unit] = None,
                 datasets: List[Dataset] = None, **kwargs):
        """[summary]

        Args:
            synchronize (int): [description]
            units (List[Unit], optional): [description].
            datasets (List[Dataset], optional): Data set of variables to be
                used during question in equations.
        """
        super().__init__(**kwargs)
        self.synchronize = Synchronise.NO_SYNC if synchronize is None \
            else synchronize
        self.units = [] if units is None else units
        self.datasets = [] if datasets is None else datasets

    @classmethod
    def from_json(cls, data) -> "QCalculated":
        data["synchronize"] = Synchronise(data["synchronize"])
        for i in range(len(data["units"])):
            data["units"][i] = Unit.from_json(data["units"][i])
        for i in range(len(data["datasets"])):
            data["datasets"][i] = Dataset.from_json(data["datasets"][i])
        for i in range(len(data["options"])):
            data["options"][i] = CalculatedAnswer.from_json(data["options"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["synchronize"] = (Synchronise, "synchronize")
        tags["units"] = (Unit.from_xml, "units", True)
        tags["dataset_definitions"] = (Dataset.from_xml_list, "datasets")
        tags["answer"] = (CalculatedAnswer.from_xml, "options", True)
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool) -> et.Element:
        question = super().to_xml(strict)
        et.SubElement(question, "synchronize").text = self.synchronize.value
        if self.units:
            units = et.SubElement(question, "units")
            for unit in self.units:
                units.append(unit.to_xml(strict))
        if self.datasets:
            definitions = et.SubElement(question, "dataset_definitions")
            for dataset in self.datasets:
                definitions.append(dataset.to_xml(strict))
        return question


class QCalculatedSimple(QCalculated):
    """Same as QCalculated. Implemented only for compatibility with the moodle
    XML format.
    """
    MOODLE = "calculatedsimple"
    QNAME = "Simplified Calculated"


class QCalculatedMultichoice(_QuestionMTCS):
    """Represents a "Calculated" question with multiple choices, behaving like
    a multichoice question where the answers are calculated using equations and
    datasets.
    """
    MOODLE = "calculatedmulti"
    QNAME = "Calculated Multichoice"

    def __init__(self, synchronize: Synchronise, numbering: Numbering = None,
                 single = False, datasets: List[Dataset] = None, **kwargs):
        super().__init__(**kwargs)
        self.synchronize = synchronize
        self.single = single
        self.numbering = Numbering.ALF_LR if numbering is None else numbering
        self.datasets = [] if datasets is None else datasets

    def add_dataset(self, status: Status, name: str, dist: Distribution,
                    minim: float, maxim: float, dec: int) -> None:
        """_summary_

        Args:
            status (Status): _description_
            name (str): _description_
            dist (Distribution): _description_
            minim (float): _description_
            maxim (float): _description_
            dec (int): _description_
        """
        data = Dataset(status, name, "calculated", dist, minim, maxim, dec)
        self.datasets.append(data)

    @classmethod
    def from_json(cls, data: dict) -> QCalculatedMultichoice:
        data["numbering"] = Numbering(data["numbering"])
        data["synchronize"] = Synchronise(data["synchronize"])
        for i in range(len(data["datasets"])):
            data["datasets"][i] = Dataset.from_json(data["datasets"][i])
        for i in range(len(data["options"])):
            data["options"][i] = CalculatedAnswer.from_json(data["options"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["synchronize"] = (Synchronise, "synchronize")
        tags["single"] = (bool, "single")
        tags["answernumbering"] = (Numbering, "numbering")
        tags["dataset_definitions"] = (Dataset.from_xml_list, "datasets")
        tags["answer"] = (CalculatedAnswer.from_xml, "options", True)
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool) -> et.Element:
        question = super().to_xml(strict)
        et.SubElement(question, "synchronize").text = self.synchronize.value
        if self.single:
            et.SubElement(question, "single")
        et.SubElement(question, "answernumbering").text = self.numbering.value
        dataset_definitions = et.SubElement(question, "dataset_definitions")
        for dataset in self.datasets:
            dataset_definitions.append(dataset.to_xml(strict))
        return question


class QCloze(_QuestionMT):
    """This is a very simples class that hold cloze data. All data is compressed
    inside the question text, so no further implementation is necessary.
    """
    MOODLE = "cloze"
    QNAME = "Cloze"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cloze_text = self.question.text
        self.update()

    @classmethod
    def from_json(cls, data: dict):
        for i in range(len(data["options"])):
            data["options"][i] = ClozeItem.from_json(data["options"][i])
        return super().from_json(data)

    @classmethod
    def from_cloze(cls, buffer):
        """_summary_

        Args:
            buffer (MOODLE_): _description_

        Returns:
            QCloze: _description_
        """
        data = buffer.read()
        name, text = data.split("\n", 1)
        ftext = FText("questiontext", text, Format.HTML, None)
        return cls(name=name, question=ftext)

    def to_xml(self, strict: bool) -> et.Element:
        tmp = self.question.text
        self.question.text = self._cloze_text
        question = super().to_xml(strict)
        self.question.text = tmp
        return question

    def update(self):
        self.options.clear()
        pattern = re.compile(r"(?!\\)\{(\d+)?(?:\:(.*?)\:)(.*?(?!\\)\})")
        gui_text = []
        start = 0
        for match in pattern.finditer(self._cloze_text):
            item = ClozeItem.from_cloze(match)
            self.options.append(item)
            gui_text.append(self._cloze_text[start: match.start()-1])
            start =  match.end()+1 
        gui_text.append(self._cloze_text[start:])
        self.question.text = MARKER_STR.join(gui_text)


class QDescription(_Question):
    """Represents a simple description. This is not a question. It has the same
    extructure as Question class and was add for compatiblity with the moodle
    XML format.
    """
    MOODLE = "description"
    QNAME = "Description"

    @classmethod
    def from_gift(cls, header: list, answer: list):
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        return cls(name=header[1], question=FText("questiontext", header[3],
                                                  formatting, None))


class QDragAndDropText(_QuestionMTCS):
    """
    This class represents a drag and drop text onto image question.
    It inherits from abstract class Question.
    """
    MOODLE = "ddwtos"
    QNAME = "Drag and Drop Text"

    @classmethod
    def from_json(cls, data):
        for i in range(len(data["options"])):
            data["options"][i] = DragText.from_json(data["options"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["dragbox"] = (DragText.from_xml, "options", True)
        return super().from_xml(root, tags, attrs)


class QDragAndDropImage(_QuestionMTCS):
    """This class represents a drag and drop onto image question.
    It inherits from abstract class Question.
    """
    MOODLE = "ddimageortext"
    QNAME = "Drag and Drop Image"

    def __init__(self, background: B64File = None,
                 zones: List[DropZone] = None, **kwargs):
        """Creates an drag and drop onto image type of question.

        Args:
            background (str): Filepath to the background image.
        """
        super().__init__(**kwargs)
        self.background = background
        self.zones = [] if zones is None else zones

    def add_image(self, text: str, group: int, file: str, unlimited=False):
        """Adds new DragItem with assigned DropZones.

        Args:
            file (str): path to image to be used as a drag image;
            text (str, optional): text of the drag text.
            group (int, optional): group.
            unlimited (bool, optional): if item is allowed to be used again.
                Defaults to False.
        """
        dragimage = DragItem(len(self.options) + 1, text, unlimited, group,
                             image=file)
        self.options.append(dragimage)

    def add_text(self, text: str, group: str, unlimited=False):
        """Adds new DragText with assigned DropZones.

        Args:
            text (str): text of the drag text.
            group (str): group.
            unlimited (bool, optional): if item is allowed to be used again.
                Defaults to False.
        """
        dragitem = DragItem(len(self.options) + 1, text, unlimited, group)
        self.options.append(dragitem)

    def add_zone(self, coord_x: int, coord_y: int, text: str, choice: int):
        """[summary]

        Args:
            x (int): [description]
            y (int): [description]
            text (str): [description]
            choice (int): [description]
        """
        self.zones.append(DropZone(coord_x, coord_y, text, choice,
                                   len(self.zones) + 1))

    @classmethod
    def from_json(cls, data):
        data["background"] = B64File.from_json(data["background"])
        for i in range(len(data["options"])):
            data["options"][i] = DragItem.from_json(data["options"][i])
        for i in range(len(data["zones"])):
            data["zones"][i] = DropZone.from_json(data["zones"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["file"] = (B64File.from_xml, "background")
        tags["drag"] = (DragItem.from_xml, "options", True)
        tags["drop"] = (DropZone.from_xml, "zones", True)
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool):
        question = super().to_xml(strict)
        if self.background:
            question.append(self.background.to_xml(strict))
        for dropzone in self.zones:
            question.append(dropzone.to_xml(strict))
        return question


class QDragAndDropMarker(_QuestionMTCS):
    """Represents a Drag and Drop question where the items are markers.
    """
    MOODLE = "ddmarker"
    QNAME = "Drag and Drop Marker"

    def __init__(self, highlight=False, background: B64File = None,
                 zones: List[DropZone] = None,  **kwargs):
        """Creates an drag and drop onto image type of question.

        Args:
            background (str): Filepath to the background image.
        """
        super().__init__(**kwargs)
        self.background = background
        self.highlight = highlight
        self.zones = [] if zones is None else zones

    def add_option(self, text: str, no_of_drags: str, unlimited: bool = False):
        """[summary]

        Args:
            text (str): [description]
            no_of_drags (str): [description]
            unlimited (bool, optional): [description]. Defaults to False.
        """
        dragitem = DragItem(len(self.options) + 1, text, unlimited,
                            no_of_drags=no_of_drags)
        self.options.append(dragitem)

    @classmethod
    def from_json(cls, data):
        data["background"] = B64File.from_json(data["background"])
        for i in range(len(data["options"])):
            data["options"][i] = DragItem.from_json(data["options"][i])
        for i in range(len(data["zones"])):
            data["zones"][i] = DropZone.from_json(data["zones"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["file"] = (B64File.from_xml, "background")
        tags["showmisplaced"] = (bool, "highlight")
        tags["drag"] = (DragItem.from_xml, "options", True)
        tags["drop"] = (DropZone.from_xml, "zones", True)
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool):
        question = super().to_xml(strict)
        if self.highlight:
            et.SubElement(question, "showmisplaced")
        for dropzone in self.zones:
            question.append(dropzone.to_xml(strict))
        if self.background:
            question.append(self.background.to_xml(strict))
        return question


class QEssay(_Question):
    """Represents an essay question, in which the answer is written as an essay
    and need to be submitted for review (no automatic correct/answer feedback
    provided).
    """
    MOODLE = "essay"
    QNAME = "Essay"

    def __init__(self, lines=10, attachments=0, max_bytes=0, file_types="", 
                 rsp_required=True, atts_required=False,
                 min_words: int = None, max_words: int = None,
                 grader_info: FText = None,
                 template: FText = None, rsp_format=ResponseFormat.HTML,
                 **kwargs):
        super().__init__(**kwargs)
        self.rsp_format = rsp_format
        self.rsp_required = rsp_required
        self.lines = lines
        self.min_words = min_words
        self.max_words = max_words
        self.attachments = attachments
        self.atts_required = atts_required
        self.max_bytes = max_bytes
        self.file_types = file_types
        self.grader_info = grader_info
        self.template = template

    @classmethod
    def from_gift(cls, header: list, answer: list):
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        return cls(name=header[1], question=FText("questiontext", header[3],
                                                  formatting, None))

    @classmethod
    def from_json(cls, data):
        data["rsp_format"] = ResponseFormat(data["rsp_format"])
        data["grader_info"] = FText.from_json(data["grader_info"])
        data["template"] = FText.from_json(data["template"])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["responseformat"] = (ResponseFormat, "rsp_format")
        tags["responserequired"] = (bool, "rsp_required")
        tags["responsefieldlines"] = (int, "lines")
        tags["minwordlimit"] = (int, "min_words")
        tags["minwordlimit"] = (int, "max_words")
        tags["attachments"] = (int, "attachments")
        tags["attachmentsrequired"] = (bool, "atts_required")
        tags["maxbytes"] = (int, "max_bytes")
        tags["filetypeslist"] = (str, "file_types")
        tags["graderinfo"] = (FText.from_xml, "grader_info")
        tags["responsetemplate"] = (FText.from_xml, "template")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool) -> et.Element:
        question = super().to_xml(strict)
        et.SubElement(question, "responseformat").text = self.rsp_format.value
        if self.rsp_required:
            et.SubElement(question, "responserequired")
        et.SubElement(question, "responsefieldlines").text = self.lines
        et.SubElement(question, "attachments").text = self.attachments
        if self.atts_required:
            et.SubElement(question, "attachmentsrequired")
        if self.max_bytes:
            et.SubElement(question, "maxbytes").text = self.max_bytes
        if self.file_types:
            et.SubElement(question, "filetypeslist").text = self.file_types
        if self.grader_info:
            question.append(self.grader_info.to_xml(strict))
        if self.template:
            question.append(self.template.to_xml(strict))
        return question


class QMatching(_QuestionMTCS):
    """Represents a Matching question, in which the goal is to find matchs.
    """
    MOODLE = "matching"
    QNAME = "Matching"

    def add_option(self, text: str, answer: str) -> None:
        """[summary]

        Args:
            text (str): [description]
            answer (str): [description]
        """
        self.options.append(Subquestion(Format.AUTO, text, answer))

    @classmethod
    def from_gift(cls, header: list, answer: list):
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(name=header[1], question=FText("questiontext", header[3],
                                                 formatting, None))
        for ans in answer:
            if ans[0] == "=":
                rgx = re.match(r"(.*?)(?<!\\)->(.*)", ans[2])
                qst.options.append(Subquestion(formatting, rgx[1].strip(),
                                               rgx[2].strip()))
            elif ans[0] == "####":
                qst.feedback = FText("generalfeedback", ans[2], formatting)
        return qst

    @classmethod
    def from_json(cls, data):
        for i in range(len(data["options"])):
            data["options"][i] = Subquestion.from_json(data["options"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["subquestion"] = (Subquestion.from_xml, "options", True)
        return super().from_xml(root, tags, attrs)


class QRandomMatching(_QuestionMTCS):
    """Represents a Random match question.
    """
    MOODLE = "randomsamatch"
    QNAME = "Random Matching"

    def __init__(self, choose: int = 0, subcats: bool = False, **kwargs):
        super().__init__(**kwargs)
        delattr(self, "options")
        delattr(self, "shuffle")
        self.choose = choose
        self.subcats = subcats

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["choose"] = (int, "choose")
        tags["subcats"] = (bool, "subcats")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool) -> et.Element:
        question = super().to_xml(strict)
        et.SubElement(question, "choose").text = self.choose
        et.SubElement(question, "subcats").text = self.subcats
        return question


class QMissingWord(_QuestionMTCS):
    """ Represents a "Missing Word" question.
    """
    MOODLE = "gapselect"
    QNAME = "Missing Word"

    @classmethod
    def from_json(cls, data):
        for i in range(len(data["options"])):
            data["options"][i] = SelectOption.from_json(data["options"][i])
        return super().from_json(data)

    @classmethod
    def from_gift(cls, header: list, answer: list):
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(name=header[1], question=FText("questiontext", header[3],
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
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["selectoption"] = (SelectOption.from_xml, "options", True)
        return super().from_xml(root, tags, attrs)

    # def update(self):
    #     for i in re.finditer(r"\[\[[0-9]+\]\]", self.toPlainText()):
    #         self.__tags.append(i.span())


class QMultichoice(_QuestionMTCS):
    """This class represents 'Multiple choice' question.
    """
    MOODLE = "multichoice"
    QNAME = "Multichoice"

    def __init__(self, single=True, show_instr=False,
                 numbering: Numbering = None, **kwargs):
        super().__init__(**kwargs)
        self.single = single
        self.show_instr = show_instr
        self.numbering = Numbering.ALF_LR if numbering is None else numbering

    @classmethod
    def from_json(cls, data):
        data["numbering"] = Numbering(data["numbering"])
        for i in range(len(data["options"])):
            data["options"][i] = Answer.from_json(data["options"][i])
        return super().from_json(data)

    @classmethod
    def from_aiken(cls, buffer, name):
        """_summary_

        Args:
            buffer (LineBuffer): _description_
            name (str): _description_

        Returns:
            QMultichoice: _description_
        """
        header = buffer.read(True).strip()
        answers = []
        while buffer.read() and "ANSWER:" not in buffer.read()[:7]:
            ans = re.match(r"[A-Z]+\) (.+)", buffer.read(True))
            if ans:
                answers.append(Answer(0.0, ans[1], None, Format.PLAIN))
        try:
            answers[ord(buffer.read(True)[8].upper())-65].fraction = 100.0
        except IndexError:
            LOG.exception(f"Failed to set correct answer in question {name}.")
        return cls(name=name, options=answers,
                   question=FText("questiontext", header, Format.PLAIN, None))

    @classmethod
    def from_gift(cls, header: list, answer: list):
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(name=header[1], question=FText("questiontext", header[3],
                                                 formatting, None))
        prev_answer = None
        for ans in answer:
            txt = ans[2]
            if ans[0] == "~":  # Wrong or partially correct answer
                fraction = 0 if not ans[1] else float(ans[1][1:-1])
                prev_answer = Answer(fraction, txt, None, formatting)
                qst.options.append(prev_answer)
            elif ans[0] == "=":  # Correct answer
                prev_answer = Answer(100, txt, None, formatting)
                qst.options.append(prev_answer)
            elif ans[0] == "#":  # Answer feedback
                prev_answer.feedback = FText("feedback", ans[2],
                                             formatting, None)
        return qst

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["single"] = (bool, "single")
        tags["showstandardinstruction"] = (bool, "show_instr")
        tags["answernumbering"] = (Numbering, "numbering")
        tags["answer"] = (Answer.from_xml, "options", True)
        return super().from_xml(root, tags, attrs)

    @staticmethod
    def from_markdown(lines: list, answer_mkr: str, question_mkr: str,
                      name: str = "mkquestion"):
        """[summary]

        Returns:
            [type]: [description]
        """
        data = ""
        match = re.match(answer_mkr, lines[-1])
        while lines and match is None:
            data += lines.pop().strip()
            match = re.match(answer_mkr, lines[-1])
        question = QMultichoice(name=name, question=FText("questiontext", data,
                                                          Format.MD, None))
        regex_exp = f"({question_mkr})|({answer_mkr})"
        while lines:
            match = re.match(regex_exp, lines.pop())
            if match and match[3]:
                ans = Answer(100.0 if match[4] is not None else 0.0, match[5],
                             None, Format.HTML)
                question.options.append(ans)
            else:
                break
        return question

    def to_xml(self, strict: bool) -> et.Element:
        question = super().to_xml(strict)
        et.SubElement(question, "answernumbering").text = self.numbering.value
        if self.single:
            et.SubElement(question, "single")
        return question


class QNumerical(_QuestionMTUH):
    """
    This class represents 'Numerical Question' moodle question type.
    Units are currently not implemented, only numerical answer, which
    are specified as text and absolute tolerance value are implemented
    """
    MOODLE = "numerical"
    QNAME = "Numerical"

    def __init__(self, units: List[Unit] = None,  **kwargs):
        super().__init__(**kwargs)
        self.units = [] if units is None else units

    def add_option(self, text: str, tol: float, fraction: float,
                   feedback: str = None) -> None:
        """_summary_

        Args:
            tol (float): _description_
            fraction (float): _description_
            text (str): _description_
            feedback (str, optional): _description_. Defaults to None.
        """
        self.options.append(NumericalAnswer(tol, fraction=fraction, text=text,
                                            formatting=feedback))

    @classmethod
    def from_json(cls, data):
        for i in range(len(data["units"])):
            data["units"][i] = Unit.from_json(data["units"][i])
        for i in range(len(data["options"])):
            data["options"][i] = NumericalAnswer.from_json(data["options"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["answer"] = (NumericalAnswer.from_xml, "options", True)
        tags["units"] = (Unit.from_xml, "units", True)
        return super().from_xml(root, tags, attrs)

    @classmethod
    def from_gift(cls, header: list, answer: list):
        def _extract(data: str) -> tuple:
            rgx = re.match(r"(.+?)(:|(?:\.\.))(.+)", data)
            if rgx[2] == "..":  # Converts min/max to value +- tol
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
        qst = cls(name=header[1], question=FText("questiontext", header[3],
                                                 formatting, None))
        if len(answer) == 1:
            txt, tol = _extract(answer[0][2])
            qst.options.append(NumericalAnswer(tol, fraction=100, text=txt,
                                               formatting=Format.AUTO))
        elif len(answer) > 1:
            for ans in answer[1:]:
                if ans[0] == "=":   # Happens first, thus ans is always defined
                    txt, tol = _extract(ans[2])
                    fraction = float(ans[1][1:-1]) if ans[0] == "=" else 0
                    nans = NumericalAnswer(tol, fraction=fraction, text=txt,
                                           formatting=Format.AUTO)
                    qst.options.append(nans)
                elif ans[0] == "~":
                    nans = NumericalAnswer(0, fraction=0, text="",
                                           formatting=Format.AUTO)
                elif ans[0] == "#":
                    nans.feedback = FText("feedback", ans[2], formatting, None)
        return qst

    def to_xml(self, strict: bool) -> et.Element:
        question = super().to_xml(strict)
        if len(self.units) > 0:
            units = et.SubElement(question, "units")
            for unit in self.units:
                units.append(unit.to_xml(strict))
        return question


class QShortAnswer(_QuestionMT):
    """
    This class represents 'Short answer' question.
    """
    MOODLE = "shortanswer"
    QNAME = "Short Answer"

    def __init__(self, use_case = False, **kwargs):
        """_summary_

        Args:
            use_case (bool): If answer is case sensitive. Defaults to False.

        Returns:
            _type_: _description_
        """
        super().__init__(**kwargs)
        self.use_case = use_case

    @classmethod
    def from_json(cls, data):
        for i in range(len(data["options"])):
            data["options"][i] = Answer.from_json(data["options"][i])
        return super().from_json(data)

    @classmethod
    def from_gift(cls, header: list, answer: list):
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(name=header[1], question=FText("questiontext", header[3],
                                                 formatting, None))
        for ans in answer:
            fraction = 100 if not ans[1] else float(ans[1][1:-1])
            qst.options.append(Answer(fraction, ans[2], formatting))
        return qst

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["usecase"] = (str, "use_case")
        tags["answer"] = (Answer.from_xml, "options", True)
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool) -> et.Element:
        question = super().to_xml(strict)
        et.SubElement(question, "usecase").text = self.use_case
        return question


class QTrueFalse(_Question):
    """
    This class represents true/false question.
    """
    MOODLE = "truefalse"
    QNAME = "True or False"

    def __init__(self, options: list, **kwargs) -> None:
        super().__init__(**kwargs)
        if options is not None:
            if len(options) != 2:
                raise ValueError()
            for answer in options:
                if answer.text.lower() == "true":
                    self.__true = answer
                    self.__correct = answer.fraction == 100
                elif answer.text.lower() == "false":
                    self.__false = answer
        else:
            self.__true = Answer(100, "true", FText("feedback"), Format.AUTO)
            self.__false = Answer(0, "false", FText("feedback"), Format.AUTO)
            self.__correct = True

    def set_feedbacks(self, correct: FText, incorrect: FText):
        """_summary_

        Args:
            correct (FText): _description_
            incorrect (FText): _description_
        """
        self.__true.feedback = correct if self.correct else incorrect
        self.__false.feedback = correct if not self.correct else incorrect

    @property
    def correct(self) -> bool:
        """_summary_

        Returns:
            bool: _description_
        """
        return self.__correct

    @correct.setter
    def correct(self, value: bool) -> None:
        """_summary_

        Args:
            value (bool): _description_
        """
        self.__true.fraction = 100 if value else 0
        self.__false.fraction = 100 if not value else 0
        self.__correct = value

    @classmethod
    def from_json(cls, data: dict):
        true_answer = Answer.from_json(data.pop("_QTrueFalse__true"))
        wrong_answer = Answer.from_json(data.pop("_QTrueFalse__false"))
        data["options"] = [true_answer, wrong_answer]
        data.pop("_QTrueFalse__correct")  # Defined during init call
        return super().from_json(data)

    @classmethod
    def from_gift(cls, header: list, answer: list):
        correct = answer.pop(0)[0].lower() in ["true", "t"]
        true_ans = Answer(100 if correct else 0, "true", None, Format.AUTO)
        false_ans = Answer(0 if correct else 100, "false", None, Format.AUTO)
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(options=[true_ans, false_ans], name=header[1],
                  question=FText("questiontext", header[3], formatting, None))
        for ans in answer:
            if ans[0] == "####":
                qst.feedback = FText("generalfeedback", ans[2],
                                     Format(header[2][1:-1]))
            elif false_ans.feedback is None:
                false_ans.feedback = FText("feedback", ans[2],
                                           Format(header[2][1:-1]))
            else:
                true_ans = FText("feedback", ans[2], Format(header[2][1:-1]))
        return qst

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["answer"] = (Answer.from_xml, "options", True)
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool) -> et.Element:
        question = super().to_xml(strict)
        question.append(self.__true.to_xml(strict))
        question.append(self.__false.to_xml(strict))
        return question


class QFreeDrawing(_Question):
    """Represents a question where the use is free to make any drawing. The
    result is submited for review (there is no automatic correct/wrong
    feedback).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class QLineDrawing(_Question):
    """Represents a question where the user should draw line either to complete
    an image or to draw a new one. The result is submited for review (there is
    no automatic correct/wrong feedback).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class QCrossWord(_Question):
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
    def from_json(cls, data):
        for i in range(len(data["words"])):
            data["words"][i] = CrossWord.from_json(data["words"][i])
        return super().from_json(data)
