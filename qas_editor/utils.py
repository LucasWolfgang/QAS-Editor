def extract(data: dict, key: str, res: dict, name: str, cast_type) -> None:
    if key in data:
        try:
            if cast_type == str:
                res[name] = data[key].text
            elif cast_type == bool:
                if data[key].text:
                    res[name] = data[key].text.lower() in ["true", "1", "t"]
                else:
                    res[name] = True
            else:
                res[name] = cast_type(data[key].text)
        except:
            res[name] = data[key].text
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