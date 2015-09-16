import json
import time
import re
import feedparser
import socket
import PyRSS2Gen
import pytz
import datetime
now = pytz.UTC.localize(datetime.datetime.utcnow());
import sys
import argparse
import pprint
pp = pprint.pformat
import StringIO
import traceback
import logging



# Sets a timeout of 15 sec for feedparser
socket.setdefaulttimeout(5);


def main(argv):
	global settings
	global logger

	# Parsing arguments
	parser = argparse.ArgumentParser(description='Merge RSS feeds.')
	parser.add_argument(
		'--log', '-l', action='store', required=False,
		dest='logLevel', default=4,
		help='logging level (default=4): 0=off, 1=critical, 2=errors, 3=warnings, 4=info, 5=debug'
	)
	parser.add_argument(
		'--log-output', action='store', required=False,
		dest='logOutput', default=None,
		help='output file for the log'
	)
	parser.add_argument(
		'databasePath', action='store',
		help='name of the json file containing the feeds to parse'
	)
	args = parser.parse_args()



	# Logging
	logger = logging.getLogger()
	if args.logOutput:
		handler = logging.FileHandler(args.logOutput)
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
	
	# Redirecting the traceback print to the logger
	old_print_exception = traceback.print_exception
	def custom_print_exception(etype, value, tb, limit=None, file=None):
		tb_output = StringIO.StringIO()
		traceback.print_tb(tb, limit, tb_output)
		logger.error(tb_output.getvalue())
		tb_output.close()
		old_print_exception(etype, value, tb, limit=None, file=None)
	traceback.print_exception = custom_print_exception


	# Opening the db and creating the feeds
	db = openDB(args.databasePath);
	settings = db['settings'];
	for item in db['data']:
		try:
			createFeed(item);
		except:
			traceback.print_exc();



def fillWithDefault(data, default):
	if isinstance(data, dict):
		for key in default:
			if key in data:
				fillWithDefault(data[key], default[key]);
			else:
				data[key] = default[key];

	elif isinstance(data, list):
		for i,val in enumerate(data):
			fillWithDefault(data[i], default);



def openDB(databasePath):
	dbFile = open(databasePath,'r');
	db = json.loads(dbFile.read());
	dbFile.close();
	fillWithDefault(db['data'], db['defaults']),

	return db



def createFeed(feedInfos):
	global settings
	global logger

	logger.info("Creating feed \""+feedInfos['title']+"\".");

	feed = [];
	for itemInfos in feedInfos['feeds']:
		# Fusing the feed lists while keeping them sorted
		try:
			feed.extend(fetchFeed(itemInfos));
		except:
			traceback.print_exc()

	# Sorting (to be sure)
	feed = sorted(feed, key=lambda k: k['published_parsed'], reverse=True) ;
	# Truncating
	del feed[feedInfos['size']:];

	# Creating the feed
	rssItems = [];
	for item in feed:
		rssItems.append(
			PyRSS2Gen.RSSItem(
				title = item['title'],
				link = item['link'],
				description = item['summary'],
				guid = PyRSS2Gen.Guid(item['link']),
				pubDate = item['published'],
			)
		);

	rss = PyRSS2Gen.RSS2(
		title = feedInfos['title'],
		link = feedInfos['link'],
		description = feedInfos['summary'],
		lastBuildDate = now,
		items = rssItems
	);

	rss = rss.to_xml("utf-8");

	feedFile = open(settings['OUTPUT_DIRECTORY'] + feedInfos['filename'] , "w");
	feedFile.write(rss);
	feedFile.close();


def fetchFeed(itemInfos):
	global settings	
	global logger


	logger.info("\tFetching feed \""+itemInfos['name']+"\".");

	if itemInfos['type'] == 'youtube':
		sourceURL = settings['YOUTUBE_URL_CHANNEL'] + itemInfos['source'];
	elif itemInfos['type'] == 'youtube-playlist':
		sourceURL = settings['YOUTUBE_URL_PLAYLIST'] + itemInfos['source'];
	else:
		sourceURL = itemInfos['source'];

	source = feedparser.parse(sourceURL);
	if source.entries == []:
		logger.error("Error with an RSS feed: \""+sourceURL+"\".");
		logger.error(str(source));
	feed = []

	for entry in source.entries:
		logger.debug(pp(entry));
		# Making sure the required fields are here
		fillWithDefault(entry, {'title': "TITLE", 'link': "LINK", 'summary': "SUMMARY", 'media_description': None});

		# Special treatement for the summary in youtube feeds
		if 'youtube' in itemInfos['type']:
			entry['summary'] = '<h1>' + entry['title'] + '</h1>' + \
				'<iframe id="ytplayer" type="text/html" width="640" height="390" src="https://www.youtube.com/embed/' + \
				re.sub(r'.*youtube.com/watch.*v=([^&]+)', r'\1', entry['link']) + '"/>';
			if entry['media_description']:
				entry['summary'] += '<p>' + entry['media_description'] + '</p>';
		
		# Pattern substitution on the title
		if (itemInfos['regex']['pattern'] != None and itemInfos['regex']['replace'] != None):
			entry['title'] = re.sub(itemInfos['regex']['pattern'], itemInfos['regex']['replace'], entry['title']);
		
		# Filtering the titles
		if not (itemInfos['filter'] != None and not re.match(itemInfos['filter'], entry['title'])):
			entry['title'] = itemInfos['prefix'] + entry['title']
			
			# Checking that there is time information in the feed
			if (('published' in entry) and ('published_parsed' in entry) and
				(entry['published'] != None) and (entry['published_parsed'] != None)):
				feed.append(entry);
			else:
				logger.warning("Discarded an entry in \""+itemInfos['name']+"\": \""+entry['title']+"\" - no time data.");
	

	# Sorting
	feed = sorted(feed, key=lambda k: k['published_parsed'], reverse=True) ;
	# Truncating
	del feed[itemInfos['size']:];

	return feed;


if __name__ == "__main__":
   main(sys.argv)