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
from typing import TYPE_CHECKING
from xml.etree import ElementTree as et

from ..answer import ACalculated, ANumerical, Answer, DragItem, DragGroup, \
                     DropZone, Subquestion, SelectOption
from ..questions import QCalculated, QCalculatedMultichoice, QDescription,\
                        QCalculatedSimple, QCloze, QMissingWord, QTrueFalse,\
                        QDaDMarker, QDaDImage, QNumerical,\
                        QDaDText, QEssay, QMatching,  QMultichoice,\
                        QRandomMatching, QShortAnswer
from ..enums import TextFormat, ShowUnits,Numbering, RespFormat, Synchronise,\
                    ShapeType, Grading, Status, TolFormat, TolType,\
                    Distribution
from ..utils import gen_hier, Dataset, Hint, TList, FText, B64File, Unit
if TYPE_CHECKING:
    from ..category import Category


def serialize_fxml(write, elem, short_empty, pretty, level=0):
    tag = elem.tag
    text = elem.text
    if pretty:
        write(level * "  ")
    write(f"<{tag}")
    for key, value in elem.attrib.items():
        value = _escape_attrib_html(value)
        write(f" {key}=\"{value}\"")
    if (isinstance(text, str) and text) or text is not None or \
            len(elem) or not short_empty:
        if len(elem) and pretty:
            write(">\n")
        else:
            write(">")
        write(_escape_cdata(text))
        for child in elem:
            serialize_fxml(write, child, short_empty, pretty, level+1)
        if len(elem) and pretty:
            write(level * "  ")
        write(f"</{tag}>")
    else:
        write(" />")
    if pretty:
        write("\n")
    if elem.tail:
        write(_escape_cdata(elem.tail))


def _escape_cdata(data):
    if data is None:
        return ""
    if isinstance(data, (int, float)):
        return str(data)
    if ("&" in data or "<" in data or ">" in data) and not\
            (str.startswith(data, "<![CDATA[") and str.endswith(data, "]]>")):
        return f"<![CDATA[{data}]]>"
    return data


def _escape_attrib_html(data):
    if data is None:
        return ""
    if isinstance(data, (int, float)):
        return str(data)
    if "&" in data:
        data = data.replace("&", "&amp;")
    if ">" in data:
        data = data.replace(">", "&gt;")
    if "\"" in data:
        data = data.replace("\"", "&quot;")
    return data


# -----------------------------------------------------------------------------


def _from_xml(root: et.Element, tags: dict, attrs: dict, cls):
    if root is None:
        return None
    results = {}
    name = tags.pop(True, None)  # True is used as a key to ask for the tag
    if name:                     # If it is present, tag is mapped to <name>
        results[name] = root.tag
    for obj in root:
        if obj.tag in tags:
            cast_type, name, *_ = tags[obj.tag]
            if not isinstance(cast_type, type):
                tmp = cast_type(obj, {}, {})
            else:
                tmp = obj.text.strip() if obj.text else ""
                if not tmp:
                    text = obj.find("text")
                    if text is not None:
                        tmp = text.text
                if cast_type == bool:
                    tmp = tmp.lower() in ["true", "1", "t", ""]
                elif tmp or cast_type == str:
                    tmp = cast_type(tmp)
            if len(tags[obj.tag]) == 3 and tags[obj.tag][2]:
                if name not in results:
                    results[name] = []
                results[name].append(tmp)
            else:
                results[name] = tmp
                tags.pop(obj.tag)
    for key in tags:
        cast_type, name, *_ = tags[key]
        if cast_type == bool:  # Some tags act like False when missing
            results[name] = False
    if attrs:
        for key in attrs:
            cast_type, name = attrs[key]
            results[name] = root.get(key, None)
            if results[name] is not None:
                results[name] = cast_type(results[name])
    return cls(**results)


def _from_B64File(root: et.Element, tags: dict, attrs: dict):
    return B64File(root.get("name"), root.get("path"), root.text)


def _from_DatasetItems(root: et.Element, tags: dict, attrs: dict):
    data = {}
    for item in root:
        number = int(item.find("number").text)
        value = float(item.find("value").text)
        data[number] = value
    return data


