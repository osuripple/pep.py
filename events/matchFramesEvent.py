from objects import glob
from constants import slotStatuses
from constants import serverPackets
from helpers import logHelper as log

def handle(userToken, packetData):
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

	# The match exists, get object
	match = glob.matches.matches[matchID]

	# Change slot id in packetData
	slotID = match.getUserSlotID(userID)

	# Enqueue frames to who's playing
	for i in range(0,16):
		if match.slots[i]["userID"] > -1 and match.slots[i]["status"] == slotStatuses.playing:
			token = glob.tokens.getTokenFromUserID(match.slots[i]["userID"])
			if token != None:
				token.enqueue(serverPackets.matchFrames(slotID, packetData))
