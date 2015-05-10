RssMerge

A python script to merge RSS feed


To run :
python RssMerge.py sampleInput.json


You can change the output directory in the json file, the path can be relative and must end with a backslash (or a slash on linux).
Be careful to respect the syntax of the input file and do not delete the default values.


The type of a RSS feed changes the way the URL is handled:
* normal: the URL is take as-it and is not modified.
* youtube: The V3 API of youtube is used to fetch the RSS feed of the channel, the source must contain the channel ID.
* youtube-playlist: Same with a playlist ID.