def _from_Datasets(root: et.Element, tags: dict, *_):
    data = []
    for obj in root:
        tags["status"] = (Status, "status")
        tags["name"] = (str, "name")
        tags["type"] = (str, "ctype")
        tags["distribution"] = (Distribution, "distribution")
        tags["minimum"] = (str, "minimum")
        tags["maximum"] = (str, "maximum")
        tags["decimals"] = (str, "decimals")
        tags["dataset_items"] = (_from_DatasetItems, "items")
        data.append(_from_xml(obj, tags, None, Dataset))
    return data


def _from_FText(root: et.Element, tags: dict, attrs: dict):
    tags[True] = "name"
    tags["text"] = (str, "text")
    tags["file"] = (_from_B64File, "bfile", True)
    attrs["format"] = (TextFormat, "formatting")
    return _from_xml(root, tags, attrs, FText)


def _from_Hint(root: et.Element, tags: dict, attrs: dict) -> "Hint":
    tags["text"] = (str, "text")
    tags["options"] = (bool, "state_incorrect")
    tags["shownumcorrect"] = (bool, "show_correct")
    tags["clearwrong"] = (bool, "clear_wrong")
    attrs["format"] = (TextFormat, "formatting")
    return _from_xml(root, tags, attrs, Hint)


def _from_SelectOption(root: et.Element, tags: dict, attrs: dict):
    tags["text"] = (str, "text")
    tags["group"] = (str, "group")
    return _from_xml(root, tags, attrs, SelectOption)


def _from_Subquestion(root: et.Element, tags: dict, attrs: dict):
    attrs["format"] = (TextFormat, "formatting")
    tags["text"] = (str, "text")
    tags["answer"] = (str, "answer")
    return _from_xml(root, tags, attrs, Subquestion)


def _from_units(root: et.Element, *_) -> Unit:
    units = []
    for elem in root:
        unit = Unit(elem.find("unit_name").text, float(elem.find("multiplier").text))
        units.append(unit)
    return units


def _from_Tags(root: et.Element, *_) -> TList:
    _tags = TList(str)
    for elem in root:
        _tags.append(elem.text)
    return _tags


# -----------------------------------------------------------------------------


def _from_Answer(root: et.Element, tags: dict, attrs: dict, cls=None):
    tags["text"] = (str, "text")
    tags["feedback"] = (_from_FText, "feedback")
    attrs["format"] = (TextFormat, "formatting")
    attrs["fraction"] = (float, "fraction")
    return _from_xml(root, tags, attrs, cls if cls else Answer)


def _from_ANumerical(root: et.Element, tags: dict, attrs: dict, cls=None):
    tags["tolerance"] = (float, "tolerance")
    return _from_Answer(root, tags, attrs, cls if cls else ANumerical)


def _from_ACalculated(root: et.Element, tags: dict, attrs: dict):
    tags["tolerancetype"] = (TolType, "ttype")
    tags["correctanswerformat"] = (TolFormat, "aformat")
    tags["correctanswerlength"] = (int, "alength")
    return _from_ANumerical(root, tags, attrs, ACalculated)


def _from_dragtext(root: et.Element, tags: dict, attrs: dict):
    tags["text"] = (str, "text")
    tags["group"] = (str, "group")
    tags["unlimited"] = (bool, "unlimited")
    return _from_xml(root, tags, attrs, DragGroup)


def _from_dragitem(root: et.Element, tags: dict, attrs: dict):
    tags["no"] = (int, "number")
    tags["text"] = (str, "text")
    tags["infinite"] = (bool, "unlimited")
    tags["draggroup"] = (int, "group")
    tags["noofdrags"] = (bool, "no_of_drags")
    tags["file"] = (_from_B64File, "image")
    return _from_xml(root, tags, attrs, DragGroup)


def _from_dropzone(root: et.Element, *_):
    data = {a.tag: a for a in root}
    res = {}
    if "coords" in data and "shape" in data:
        res["shape"] = ShapeType(data["shape"].text)
        coords = data["coords"].text.split(";", 1)
        res["coord_x"], res["coord_y"] = map(int, coords[0].split(","))
        res["points"] = coords[1]
    elif "xleft" in data and "ytop" in data:
        res["coord_x"] = int(data["xleft"].text)
        res["coord_y"] = int(data["ytop"].text)
    else:
        raise AttributeError("One or more coordenates are missing")
    res["choice"] = int(data["choice"].text)
    res["number"] = int(data["no"].text)
    res["text"] = data["text"].text if "text" in data else None
    return DropZone(**res)


