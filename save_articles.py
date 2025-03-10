import urllib.request
import ssl
import certifi
from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = None
            is_target_class = False
            for attr_name, attr_value in attrs:
                if attr_name == 'href':
                    href = attr_value
                if attr_name == 'class' and attr_value == "block mb-4 text-2xl text-black loop-item__title font-happy hover:text-black focus:text-black hover:underline focus:underline":
                    is_target_class = True
            if href and is_target_class:
                if len(self.links) < 50:
                    self.links.append(href)


def gather_links(url):
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    context = ssl._create_unverified_context()
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, context=context) as response:
            web_content = response.read().decode('utf-8')
            parser = MyHTMLParser()
            parser.feed(web_content)
            return parser.links
    except Exception as e:
        print("Error fetching URL:", e)
    

url = 'https://www.freethink.com/articles'

extracted_links = gather_links(url)

print (f"This is the top {len(extracted_links)} total article links:")
for link in extracted_links:
    print(link)

