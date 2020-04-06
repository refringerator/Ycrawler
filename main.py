import os
import asyncio
import argparse
import logging
import aiohttp
import async_timeout
import html
import re
from datetime import datetime

LOGGER_FORMAT = '%(asctime)s %(message)s'
URL_TEMPLATE = "https://hacker-news.firebaseio.com/v0/item/{}.json"
STORY_TEMPLATE = 'https://news.ycombinator.com/item?id={}'
TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
FETCH_TIMEOUT = 10
CHUNK_SIZE = 1024
REG_EXP = r'<a[^>]* href="([^"]*)"'
DOWNLOADED_STORIES = []
CONTENT_FILE = 'list.txt'

parser = argparse.ArgumentParser(
    description='Download top stories from news.ycombinator.com \
    with pages referenced in comments using Hacker News API.')
parser.add_argument('--period', type=int, default=30, help='Number of seconds between poll')
parser.add_argument('--limit', type=int, default=30, help='Number of new stories to download')
parser.add_argument('--verbose', action='store_true', help='Detailed output')
parser.add_argument('--path', type=str, default='./stories', help='Folder to collect stories')
parser.add_argument('--connections_limit', type=int, default=3, help='The limit for simultaneous connections')

logging.basicConfig(format=LOGGER_FORMAT, datefmt='[%H:%M:%S]')
log = logging.getLogger()
log.setLevel(logging.INFO)


class URLFetcher:
    """Provides counting of URL fetches for a particular task.
    """

    def __init__(self):
        self.fetch_counter = 0

    async def fetch(self, session, url, just_json=True, dest_dir=''):
        """Fetch a URL using aiohttp returning parsed JSON response or saving to file.
        As suggested by the aiohttp docs we reuse the session.
        """
        with async_timeout.timeout(FETCH_TIMEOUT):
            self.fetch_counter += 1
            try:
                async with session.get(url) as response:
                    if just_json:
                        log.debug('Response status {} on {}'.format(response.status, url))
                        return await response.json()
                    else:
                        write_to_disk(await response.read(), url, dest_dir)

            except asyncio.TimeoutError:
                log.error('Timeout error on url: {}'.format(url))


def write_to_disk(resp_bytes, url, dest_dir):
    if resp_bytes is None:
        log.debug('Nothing to save: {}'.format(url))
        return
    basename = os.path.basename(url)
    filename = basename if basename else url.replace('/', '-').replace('.', '_')
    full_filename = os.path.join(dest_dir, filename[:30])
    with open(full_filename, 'wb') as f:
        f.write(resp_bytes)


def get_dir_name_for_story(dest_dir, title, story_id, url):
    basename = os.path.basename(url)
    dir_name = ''.join([str(story_id), ' ', str(basename if basename else title)[:25]])
    path = os.path.join(dest_dir, dir_name)
    if not os.path.exists(path):
        create_dir_and_add_to_list(dest_dir, path, title, story_id, url)

    return path


def create_dir_and_add_to_list(dest_dir, path, title, story_id, url):
    os.makedirs(path)
    DOWNLOADED_STORIES.append(story_id)
    with open(os.path.join(dest_dir, CONTENT_FILE), 'at') as f:
        f.write('\t'.join([str(story_id), title, url]) + '\n')


def find_refs_in_comment(comment):
    return set(re.findall(REG_EXP, html.unescape(comment)))


def init_list(story_dir):
    path_to_file = os.path.join(story_dir, CONTENT_FILE)
    if os.path.exists(path_to_file):
        with open(path_to_file, 'r') as f:
            return [int(item.split('\t')[0]) for item in f.readlines()]
    else:
        return []


def unpack_result(results, index):
    return [res[index] for res in results]