# -----------------------------------------------------------------------------


def _from_question(root: et.Element, tags: dict, attrs: dict, cls):
    tags["name"] = (str, "name")
    tags["questiontext"] = (_from_FText, "question")
    tags["generalfeedback"] = (_from_FText, "feedback")
    tags["defaultgrade"] = (float, "default_grade")
    tags["idnumber"] = (int, "dbid")
    tags["tags"] = (_from_Tags, "tags")
    return _from_xml(root, tags, attrs, cls)


def _from_question_mt(root: et.Element, tags: dict, attrs: dict, cls):
    tags["hint"] = (_from_Hint, "hints", True)
    tags["penalty"] = (float, "penalty")
    # Defintion of options reading should be done by children
    return _from_question(root, tags, attrs, cls)


def _from_question_mtcs(root: et.Element, tags: dict, attrs: dict, cls):
    tags["correctfeedback"] = (_from_FText, "if_correct")
    tags["partiallycorrectfeedback"] = (_from_FText, "if_incomplete")
    tags["incorrectfeedback"] = (_from_FText, "if_incorrect")
    tags["shownumcorrect"] = (bool, "show_num")
    tags["shuffleanswers"] = (bool, "shuffle")
    return _from_question_mt(root, tags, attrs, cls)


def _from_question_mtuh(root: et.Element, tags: dict, attrs: dict, cls):
    tags["unitgradingtype"] = (Grading, "grading_type")
    tags["unitpenalty"] = (str, "unit_penalty")
    tags["unitsleft"] = (bool, "left")
    tags["showunits"] = (ShowUnits, "show_unit")
    return _from_question_mt(root, tags, attrs, cls)


def _from_qcalculated(root: et.Element, tags: dict, attrs: dict, cls=None):
    tags["synchronize"] = (Synchronise, "synchronize")
    tags["units"] = (_from_units, "units", False)
    tags["dataset_definitions"] = (_from_Datasets, "datasets")
    tags["answer"] = (_from_ACalculated, "options", True)
    return _from_question_mtuh(root, tags, attrs, cls if cls else QCalculated)


def _from_qcalculatedsimple(root: et.Element, tags: dict, attrs: dict):
    return _from_qcalculated(root, tags, attrs, QCalculatedSimple)


def _from_qcalcmultichoice(root: et.Element, tags: dict, attrs: dict):
    tags["synchronize"] = (Synchronise, "synchronize")
    tags["single"] = (bool, "single")
    tags["answernumbering"] = (Numbering, "numbering")
    tags["dataset_definitions"] = (_from_Datasets, "datasets")
    tags["answer"] = (_from_ACalculated, "options", True)
    return _from_question_mtcs(root, tags, attrs, QCalculatedMultichoice)


def _from_qcloze(root: et.Element, tags: dict, attrs: dict):
    return _from_question_mt(root, tags, attrs, QCloze)


def _from_qdescription(root: et.Element, tags: dict, attrs: dict):
    return _from_question(root, tags, attrs, QDescription)


def _from_ddwtos(root: et.Element, tags: dict, attrs: dict):
    tags["dragbox"] = (_from_dragtext, "options", True)
    return _from_question_mtcs(root, tags, attrs, QDaDText)


def _from_ddimageortext(root: et.Element, tags: dict, attrs: dict):
    tags["file"] = (_from_B64File, "background")
    tags["drag"] = (_from_dragitem, "options", True)
    tags["drop"] = (_from_dropzone, "zones", True)
    return _from_question_mtcs(root, tags, attrs, QDaDImage)


def _from_ddmarker(root: et.Element, tags: dict, attrs: dict):
    tags["file"] = (_from_B64File, "background")
    tags["showmisplaced"] = (bool, "highlight")
    tags["drag"] = (_from_dragitem, "options", True)
    tags["drop"] = (_from_dropzone, "zones", True)
    return _from_question_mtcs(root, tags, attrs, QDaDMarker)


