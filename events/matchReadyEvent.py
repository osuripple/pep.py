from objects import glob

def handle(userToken, _):
	# Get usertoken data
	userID = userToken.userID

	# Make sure the match exists
	matchID = userToken.matchID
	if matchID not in glob.matches.matches:
		return

	with glob.matches.matches[matchID] as match:
		# Get our slotID and change ready status
		slotID = match.getUserSlotID(userID)
		if slotID is not None:
			match.toggleSlotReady(slotID)

		# If this is a tournament match, we should send the current status of ready
		# players.
		if match.isTourney:
			match.sendReadyStatus()
