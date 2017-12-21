from objects import glob

def handle(userToken, _):
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

	# Set our match complete
	with glob.matches.matches[matchID] as match:
		match.playerCompleted(userID)