def _from_qessay(root: et.Element, tags: dict, attrs: dict):
    tags["responseformat"] = (RespFormat, "rsp_format")
    tags["responserequired"] = (bool, "rsp_required")
    tags["responsefieldlines"] = (int, "lines")
    tags["minwordlimit"] = (int, "min_words")
    tags["minwordlimit"] = (int, "max_words")
    tags["attachments"] = (int, "attachments")
    tags["attachmentsrequired"] = (bool, "atts_required")
    tags["maxbytes"] = (int, "max_bytes")
    tags["filetypeslist"] = (str, "file_types")
    tags["graderinfo"] = (_from_FText, "grader_info")
    tags["responsetemplate"] = (_from_FText, "template")
    return _from_question(root, tags, attrs, QEssay)


def _from_qmatching(root: et.Element, tags: dict, attrs: dict):
    tags["subquestion"] = (_from_Subquestion, "options", True)
    return _from_question_mtcs(root, tags, attrs, QMatching)


def _from_QRandomMatching(root: et.Element, tags: dict, attrs: dict):
    tags["choose"] = (int, "choose")
    tags["subcats"] = (bool, "subcats")
    return _from_question_mtcs(root, tags, attrs, QRandomMatching)


def _from_QMissingWord(root: et.Element, tags: dict, attrs: dict):
    tags["selectoption"] = (_from_SelectOption, "options", True)
    return _from_question_mtcs(root, tags, attrs, QMissingWord)


def _from_QMultichoice(root: et.Element, tags: dict, attrs: dict):
    tags["single"] = (bool, "single")
    tags["showstandardinstruction"] = (bool, "show_instr")
    tags["answernumbering"] = (Numbering, "numbering")
    tags["answer"] = (_from_Answer, "options", True)
    return _from_question_mtcs(root, tags, attrs, QMultichoice)


def _from_QNumerical(root: et.Element, tags: dict, attrs: dict):
    tags["answer"] = (_from_ANumerical, "options", True)
    tags["units"] = (_from_units, "units", False)
    return _from_question_mtuh(root, tags, attrs, QNumerical)


def _from_QShortAnswer(root: et.Element, tags: dict, attrs: dict):
    tags["usecase"] = (str, "use_case")
    tags["answer"] = (_from_Answer, "options", True)
    return _from_question_mt(root, tags, attrs, QShortAnswer)


def _from_QTrueFalse(root: et.Element, tags: dict, attrs: dict):
    tags["answer"] = (_from_Answer, "options", True)
    return _from_question(root, tags, attrs, QTrueFalse)


# -----------------------------------------------------------------------------


def _to_b64file(b64file) -> et.Element:
    bfile = et.Element("file", {"name": b64file.name, "encoding": "base64"})
    if b64file.path:
        bfile.set("path", b64file.path)
    bfile.text = b64file.bfile
    return bfile


def _to_dataset(dset) -> et.Element:
    dataset_def = et.Element("dataset_definition")
    status = et.SubElement(dataset_def, "status")
    et.SubElement(status, "text").text = dset.status.value
    name = et.SubElement(dataset_def, "name")
    et.SubElement(name, "text").text = dset.name
    et.SubElement(dataset_def, "type").text = dset.ctype
    distribution = et.SubElement(dataset_def, "distribution")
    et.SubElement(distribution, "text").text = dset.distribution.value
    minimum = et.SubElement(dataset_def, "minimum")
    et.SubElement(minimum, "text").text = dset.minimum
    maximum = et.SubElement(dataset_def, "maximum")
    et.SubElement(maximum, "text").text = dset.maximum
    decimals = et.SubElement(dataset_def, "decimals")
    et.SubElement(decimals, "text").text = dset.decimals
    et.SubElement(dataset_def, "itemcount").text = len(dset.items)
    dataset_items = et.SubElement(dataset_def, "dataset_items")
    for key, val in dset.items.items():
        item = et.Element("dataset_item")
        number = et.Element("number")
        number.text = key
        item.append(number)
        value = et.Element("value")
        value.text = val
        item.append(value)
        dataset_items.append(item)
    et.SubElement(dataset_def, "number_of_items").text = len(dset.items)
    return dataset_def


def _to_ftext(ftext: FText) -> None:
    elem = et.Element(ftext.name, {"format": ftext.formatting.value})
    txt = et.SubElement(elem, "text")
    txt.text = ftext.text
    for bfile in ftext.bfile:
        elem.append(_to_b64file(bfile))
    return elem


