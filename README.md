RssMerge

A python script to merge RSS feed


To run :
python RssMerge.py sampleInput.json


You can change the output directory in the json file, the path can be relative and must end with a backslash (or a slash on linux).


The type of a RSS feed changes the way the URL is handled:
* normal: the URL is take as-it and is not modified.
* youtube: The V3 API of youtube is used to fetch the RSS feed of the channel, the source must contain the channel ID.
* youtube-playlist: Same with a playlist ID.


Be careful to respect the syntax of the input file and do not delete the default values.

{
	"filename": Name of file, can be a path relative to the OUTPUT_DIRECTORY
	"title": Name of the feed in the metadata
	"link": URL the feed is pointing to
	"summary": Summary of the file in the RS metadata
	"size": Max number of elements in the feed

	"feeds":[
		{
		"name": Name of the feed (optionnal)

		"type": Type of the feed (defaults to normal)
		"source": source URL of the feed

		"size": Max number of this feed items that will be included in the merged feed
		
		"prefix": Prefex to add in front of the title of every element
		
		"regex": { Runs a regex replacement on the title of each element
			"pattern": 
			"replace": 
		},
		"filter": Allow only titles matching this regex
		},

		...
	]
}