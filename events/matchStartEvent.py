from objects import glob
from constants import slotStatuses
from constants import serverPackets

def handle(userToken, _):

	# Get match ID and match object
	matchID = userToken.matchID

	# Make sure we are in a match
	if matchID == -1:
		return

	# Make sure the match exists
	if matchID not in glob.matches.matches:
		return

	# The match exists, get object
	match = glob.matches.matches[matchID]

	# Host check
	if userToken.userID != match.hostUserID:
		return

	match.start()