def _to_hint(hint: Hint) -> et.Element:
    elem = et.Element("hint", {"format": hint.formatting.value})
    txt = et.SubElement(elem, "text")
    txt.text = hint.text
    if hint.show_correct:
        et.SubElement(elem, "shownumcorrect")
    if hint.state_incorrect:
        et.SubElement(elem, "options")
    if hint.clear_wrong:
        et.SubElement(elem, "clearwrong")
    return elem


def _to_unit(unit: Unit) -> et.Element:
    elem = et.Element("units")
    et.SubElement(elem, "unit_name").text = unit.unit_name
    et.SubElement(elem, "multiplier").text = unit.multiplier
    return elem


def _to_tags(tags: TList) -> et.Element:
    tags = et.Element("tags")
    for item in tags:
        _tag = et.SubElement(tags, "tag")
        et.SubElement(_tag, "text").text = item
    return tags


def _to_answer(ans: Answer) -> et.Element:
    answer = et.Element("answer", {"fraction": ans.fraction})
    if ans.formatting:
        answer.set("format", ans.formatting.value)
    et.SubElement(answer, "text").text = ans.text
    if ans.feedback:
        answer.append(_to_ftext(ans.feedback))
    return answer


def _to_anumerical(ans) -> et.Element:
    answer = _to_answer(ans)
    et.SubElement(answer, "tolerance").text = ans.tolerance
    return answer


def _to_acalculated(ans) -> et.Element:
    answer = _to_anumerical(ans)
    et.SubElement(answer, "tolerancetype").text = ans.ttype.value
    et.SubElement(answer, "correctanswerformat").text = ans.aformat.value
    et.SubElement(answer, "correctanswerlength").text = ans.alength
    return answer


def _to_dragtext(drag) -> et.Element:
    dragbox = et.Element("dragbox")
    et.SubElement(dragbox, "text").text = drag.text
    et.SubElement(dragbox, "group").text = str(drag.group)
    if drag.unlimited:
        et.SubElement(dragbox, "infinite")
    return dragbox


def _to_dragitem(drag) -> et.Element:
    dragitem = et.Element("drag")
    et.SubElement(dragitem, "no").text = drag.number
    et.SubElement(dragitem, "text").text = drag.text
    if drag.group:
        et.SubElement(dragitem, "draggroup").text = drag.group
    if drag.unlimited:
        et.SubElement(dragitem, "infinite")
    if drag.no_of_drags:
        et.SubElement(dragitem, "noofdrags").text = drag.no_of_drags
    if drag.image:
        dragitem.append(_to_b64file(drag.image))
    return dragitem


def _to_dropzone(drop) -> et.Element:
    dropzone = et.Element("drop")
    if drop.text:
        et.SubElement(dropzone, "text").text = drop.text
    et.SubElement(dropzone, "no").text = str(drop.number)
    et.SubElement(dropzone, "choice").text = str(drop.choice)
    if drop.shape:
        et.SubElement(dropzone, "shape").text = drop.shape.value
    if not drop.points:
        et.SubElement(dropzone, "xleft").text = str(drop.coord_x)
        et.SubElement(dropzone, "ytop").text = str(drop.coord_y)
    else:
        _tmp = et.SubElement(dropzone, "coords")
        _tmp.text = f"{drop.coord_x},{drop.coord_y};{drop.points}"
    return dropzone


def _to_subquestion(sub) -> et.Element:
    subquestion = et.Element("subquestion",
                            {"format": sub.formatting.value})
    text = et.Element("text")
    text.text = sub.text
    subquestion.append(text)
    answer = et.Element("answer")
    subquestion.append(answer)
    text = et.Element("text")
    text.text = sub.answer
    answer.append(text)
    return subquestion


def _to_selectOption(opt) -> et.Element:
    select_option = et.Element("selectoption")
    text = et.Element("text")
    text.text = opt.text
    select_option.append(text)
    group = et.Element("group")
    group.text = str(opt.group)
    select_option.append(group)
    return select_option


def _to_question(question) -> et.Element:
    elem = et.Element("question", {"type": question.MOODLE})
    name = et.SubElement(elem, "name")
    et.SubElement(name, "text").text = question.name
    elem.append(_to_ftext(question.question))
    if question.feedback:
        elem.append(_to_ftext(question.feedback))
    et.SubElement(elem, "defaultgrade").text = question.default_grade
    # et.SubElement(question, "hidden").text = "0"
    if question.dbid is not None:
        et.SubElement(elem, "idnumber").text = question.dbid
    if question.tags:
        elem.append(_to_tags(question.tags))
    return elem


