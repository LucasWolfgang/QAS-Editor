def get_txt(data: dict, key: str, default=None) -> str:
    if key not in data:
        return default
    return data[key].text

def cdata_str(text: str):
    return f"<![CDATA[{text}]]>" if text else ""
