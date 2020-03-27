import os
DEST_DIR = './stories'


def download_story(session, fetcher, url):
    response = await fetcher.fetch(session, url, json=False)

    filename = '123.html'
    path = os.path.join(DEST_DIR, filename)
    with open(path, 'wb') as fp:
        fp.write(response)