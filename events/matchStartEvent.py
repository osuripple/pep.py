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

	# Make sure we have enough players
	if match.countUsers() < 2 or match.checkTeams() == False:
		return

	# Change inProgress value
	match.inProgress = True

	# Set playing to ready players and set load, skip and complete to False
	for i in range(0,16):
		if (match.slots[i].status & slotStatuses.ready) > 0:
			match.slots[i].status = slotStatuses.playing
			match.slots[i].loaded = False
			match.slots[i].skip = False
			match.slots[i].complete = False

	# Send match start packet
	for i in range(0,16):
		if (match.slots[i].status & slotStatuses.playing) > 0 and match.slots[i].userID != -1:
			token = glob.tokens.getTokenFromUserID(match.slots[i].userID)
			if token is not None:
				token.enqueue(serverPackets.matchStart(matchID))

	# Send updates
	match.sendUpdate()
