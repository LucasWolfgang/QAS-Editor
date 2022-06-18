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
import json
from typing import TYPE_CHECKING
from enum import Enum
from ..enums import ClozeFormat, Direction, Distribution, Grading, RespFormat, \
                    ShapeType, Synchronise, TolType, TolFormat, Status, \
                    ShowUnits, TextFormat, Numbering
from ..utils import B64File, Dataset, FText, Hint, TList, Unit
from ..answer import ACalculated, ANumerical, Answer, ClozeItem, DragItem, \
                     ACrossWord, DropZone, SelectOption, DragGroup, Subquestion
from ..questions import QCalculatedMultichoice, QCrossWord, QDescription, \
                        QTrueFalse, QCalculated, QCalculatedSimple, QCloze,\
                        QDaDImage, QDaDMarker, QMissingWord,\
                        QEssay, QMatching, QDaDText, QMultichoice, \
                        QNumerical, QRandomMatching, QShortAnswer
if TYPE_CHECKING:
    from ..category import Category

def _from_json(data: dict, cls):
    return cls(**data) if isinstance(data, dict) else None


def _from_b64file(data: dict):
    return _from_json(data, B64File)


def _from_dataset(data: dict):
    data["status"] = Status(data["status"])
    data["distribution"] = Distribution(data["distribution"])
    tmp = {}  # Convertion of keys from string to int
    for key in data["items"]:
        tmp[int(key)] = data["items"][key]
    data["items"] = tmp
    return _from_json(data, Dataset)


def _from_ftext(data: dict):
    data["formatting"] = TextFormat(data["formatting"])
    for index in range(len(data["bfile"])):
        data["bfile"][index] = _from_b64file(data["bfile"][index])
    return _from_json(data, FText)


def _from_hint(data: dict):
    data["formatting"] = TextFormat(data["formatting"])
    return _from_json(data, Hint)


def _from_tags(data: list):
    return TList(str, data)


def _from_unit(data:dict):
    return _from_json(data, Unit)


# -----------------------------------------------------------------------------


def _from_answer(data: dict, cls=None):
    data["formatting"] = TextFormat(data["formatting"])
    data["feedback"] = _from_ftext(data["feedback"])
    return _from_json(data, cls if cls else Answer)


def _from_anumerical(data: dict, cls=None):
    return _from_answer(data, cls if cls else ANumerical)


def _from_acalculated(data: dict):
    data["ttype"] = TolType(data["ttype"])
    data["aformat"] = TolFormat(data["aformat"])
    return _from_anumerical(data, ACalculated)


def _from_clozeitem(data: dict):
    data["cformat"] = ClozeFormat(data["cformat"])
    for i in range(len(data["opts"])):
        data["opts"][i] = _from_answer(data["opts"][i])
    return _from_json(data, ClozeItem)


def _from_dragtext(data: dict):
    return _from_json(data, DragGroup)


def _from_dragitem(data: dict):
    data["image"] = _from_b64file(data["image"])
    return _from_json(data, DragItem)


def _from_dropzone(data: dict):
    if data["shape"] is not None:
        data["shape"] = ShapeType(data["shape"])
    return _from_json(data, DropZone)


def _from_acrossword(data: dict):
    data["direction"] = Direction(data["direction"])
    return _from_json(data, ACrossWord)


def _from_subquestion(data: dict):
    data["formatting"] = TextFormat(data["formatting"])
    return _from_json(data, Subquestion)


def _from_selectoption(data: dict):
    return _from_json(data, SelectOption)


# -----------------------------------------------------------------------------


def _from_question(data: dict, cls):
    data["question"] = _from_ftext(data["question"])
    data["feedback"] = _from_ftext(data["feedback"])
    data["tags"] = _from_tags(data["tags"])
    return _from_json(data, cls)


def _from_question_mt(data: dict, cls):
    for i in range(len(data["hints"])):
        data["hints"][i] = _from_hint(data["hints"][i])
    # Defintion of options reading should be done by children
    return _from_question(data, cls)


def _from_question_mtcs(data: dict, cls):
    data["if_correct"] =_from_ftext(data["if_correct"])
    data["if_incomplete"] = _from_ftext(data["if_incomplete"])
    data["if_incorrect"] = _from_ftext(data["if_incorrect"])
    return _from_question_mt(data, cls)


def _from_question_mtuh(data: dict, cls):
    data["grading_type"] = Grading(data["grading_type"])
    data["show_unit"] = ShowUnits(data["show_unit"])
    return _from_question_mt(data, cls)


def _from_qcalculated(data: dict, cls=None):
    data["synchronize"] = Synchronise(data["synchronize"])
    for i in range(len(data["units"])):
        data["units"][i] = _from_unit(data["units"][i])
    for i in range(len(data["datasets"])):
        data["datasets"][i] = _from_dataset(data["datasets"][i])
    for i in range(len(data["options"])):
        data["options"][i] = _from_acalculated(data["options"][i])
    return _from_question_mtuh(data, cls if cls else QCalculated)


def _from_qcalculatedsimple(data: dict):
    return _from_qcalculated(data, QCalculatedSimple)


def _from_qcalculatedmultichoice(data: dict):
    data["numbering"] = Numbering(data["numbering"])
    data["synchronize"] = Synchronise(data["synchronize"])
    for i in range(len(data["datasets"])):
        data["datasets"][i] = _from_dataset(data["datasets"][i])
    for i in range(len(data["options"])):
        data["options"][i] = _from_acalculated(data["options"][i])
    return _from_question_mtcs(data, QCalculatedMultichoice)


def _from_qcloze(data: dict):
    for i in range(len(data["options"])):
        data["options"][i] = _from_clozeitem(data["options"][i])
    return _from_question_mt(data, QCloze)


