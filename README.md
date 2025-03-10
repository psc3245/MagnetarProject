# MagnetarProject

## How it all went down:

### First Push - Scraping Article Links
1. Read online and considered many approaches to this problem.
2. Elected to use python due to having a good way to make an http request and also a good way to talk to the system to write files
3. Read https://www.freethink.com/robots.txt and researched if this website was scraping friendly. This website is, as all user-agents are allowed and no files are disallowed.
4. Poked through the website to find a page that had a lot of articles, which was https://www.freethink.com/articles (shocker)
5. Landed on a strategy, utilizing the class attribute shared by every link, and began writing code to parse the top 50 links
6. Started researching HTML parsing in python, landed on using a library called html.parser that allowed me to overwrite methods in their class, HTMLParser
7. Used postman to make a get request and gather some html to ensure the code worked
8. Began researching how to make an http request in python
9. Found urllib.request to make a request and get the whole webpage as a response
10. Ran into a problem of not being certified. Tried simply adding headers to act like I was firefox but that did not work either. Ended up finding a library called certifi to set up a fake ssl context. 
11. Successfully got the webpage with the request and passed it to the parser
12. Expanded parser class to have a member variable to keep track of links
13. Tested code and successfully gathered links from the website. Limited size to 50. Tested code again and ensured I had successfully collected the top 50 links off freethink.

