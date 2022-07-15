from html.parser import HTMLParser
from xml.etree import ElementTree as et
from io import StringIO

class HTMLTest(HTMLParser):
    def handle_starttag(self, tag, attrs):
        print("Encountered a start tag:", tag, attrs)

    def handle_endtag(self, tag):
        print("Encountered an end tag :", tag)

    def handle_data(self, data):
        print("Encountered some data  :", data)

# def process_string(in_string):
#     """Scan a string for LaTeX equations, image tags, etc, and process them.
#     """
#     #Process img tags
#     pattern = re.compile(r"<img.*?>")

#     def img_src_processor(img_txt, html_mode):
#         img_tag = html.fragment_fromstring(img_txt)
#         xid, path = ("10001", "something")
#         if html_mode:
#             img_tag.attrib['src'] = path
#         else:
#             img_tag.attrib['src'] = '@X@EmbeddedFile.requestUrlStub@X@bbcswebdav/xid-'+xid
#         return html.tostring(img_tag).decode('utf-8')

#     html_string = pattern.sub(lambda match : img_src_processor(match.group(0), True), in_string)
#     in_string = pattern.sub(lambda match : img_src_processor(match.group(0), False), in_string)
#     return in_string, html_string

def process_string_2(in_string):
    """Scan a string for LaTeX equations, image tags, etc, and process them.
    """
    #Process img tags
    et.parse(StringIO(in_string), HTMLTest())
    return in_string