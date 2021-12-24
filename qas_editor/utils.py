from typing import cast


def extract(data: dict, key: str, res: dict, name: str, cast_type) -> None:
    if key in data:
        if cast_type == str:
            res[name] = data[key].text
        elif cast_type != bool:
            res[name] = data[key].text
            if res[name]: res[name] = cast_type(res[name])
        else:
            if data[key].text:
                res[name] = data[key].text.lower() in ["true", "1", "t"]
            else:
                res[name] = True
    elif cast_type == bool:
        res[name] = False


def cdata_str(text: str):
    return f"<![CDATA[{text}]]>" if text else ""

def conf_logger():
    import logging
    import os
    log = logging.getLogger("qas_editor")
    log.setLevel(logging.DEBUG)
    fhandler = logging.FileHandler(filename=f"{os.environ['USERPROFILE']}/qas_editor.log",
                                mode="w", encoding="utf-8")
    fhandler.setFormatter(logging.Formatter("%(levelname)s [%(asctime)s]: %(message)s"))
    fhandler.setLevel(logging.DEBUG)
    log.addHandler(fhandler)

from PyPDF2.generic import IndirectObject
def quick_print(data, pp):
    """This is a temporary function that I am using to test PDF import/export
    """
    if isinstance(data, dict):
        for i in data:
            print(f"{pp}{i}:")
            quick_print(data[i], pp+"  ")
    elif isinstance(data, list):
        for i in data:
            quick_print(i, pp+"  ")
    elif isinstance(data, IndirectObject):
        quick_print(data.getObject(), pp+"  ")
    else:
        print(pp, data)