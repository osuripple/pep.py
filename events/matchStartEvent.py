from objects import glob

def handle(userToken, _):

	# Get match ID and match object
	matchID = userToken.matchID

	# Make sure we are in a match
	if matchID == -1:
		return

	# Make sure the match exists
	if matchID not in glob.matches.matches:
		return

	with glob.matches.matches[matchID] as match:
		# Host check
		if userToken.userID != match.hostUserID:
			return

		match.start()
