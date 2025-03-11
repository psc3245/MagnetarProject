import urllib.request
import ssl
import certifi
from html.parser import HTMLParser
import time
import json
import random
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class LinkParser(HTMLParser):
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
    context = ssl.create_default_context(cafile=certifi.where())
    req = urllib.request.Request(url, headers=headers)
    try:
        response = urllib.request.urlopen(req, context=context)
        web_content = response.read().decode('utf-8')
        parser = LinkParser()
        parser.feed(web_content)
        logger.info(f"Gathered links successfully")
        return parser.links
    except Exception as e:
        logger.error(f"Failed to gather links on {url}: {str(e)}")
        return []

VOID_ELEMENTS = {'br', 'img', 'iframe', 'input', 'meta', 'link', 'hr', 'embed'}


class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.content = []
        self.author = ""
        self.date = ""
        self.categories = []
        
        self.in_title = False
        self.in_author = False
        self.in_date = False

        self.in_para = False
        
        self.in_quote = False
        self.in_cite = False

        self.in_image = False
        self.in_tweet_container = False
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == 'div' and 'class' in attrs_dict and 'twitter-tweet' in attrs_dict['class']:
            self.in_tweet_container = True
            self.tweet_depth = 1
            return
        elif self.in_tweet_container:
            if tag not in VOID_ELEMENTS:
                self.tweet_depth += 1
        
        if tag == 'h1':
            self.in_title = True
        elif tag == 'a' and 'class' in attrs_dict and '/people/' in attrs_dict['href']:
            self.in_author = True
        elif tag == 'time' and 'datetime' in attrs_dict:
            date = attrs_dict['datetime']
            self.date = date.split('T')[0] 

        elif 'class' in attrs_dict and attrs_dict['class'] == 'class-related__item-link':
            href = attrs_dict['class']
            arr = href.split('/')
            self.categories.append(arr[-1])
        elif tag == 'p' and self.in_quote:
            self.in_quote_quote = True
        elif tag == 'cite' and self.in_quote:
            self.in_cite = True

        elif tag == 'p':
            self.in_para = True
    
    def handle_endtag(self, tag):
        if self.in_tweet_container:
            self.tweet_depth -= 1
            if self.tweet_depth == 0:
                self.in_tweet_container = False
        
        if tag == 'h1' and self.in_title:
            self.in_title = False
        elif tag == 'p' and self.in_para:
            self.in_para = False
        elif tag == 'a' and self.in_author:
            self.in_author = False
        elif tag == 'blockquote':
            self.in_quote = False
            self.in_quote_quote = False
            self.in_cite = False
    
    def handle_data(self, data):
        if self.in_tweet_container: return
        if self.in_title:
            self.title += data.strip()
        if self.in_para:
            text = data.strip()
            if text:
                self.content.append(text)
        if self.in_author:
            self.author = data.strip()
        if self.in_cite:
            if self.content and isinstance(self.content[-1], str) and self.content[-1].startswith(">"):
                clean_quote = self.content[-1].split(' - ')[0]
                self.content[-1] = f"{clean_quote} - {data.strip()}"
            else:
                return
        
def parse_articles(links):
    articles = []
    for url in links:
        headers = {
            'User-Agent': 'Mozilla/5.0'
        }
        context = ssl.create_default_context(cafile=certifi.where())
        req = urllib.request.Request(url, headers=headers)

        try:
            response = urllib.request.urlopen(req, context=context)
            web_content = response.read().decode('utf-8')
            parser = ArticleParser()
            parser.feed(web_content)
            article = {
                "title": parser.title,
                "author" : parser.author,
                "date" : parser.date,
                "content" : parser.content,
            }
            articles.append(article)
            logger.info(f'Successfully parsed {url}')
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {str(e)}")
            continue
        # wait for a random interval to be a polite parser
        t = random.uniform(0.5, 3.0)
        time.sleep(t)

    for article in articles:
        save_article(article)

def save_article(article, output_dir="articles"):
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{article['date']}_{article['title'][:50]}.json".replace(' ','_')
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump({
            'title': article['title'],
            'author': article['author'],
            'date': article['date'],
            'content': article['content']
        }, f, indent=2)

url = 'https://www.freethink.com/articles'

extracted_links = gather_links(url)

parse_articles(extracted_links)

