from objects import glob

def handle(userToken, _, has):
	# Get usertoken data
	userID = userToken.userID

	# Get match ID and match object
	matchID = userToken.matchID

	# Make sure we are in a match
	if matchID == -1:
		return

	# Make sure the match exists
	if matchID not in glob.matches.matches:
		return

	# Set has beatmap/no beatmap
	with glob.matches.matches[matchID] as match:
		match.userHasBeatmap(userID, has)
