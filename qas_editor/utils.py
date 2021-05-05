def get_txt(data: dict, key: str, default=None) -> str:
    if key not in data:
        return default
    return data[key].text

def extract(data: dict, key: str, res: dict, name: str, cast_type) -> None:
    if key in data:
        try:
            if cast_type == bool:
                res[name] = data[key].text.lower() in ["true", "1", "t"]
            elif cast_type != str:
                res[name] = cast_type(data[key].text)
            else:
                res[name] = data[key].text
        except:
             res[name] = data[key].text


def cdata_str(text: str):
    return f"<![CDATA[{text}]]>" if text else ""
