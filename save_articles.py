import urllib.request
import ssl
import certifi
from html.parser import HTMLParser
import time
import random
import os
import logging

# URL to scrape
TARGET_URL = 'https://www.freethink.com/articles'

# Set up a logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Class to parse links to get the top 50 articles
class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    
    # A link tag begins, get the link from it
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

# A function to use the link parser to generate a list of links
def gather_links(url):
    # Set up headers and context for request
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    context = ssl.create_default_context(cafile=certifi.where())
    # Make the request and get the response
    req = urllib.request.Request(url, headers=headers)
    try:
        response = urllib.request.urlopen(req, context=context)
        web_content = response.read().decode('utf-8')
        # Gather the info from the web page generated
        parser = LinkParser()
        parser.feed(web_content)
        logger.info(f"Gathered links successfully")
        return parser.links
    except Exception as e:
        # Log the exception and continue on when we fail to gather the links
        logger.error(f"Failed to gather links on {url}: {str(e)}")

# Elements that we don't care about when tracking level in embedded elements
VOID_ELEMENTS = {'br', 'img', 'iframe', 'input', 'meta', 'link', 'hr', 'embed'}

# A class to parse an atricle from a web page
class ArticleParser(HTMLParser):
    # Initialize variables to store an article and flag variables to keep track of what tag we're in
    def __init__(self):
        super().__init__()
        self.title = ""
        self.content = []
        self.author = ""
        self.date = ""
        self.current_para = []
        
        self.in_title = False
        self.in_author = False
        self.in_date = False

        self.in_para = False
        self.in_header = False
        
        self.in_quote = False
        self.in_cite = False

        self.in_image = False
        self.in_tweet_container = False

    # A tag begins
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        # Figure out what type of div it is - tweet, header, author link, quote,or paragraph
        # Set flags accordingly
        if tag == 'div' and 'class' in attrs_dict and 'twitter-tweet' in attrs_dict.get('class', ''):
            self.in_tweet_container = True
            self.tweet_depth = 1
            return
        elif self.in_tweet_container:
            if tag not in VOID_ELEMENTS:
                self.tweet_depth += 1
        
        if tag == 'h1':
            self.in_title = True
        if tag == 'h2' or tag == 'h3':
            self.in_header = True
        elif tag == 'a' and 'class' in attrs_dict and '/people/' in attrs_dict['href']:
            self.in_author = True
        elif tag == 'time' and 'datetime' in attrs_dict:
            date = attrs_dict['datetime']
            self.date = date.split('T')[0] 
        elif tag == 'p' and self.in_quote:
            self.in_quote_quote = True
        elif tag == 'cite' and self.in_quote:
            self.in_cite = True

        elif tag == 'p':
            self.in_para = True
            self.current_para = []

        elif tag == 'img' and 'src' in attrs_dict and 'alt' in attrs_dict:
            # Images without an alt are not part of article
            if attrs_dict['alt'] != '':     
                src = attrs_dict['src']
                alt = attrs_dict.get('alt', 'Image')
                # Changed image display format as requested
                self.content.append(f"Image here, Source: {src}, Alt Text: {alt}")
    
    # Set the correct flag variable to False
    def handle_endtag(self, tag):
        if self.in_tweet_container:
            self.tweet_depth -= 1
            if self.tweet_depth == 0:
                self.in_tweet_container = False
        
        if tag == 'h1' and self.in_title:
            self.in_title = False
        elif (tag == 'h2' or tag == 'h3') and self.in_header:
            self.in_header = False
        elif tag == 'p' and self.in_para:
            self.in_para = False
            if self.current_para:
                full_para = ' '.join(self.current_para)
                self.content.append(full_para)
            self.current_para = []

        elif tag == 'a' and self.in_author:
            self.in_author = False
        elif tag == 'blockquote':
            self.in_quote = False
            self.in_quote_quote = False
            self.in_cite = False
        elif tag == 'img':
            self.in_image = False
    
    # Now that we're in the tag, get the data tag and parse according to flag variable
    def handle_data(self, data):
        if self.in_tweet_container: return
        elif self.in_title:
            self.title += data.strip()
        elif self.in_para:
            text = data.strip()
            if text.startswith('https:') or text.startswith('pic.twitter'): pass
            elif text:
                self.current_para.append(text)
        elif self.in_header:
            text = data.strip()
            if text.startswith('https:') or text.startswith('pic.twitter'): pass
            else:
                self.content.append('__HEADER_MARKER__') 
                self.content.append(text)
                self.content.append(f"{'-' * len(text)}")
        elif self.in_author:
            self.author = data.strip()
        elif self.in_cite:
            if self.content and isinstance(self.content[-1], str) and self.content[-1].startswith(">"):
                clean_quote = self.content[-1].split(' - ')[0]
                self.content[-1] = f"{clean_quote} - {data.strip()}"
            else:
                return

def clean_content(article):
    content = article.get('content', [])
    clean_content = []
    current_paragraph = []

    # Define prefixes that indicate special content types

    for line in content:
        line = line.strip()

        if line == '__HEADER_MARKER__':
            if current_paragraph:
                clean_content.append('\n'.join(current_paragraph))
                current_paragraph = []
            clean_content.append('__HEADER_MARKER__')
            continue

        if not line:
            continue
        if current_paragraph:
            # Check if the line starts with punctuation that connects it to the previous sentence
            if line[0] in ('.', ',', ';', ':', ')', '!', '?'):
                current_paragraph[-1] += line
            else:
                current_paragraph.append(line)
        else:
            current_paragraph.append(line)

    # Add any remaining paragraph
    if current_paragraph:
        clean_content.append('\n'.join(current_paragraph))

    article['content'] = clean_content
    return article

    
# Function to utilize ArticleParser to parse an article from each link provided
def parse_articles(links):
    for url in links:
        headers = {
            'User-Agent': 'Mozilla/5.0'
        }
        context = ssl.create_default_context(cafile=certifi.where())
        req = urllib.request.Request(url, headers=headers)

        # Utilize try catch block to continute despite errors
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
            logger.info(f'Successfully parsed {url}')
            article = clean_content(article)
            save_article(article)
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {str(e)}")
            continue
        # Wait for a random interval to be a polite parser
        t = random.uniform(0.5, 3.0)
        time.sleep(t)
        

def save_article(article, output_dir="articles"):
    # Make the directory if it doesn't already exist
    os.makedirs(output_dir, exist_ok=True)
    # Generate a filename and filepath
    filename = f"{article['title'][:50]}_{article['date']}.txt".replace(' ', '_')
    filepath = os.path.join(output_dir, filename)
    
    # Open the file
    with open(filepath, 'w') as f:
        # Write the title, author, publishing date, then each line in contents
        f.write(f'{article['title']}\n')
        logger.info(f'Written by {article['author']}, Published on {article['date']}')
        f.write(f'Written by {article['author']}, Published on {article['date']}\n\n\n')
        for line in article['content']:
            if line == '__HEADER_MARKER__':
                f.write('\n')
            else:
                f.write(f'{line}\n')
        f.close()

# Get the links and gather the articles
extracted_links = gather_links(TARGET_URL)
parse_articles(extracted_links)

