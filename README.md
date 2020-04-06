# Ycrawler
Ycrawler is autamatically download top stories from **news.ycombinator.com** with pages referenced in
comments using [Hacker News API](https://github.com/HackerNews/API).

Collected web pages located in own directories grouped by article.

List of articles saves in ```list.txt```. 

## Requirements
* Python 3.7+
* [aiohttp](https://docs.aiohttp.org/en/stable/)

## Usage
```
usage: main.py [-h] [--period PERIOD] [--limit LIMIT] [--verbose]
               [--path PATH]

Download top stories from news.ycombinator.com with pages referenced in
comments using Hacker News API.

optional arguments:
  -h, --help       show this help message and exit
  --period PERIOD  Number of seconds between poll
  --limit LIMIT    Number of new stories to download
  --verbose        Detailed output
  --path PATH      Folder to collect stories
  --connections_limit CONNECTIONS_LIMIT
                        The limit for simultaneous connections

  ```