async def post_download_page_with_refs_in_comments(loop, session, fetcher, post_id, story_dir=''):
    """Retrieve data for current post and recursively for all comments.
    """
    url = URL_TEMPLATE.format(post_id)
    number_of_refs = 0
    response = await fetcher.fetch(session, url)

    if response is None:
        return 0, 0

    elif response.get('type') == 'story':
        log.debug('story response {}'.format(response))
        story_url = response.get('url', STORY_TEMPLATE.format(post_id))
        story_dir = get_dir_name_for_story(story_dir, response.get('title', 'untitled'), post_id, story_url)
        await fetcher.fetch(session, story_url, just_json=False, dest_dir=story_dir)

    elif response.get('type') == 'comment':
        log.debug('Comment response {}'.format(response))
        refs = find_refs_in_comment(response.get('text', ''))
        number_of_refs = len(refs)

        tasks = [fetcher.fetch(session, comment_url, just_json=False, dest_dir=story_dir)
                 for comment_url in refs]
        if number_of_refs:
            log.debug('Collecting web pages for comment_id={}; total {}: {}'.format(post_id, number_of_refs, refs))
        await asyncio.gather(*tasks)

    # there are no comments
    if 'kids' not in response:
        return 0, number_of_refs

    # calculate this post's comments as number of comments
    number_of_comments = len(response['kids'])

    # create recursive tasks for all comments
    tasks = [post_download_page_with_refs_in_comments(
        loop, session, fetcher, kid_id, story_dir) for kid_id in response['kids']]

    # schedule the tasks and retrieve results
    results = await asyncio.gather(*tasks)

    # reduce the descendents comments and add it to this post's
    number_of_comments += sum(unpack_result(results, 0))
    number_of_refs += sum(unpack_result(results, 1))
    log.debug('{:^6} > {} comments'.format(post_id, number_of_comments))

    return number_of_comments, number_of_refs


async def download_top_stories_with_refs_in_comment(loop, limit, iteration, path, connections_limit):
    """Retrieve top stories in HN.
    """
    connector = aiohttp.TCPConnector(limit_per_host=connections_limit, loop=loop)
    async with aiohttp.ClientSession(connector=connector) as session:
        fetcher = URLFetcher()  # create a new fetcher for this task
        response = await fetcher.fetch(session, TOP_STORIES_URL)
        tasks = [post_download_page_with_refs_in_comments(
            loop, session, fetcher, post_id, path) for post_id in response[:limit] if post_id not in DOWNLOADED_STORIES]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for post_id, result in zip(response[:limit], results):
            if isinstance(result, Exception):
                log.error("Unexpected exception with post {}: ".format(post_id, result))
            else:
                log.info("Post {} has {} comments and {} refs in comments ({})".format(
                    post_id, *result, iteration))

        return fetcher.fetch_counter


async def poll_top_stories(loop, period, limit, path, connections_limit):
    """Periodic function that schedules download_top_stories_with_refs_in_comment.
    """
    iteration = 0
    while True:
        iteration += 1

        log.info("Downloading web pages for top {} stories ({})".format(
            limit, iteration))

        now = datetime.now()

        try:
            fetch_count = await download_top_stories_with_refs_in_comment\
                (loop, limit, iteration, path, connections_limit)

            log.info(
                '> Downloading stories with pages referenced in comments took {:.2f} seconds and {} fetches'.format(
                    (datetime.now() - now).total_seconds(), fetch_count))

        except Exception as e:
            log.error("Unexpected exception in poll_top_stories: {}".format(e))

        log.info("Waiting for {} seconds...".format(period))

        iteration += 1
        await asyncio.sleep(period)


if __name__ == '__main__':
    args = parser.parse_args()
    if args.verbose:
        log.setLevel(logging.DEBUG)

    DOWNLOADED_STORIES = init_list(args.path)
    log.info("Already downloaded stories: {}".format(DOWNLOADED_STORIES))

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(poll_top_stories(loop, args.period, args.limit, args.path, args.connections_limit))
    except KeyboardInterrupt:
        log.info("Keyboard Interrupt")

    except Exception as e:
        log.error("Unexpected exception: {}".format(e))

    finally:
        loop.close()