def _to_question_mt(qst, opt_callback) -> et.Element:
    question = _to_question(qst)
    for hint in qst.hints:
        question.append(_to_hint(hint))
    et.SubElement(question, "penalty").text = str(qst.penalty)
    if opt_callback:  # Workaround for QRandomMatching.
        for sub in qst.options:
            question.append(opt_callback(sub))
    return question


def _to_question_mtcs(qst, opt_callback) -> et.Element:
    question = _to_question_mt(qst, opt_callback)
    question.append(_to_ftext(qst.if_correct))
    question.append(_to_ftext(qst.if_incomplete))
    question.append(_to_ftext(qst.if_incorrect))
    if qst.show_num:
        et.SubElement(question, "shownumcorrect")
    if hasattr(qst, "shuffle") and qst.shuffle:    # Workaround for
        et.SubElement(question, "shuffleanswers")   # QRandomMatching
    return question


def _to_question_mtuh(qst, opt_callback) -> et.Element:
    question = _to_question_mt(qst, opt_callback)
    et.SubElement(question, "unitgradingtype").text = qst.grading_type.value
    et.SubElement(question, "unitpenalty").text = qst.unit_penalty
    et.SubElement(question, "showunits").text = qst.show_unit.value
    et.SubElement(question, "unitsleft").text = qst.left
    return question


def _to_qcalculated(qst: QCalculated) -> et.Element:
    question = _to_question_mtuh(qst, _to_acalculated)
    et.SubElement(question, "synchronize").text = qst.synchronize.value
    units = et.SubElement(question, "units")
    for unit in qst.units:
        units.append(_to_unit(unit))
    definitions = et.SubElement(question, "dataset_definitions")
    for dataset in qst.datasets:
        definitions.append(_to_dataset(dataset))
    return question


def _to_qcalcmultichoice(qst: QCalculatedMultichoice) -> et.Element:
    question = _to_question_mtcs(qst, _to_acalculated)
    et.SubElement(question, "synchronize").text = qst.synchronize.value
    if qst.single:
        et.SubElement(question, "single")
    et.SubElement(question, "answernumbering").text = qst.numbering.value
    dataset_definitions = et.SubElement(question, "dataset_definitions")
    for dataset in qst.datasets:
        dataset_definitions.append(_to_dataset(dataset))
    return question


def _to_qcloze(qst: QCloze) -> et.Element:
    tmp = qst.question.text
    qst.question.text = qst.pure_text()
    question = _to_question_mt(qst, None)
    qst.question.text = tmp
    return question


def _to_qdescription(qst: QDescription) -> et.Element:
    return _to_question(qst)


def _to_qdad_text(qst) -> et.Element:
    return _to_question_mtcs(qst, _to_dragtext)


def _to_qdad_image(qst) -> et.Element:
    question = _to_question_mtcs(qst, _to_dragitem)
    if qst.background:
        question.append(_to_b64file(qst.background))
    for dropzone in qst.zones:
        question.append(_to_dropzone(dropzone))
    return question


def _to_qdad_marker(qst: QDaDMarker) -> et.Element:
    question = _to_question_mtcs(qst, _to_dragitem)
    if qst.highlight:
        et.SubElement(question, "showmisplaced")
    for dropzone in qst.zones:
        question.append(_to_dropzone(dropzone))
    if qst.background:
        question.append(_to_b64file(qst.background))
    return question


def _to_qessay(qst) -> et.Element:
    question = _to_question(qst)
    et.SubElement(question, "responseformat").text = qst.rsp_format.value
    if qst.rsp_required:
        et.SubElement(question, "responserequired")
    et.SubElement(question, "responsefieldlines").text = qst.lines
    et.SubElement(question, "attachments").text = qst.attachments
    if qst.atts_required:
        et.SubElement(question, "attachmentsrequired")
    if qst.max_bytes:
        et.SubElement(question, "maxbytes").text = qst.max_bytes
    if qst.file_types:
        et.SubElement(question, "filetypeslist").text = qst.file_types
    if qst.grader_info:
        question.append(_to_ftext(qst.grader_info))
    if qst.template:
        question.append(_to_ftext(qst.template))
    return question


def _to_qmatching(qst) -> et.Element:
    return _to_question_mtcs(qst, _to_subquestion)


