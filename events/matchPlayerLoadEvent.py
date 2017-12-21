from objects import glob

def handle(userToken, _):
	# Get userToken data
	userID = userToken.userID

	# Get match ID and match object
	matchID = userToken.matchID

	# Make sure we are in a match
	if matchID == -1:
		return

	# Make sure the match exists
	if matchID not in glob.matches.matches:
		return

	# Set our load status
	with glob.matches.matches[matchID] as match:
		match.playerLoaded(userID)
