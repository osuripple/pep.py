from objects import glob
from constants import slotStatuses
from constants import serverPackets

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
	glob.streams.broadcast(match.playingStreamName, serverPackets.matchFrames(slotID, packetData))