def _to_qrandommatching(qst) -> et.Element:
    question = _to_question_mtcs(qst, None)
    et.SubElement(question, "choose").text = qst.choose
    et.SubElement(question, "subcats").text = qst.subcats
    return question


def _to_qmissingword(qst) -> et.Element:
    return _to_question_mtcs(qst, _to_selectOption)


def _to_qmultichoice(qst) -> et.Element:
    question = _to_question_mtcs(qst, _to_answer)
    et.SubElement(question, "answernumbering").text = qst.numbering.value
    if qst.single:
        et.SubElement(question, "single")
    return question


def _to_qnumerical(qst: QNumerical) -> et.Element:
    question = _to_question_mtuh(qst, _to_anumerical)
    if len(qst.units) > 0:
        units = et.SubElement(question, "units")
        for unit in qst.units:
            units.append(_to_unit(unit))
    return question


def _to_qshortanswer(qst) -> et.Element:
    question = _to_question_mt(qst, _to_answer)
    et.SubElement(question, "usecase").text = qst.use_case
    return question


def _to_qtruefalse(qst) -> et.Element:
    question = _to_question(qst)
    question.append(_to_answer(qst.true))
    question.append(_to_answer(qst.false))
    return question


# -----------------------------------------------------------------------------


_QTYPE = {
    "calculated": (_from_qcalculated, _to_qcalculated), 
    "calculatedsimple": (_from_qcalculatedsimple, _to_qcalculated),
    "calculatedmulti": (_from_qcalcmultichoice, _to_qcalcmultichoice),
    "cloze": (_from_qcloze, _to_qcloze),
    "description": (_from_qdescription, _to_qdescription),
    "ddwtos": (_from_ddwtos, _to_qdad_text),
    "ddimageortext": (_from_ddimageortext, _to_qdad_image),
    "ddmarker": (_from_ddmarker, _to_qdad_marker),
    "essay": (_from_qessay, _to_qessay),
    "matching": (_from_qmatching, _to_qmatching),
    "randomsamatch": (_from_QRandomMatching, _to_qrandommatching),
    "gapselect": (_from_QMissingWord, _to_qmissingword),
    "multichoice": (_from_QMultichoice, _to_qmultichoice),
    "numerical": (_from_QNumerical, _to_qnumerical),
    "shortanswer" : (_from_QShortAnswer, _to_qshortanswer),
    "truefalse": (_from_QTrueFalse, _to_qtruefalse)
}


def read_moodle(cls, file_path: str, category: str = None) -> "Category":
    """[summary]

    Returns:
        [type]: [description]
    """
    data_root = et.parse(file_path)
    top_quiz = cls(category)
    quiz = top_quiz
    for elem in data_root.getroot():
        if elem.tag != "question":
            continue
        if elem.get("type") == "category":
            quiz = gen_hier(cls, top_quiz, elem[0][0].text)
        elif elem.get("type") not in _QTYPE:
            raise TypeError(f"Type {elem.get('type')} not implemented")
        else:
            question = _QTYPE[elem.get("type")][0](elem, {}, {})
            quiz.add_question(question)
    return top_quiz


# -----------------------------------------------------------------------------


def write_moodle(self: "Category", file_path: str, pretty=False):
    """Generates XML compatible with Moodle and saves to a file.

    Args:
        file_path (str): filename where the XML will be saved
        pretty (bool): saves XML pretty printed.
    """
    def _txrecursive(cat: "Category", root: et.Element):
        question = et.Element("question")           # Add category on the top
        if cat.get_size() > 0:
            question.set("type", "category")
            category = et.SubElement(question, "category")
            catname = [cat.name]
            tmp = cat.parent
            while tmp:
                catname.append(tmp.name)
                tmp = tmp.parent
            catname.reverse()
            et.SubElement(category, "text").text = "/".join(catname)
            root.append(question)
            for question in cat.questions:          # Add own questions first
                root.append(_QTYPE[question.MOODLE][1](question))
        for name in cat:                            # Then add children data
            _txrecursive(cat[name], root)
    root = et.Element("quiz")
    _txrecursive(self, root)
    with open(file_path, "w") as ofile:
        ofile.write("<?xml version='1.0' encoding='utf-8'?>\n")
        serialize_fxml(ofile.write, root, True, pretty)