def _from_qdescription(data: dict):
    return _from_question(data, QDescription)


def _from_qdraganddroptext(data: dict):
    for i in range(len(data["options"])):
        data["options"][i] = _from_dragtext(data["options"][i])
    return _from_question_mtcs(data, QDaDText)


def _from_qdraganddropimage(data: dict):
    data["background"] = _from_b64file(data["background"])
    for i in range(len(data["options"])):
        data["options"][i] = _from_dragitem(data["options"][i])
    for i in range(len(data["zones"])):
        data["zones"][i] = _from_dropzone(data["zones"][i])
    return _from_question_mtcs(data, QDaDImage)


def _from_qdraganddropmarker(data: dict):
    data["background"] = _from_b64file(data["background"])
    for i in range(len(data["options"])):
        data["options"][i] = _from_dragitem(data["options"][i])
    for i in range(len(data["zones"])):
        data["zones"][i] = _from_dropzone(data["zones"][i])
    return _from_question_mtcs(data, QDaDMarker)


def _from_qessay(data: dict):
    data["rsp_format"] = RespFormat(data["rsp_format"])
    data["grader_info"] = _from_ftext(data["grader_info"])
    data["template"] = _from_ftext(data["template"])
    return _from_question(data, QEssay)


def _from_qmatching(data: dict):
    for i in range(len(data["options"])):
        data["options"][i] = _from_subquestion(data["options"][i])
    return _from_question_mtcs(data, QMatching)


def _from_qrandommatching(data: dict):
    return _from_question_mtcs(data, QRandomMatching)


def _from_qmissingword(data: dict):
    for i in range(len(data["options"])):
        data["options"][i] = _from_selectoption(data["options"][i])
    return _from_question_mtcs(data, QMissingWord)


def _from_qcrossword(data: dict):
    for i in range(len(data["words"])):
        data["words"][i] = _from_acrossword(data["words"][i])
    return _from_question(data, QCrossWord)


def _from_qmultichoice(data: dict):
    data["numbering"] = Numbering(data["numbering"])
    for i in range(len(data["options"])):
        data["options"][i] = _from_answer(data["options"][i])
    return _from_question_mtcs(data, QMultichoice)


def _from_qnumerical(data: dict):
    for i in range(len(data["units"])):
        data["units"][i] = _from_unit(data["units"][i])
    for i in range(len(data["options"])):
        data["options"][i] = _from_anumerical(data["options"][i])
    return _from_question_mtuh(data, QNumerical)


def _from_qshortanswer(data: dict):
    for i in range(len(data["options"])):
        data["options"][i] = _from_answer(data["options"][i])
    return _from_question_mt(data, QShortAnswer)


def _from_qtruefalse(data: dict):
    true_answer = _from_answer(data.pop("_QTrueFalse__true"))
    wrong_answer = _from_answer(data.pop("_QTrueFalse__false"))
    data["options"] = [true_answer, wrong_answer]
    data.pop("_QTrueFalse__correct")  # Defined during init call
    return _from_question(data, QTrueFalse)



# -----------------------------------------------------------------------------


_QTYPE = {
    "calculated": _from_qcalculated,
    "calculatedsimple": _from_qcalculatedsimple,
    "calculatedmulti": _from_qcalculatedmultichoice,
    "cloze": _from_qcloze,
    "description": _from_qdescription,
    "ddwtos":_from_qdraganddroptext,
    "ddimageortext": _from_qdraganddropimage,
    "ddmarker": _from_qdraganddropmarker,
    "essay": _from_qessay,
    "matching": _from_qmatching,
    "randomsamatch": _from_qrandommatching,
    "gapselect": _from_qmissingword,
    "multichoice": _from_qmultichoice,
    "numerical": _from_qnumerical,
    "shortanswer" : _from_qshortanswer,
    "truefalse": _from_qtruefalse
}


def read_json(cls, file_path) -> "Category":
    """
    Generic file. This is the default file format used by the QAS Editor.
    """
    def _rjrecursive(_dt: dict):
        quiz = cls(_dt["_Category__name"])
        for qst in _dt["_Category__questions"]:
            quiz.add_question(_QTYPE[qst.pop("MOODLE")](qst))
        for i in _dt["_Category__categories"]:
            quiz.add_subcat(_rjrecursive(_dt["_Category__categories"][i]))
        return quiz
    with open(file_path, "rb") as infile:
        data = json.load(infile)
    return _rjrecursive(data)


# -----------------------------------------------------------------------------


def write_json(self, file_path: str, pretty=False) -> None:
    """[summary]

    Args:
        file_path (str): [description]
        pretty (bool, optional): [description]. Defaults to False.
    """
    def _tjrecursive(data):
        for num, i in enumerate(data):
            res = val = data[i] if isinstance(data, dict) else i
            if isinstance(val, (list, dict)):
                res = _tjrecursive(val.copy())
            elif isinstance(val, Enum):  # For the enums
                res = val.value
            elif hasattr(val, "__dict__"):  # for the objects
                tmp = val.__dict__.copy()
                if hasattr(val, "MOODLE"):
                    tmp["MOODLE"] = val.MOODLE
                if "_Question__parent" in tmp:
                    del tmp["_Question__parent"]
                elif "_Category__parent" in tmp:
                    del tmp["_Category__parent"]
                res = _tjrecursive(tmp)
            if res != val:
                if isinstance(data, dict):
                    data[i] = res
                else:
                    data[num] = res
        return data
    tmp = self.__dict__.copy()
    del tmp["_Category__parent"]
    with open(file_path, "w", encoding="utf-8") as ofile:
        json.dump(_tjrecursive(tmp), ofile, indent=4 if pretty else None)
