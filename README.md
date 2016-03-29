rss_merge
=========

A python script to merge RSS feeds


How to run :
`python rss_merge.py sampleInput.json -o sampleOutput.rss`


The input file contains a list of the feeds to merge and some metadata, you can specify as many feeds as you want
to be merged into one. Most of these feeds are optional, see the file `sampleInput.json` for a working example.

	{
		"title": Name of the output feed in the metadata
		"link": URL the output feed is pointing to
		"summary": Summary of the file in the RSS metadata
		"size": Max number of elements in the output feed

		"feeds":[
			{
				"name": Name of the input feed

				"type": Type of the input feed (see below)
				"source": source URL of the input feed

				"size": Max number of items from this feed that will be included in the final merged feed
				
				"prefix": Prefix to add in front of the title of every element
				
				"regex": { Runs a regex replacement on the title of each element
					"pattern": 
					"replace": 
				},
				"filter": Filer the elements of the feed, including only thoses matching this regex
			},

			...
		]
	}
	
The `type` of a feed changes the way the `source` field is handled:

* `normal`: the URL is used as-it and is not modified.
* `youtube`: The Youtube API V3 is used to fetch the RSS feed of the channel, the source must contain the channel ID. 
(How to get the channel ID: http://stackoverflow.com/questions/14366648/how-can-i-get-a-channel-id-from-youtube)
* `youtube-playlist`: Same with a playlist ID (usually found in the url of a playlist on youtube).
