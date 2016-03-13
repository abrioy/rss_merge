import json
import re
import feedparser
import socket
import PyRSS2Gen
import pytz
import datetime
import sys
import argparse
import logging


now = pytz.UTC.localize(datetime.datetime.utcnow())
logger = logging.getLogger("RssMerge")

YOUTUBE_URL_CHANNEL = "https://www.youtube.com/feeds/videos.xml?channel_id=%s"
YOUTUBE_URL_PLAYLIST = "https://www.youtube.com/feeds/videos.xml?playlist_id=%s"

DEFAULTS = {
    "title": "Feed",
    "link": "",
    "summary": "RSSfeed",
    "size": 30,

    "feeds":{
        "name": "Feed",

        "type": "normal",
        "source": "",

        "size": 6,

        "prefix": "",
        "regex": {
            "pattern": None,
            "replace": None
        },
        "filter": None
    }
}

# Sets a timeout for feedparser
socket.setdefaulttimeout(15)


def main(argv):
    global logger

    # Parsing arguments
    parser = argparse.ArgumentParser(description='Merge RSS feeds.')
    parser.add_argument(
            '--log', '-l', action='store', required=False,
            dest='logLevel', default='4',
            help='logging level (default=4): 0=off, 1=critical, 2=errors, 3=warnings, 4=info, 5=debug'
    )
    parser.add_argument(
            '--log-output', action='store', required=False,
            dest='logOutputFile', default=None,
            help='output file for the log'
    )
    parser.add_argument(
            '-o', '-output', action='store', required=False,
            dest='output', default=None,
            help='output rss file'
    )
    parser.add_argument(
            'feedsFilePath', metavar="feeds.json", action='store',
            help='name of the json file containing the feeds to parse'
    )
    args = parser.parse_args()



    # Logging
    if args.logOutputFile:
        handler = logging.FileHandler(args.logOutputFile)
    else:
        handler = logging.StreamHandler()

    formatter = logging.Formatter(
            '%(asctime)s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    levels = {
        '0' : logging.NOTSET,
        '1' : logging.CRITICAL,
        '2' : logging.ERROR,
        '3' : logging.WARNING,
        '4' : logging.INFO,
        '5' : logging.DEBUG
    }
    try:
        logger.setLevel(levels[args.logLevel])
    except:
        logger.setLevel(logging.INFO)
        logger.warning("Invalid logging level: "+args.logLevel)


    # Opening the db and creating the feeds
    feeds = None
    try:
        feeds = openDB(args.feedsFilePath)
    except IOError as e:
        logger.critical("Error while opening the input file \"%s\": %s" % (args.feedsFilePath, e))

    if feeds and args.output:
        with open(args.output, "wb") as outputstream:
             createFeed(feeds, outputstream)
    else:
        createFeed(feeds, sys.stdout)



def fillWithDefault(data, default):
    if isinstance(data, dict):
        for key in default:
            if key in data:
                fillWithDefault(data[key], default[key])
            else:
                data[key] = default[key]

    elif isinstance(data, list):
        for i,val in enumerate(data):
            fillWithDefault(data[i], default)



def openDB(databasePath):
    with open(databasePath,'r') as dbFile:
        db = json.loads(dbFile.read())
        dbFile.close()
        if 'defaults' in db:
            fillWithDefault(db, DEFAULTS)
            fillWithDefault(db, db['defaults'])
        else:
            fillWithDefault(db, DEFAULTS)

        return db



def createFeed(feedInfos, outputstream):
    logger.info("Creating feed \""+feedInfos['title']+"\".")

    feed = []
    for itemInfos in feedInfos['feeds']:
        # Fusing the feed lists while keeping them sorted
        feed.extend(fetchFeed(itemInfos))

    # Sorting (to be sure)
    feed = sorted(feed, key=lambda k: k['published_parsed'], reverse=True)
    # Truncating
    del feed[feedInfos['size']:]

    # Creating the feed
    rssItems = []
    for item in feed:
        rssItems.append(
                PyRSS2Gen.RSSItem(
                        title = item['title'],
                        link = item['link'],
                        description = item['summary'],
                        guid = PyRSS2Gen.Guid(item['link']),
                        pubDate = item['published'],
                )
        )

    rss = PyRSS2Gen.RSS2(
            title = feedInfos['title'],
            link = feedInfos['link'],
            description = feedInfos['summary'],
            lastBuildDate = now,
            items = rssItems
    )


    rss.write_xml(outputstream)


def fetchFeed(itemInfos):
    logger.info("\tFetching feed \""+itemInfos['name']+"\".")

    if itemInfos['type'] == 'youtube':
        sourceURL = YOUTUBE_URL_CHANNEL % itemInfos['source']
    elif itemInfos['type'] == 'youtube-playlist':
        sourceURL = YOUTUBE_URL_PLAYLIST % itemInfos['source']
    else:
        sourceURL = itemInfos['source']

    source = feedparser.parse(sourceURL, agent='Mozilla/5.0')
    if source.bozo and source.bozo != 0:
        if source.feed == []:
            logger.error("Error with an RSS feed, no elements found: \""+sourceURL+"\".\n"+source)
        else:
            logger.warning("There is an error with the feed: \""+sourceURL+"\": "+str(source.bozo_exception))
    elif source.feed == []:
        logger.warning("Feed is empty: \""+sourceURL+"\".")
    feed = []

    i = 0
    for entry in source.entries:
        # Making sure the required fields are here
        fillWithDefault(entry, {'title': "TITLE", 'link': "LINK", 'summary': "SUMMARY", 'media_description': None})

        # Special treatement for the summary in youtube feeds
        if 'youtube' in itemInfos['type']:
            entry['summary'] = '<h1>' + entry['title'] + '</h1>' + \
                               '<iframe id="ytplayer" type="text/html" width="640" height="390" src="https://www.youtube.com/embed/' + \
                               re.sub(r'.*youtube.com/watch.*v=([^&]+)', r'\1', entry['link']) + '"/>'
            if entry['media_description']:
                entry['summary'] += '<p>' + entry['media_description'] + '</p>'

        # Pattern substitution on the title
        if (itemInfos['regex']['pattern'] != None and itemInfos['regex']['replace'] != None):
            entry['title'] = re.sub(itemInfos['regex']['pattern'], itemInfos['regex']['replace'], entry['title'])

        # Filtering the titles
        if not (itemInfos['filter'] != None and not re.match(itemInfos['filter'], entry['title'])):
            entry['title'] = itemInfos['prefix'] + entry['title']

            # Checking that there is time information in the feed
            if (not (('published' in entry) and ('published_parsed' in entry) and
                         (entry['published'] != None) and (entry['published_parsed'] != None))):
                # Creating a phony date
                entry['published'] = datetime.datetime.fromtimestamp(1) + datetime.timedelta(days=(len(source.entries)-i))
                entry['published_parsed'] = entry['published'].timetuple()
                logger.warning("Incorrect entry in \""+itemInfos['name']+"\": \""+entry['title']+"\" - no time data. Adding a phony date: "+str(entry['published']))

            feed.append(entry)
        i += 1



    # Sorting
    feed = sorted(feed, key=lambda k: k['published_parsed'], reverse=True)
    # Truncating
    del feed[itemInfos['size']:]

    return feed


if __name__ == "__main__":
    main(sys.argv)
