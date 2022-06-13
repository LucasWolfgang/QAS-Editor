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
from io import BytesIO
from PIL import Image
import base64

PDF_IMAGE_FILTER = {"/DCTDecode": "jpg",  "/JPXDecode": "jp2",
                        "/CCITTFaxDecode": "tiff", "/FlateDecode": "png" }
PDF_IMAGE_CHANNEL = {"DeviceGray": "L",    # 8-bit pixels, black and white
                        "DeviceRGB": "RGB",   # 3x8-bit pixels, true color
                        "DeviceCMYK": "CMYK", # 4x8-bit pixels, color separation
                        "/DeviceN": "P", 
                        "/Indexed": "P"
                        }

def extract_pdf_images(file_path, page, external_refs: bool):
    images = {}
    rsc = page['/Resources']
    path = file_path.rsplit('.',1)[0]
    if '/XObject' in rsc:
        for xobj in rsc['/XObject'].values():
            if xobj['/Subtype'] != '/Image':
                continue
            # Getting image
            size = (xobj['/Width'], xobj['/Height'])
            data = xobj.read_from_stream()
            color_space = xobj['/ColorSpace'][0]
            mode = PDF_IMAGE_FILTER[color_space]
            if color_space == "/Indexed":
                psize = int(xobj['/ColorSpace'][2])
                palette = [255-int(n*psize/255) for n in \
                            range(256) for _ in range(3)]
            else:
                palette = None
            xformat = PDF_IMAGE_FILTER.get(xobj['/Filter'], "png")
            if palette:
                img.putpalette(palette)
            try:
                img = Image.frombytes(mode, size, data)
                END = f"width={size[0]} height={size[1]}>"
                if external_refs:
                    name = f"{path}_{xobj.idnum}.{xformat}"
                    img.save(name)
                    url = f"<img src={name} {END}"
                else:
                    buffer = BytesIO()
                    img.save(buffer, format=xformat)
                    img_str = base64.b64encode(buffer.getvalue())
                    url = f"<file src={name} {END}{img_str}</file>"
                images[xobj.idnum] = url
            except Exception:
                pass
            finally:
                img.close()
    return images


# -----------------------------------------------------------------------------


def read_pdf(cls, file_path: str):
    """_summary_

    Args:
        file_path (str): _description_
        ptitle (str, optional): _description_.

    Returns:
        Quiz: _description_
    """
    # TODO
    raise NotImplementedError("PDF not implemented")
    # with open(file_path, "rb") as infile:
    #     pdf_file = PdfReader(infile)
    #     for page in pdf_file.pages:
    #         # It is still not the best, but it is improving!!
    #         text = page.extract_text()


def write_pdf(self, file_path: str):
    """_summary_

    Args:
        file_path (str): _description_

    Raises:
        NotImplementedError: _description_
    """
    # TODO
    raise NotImplementedError("PDF not implemented")