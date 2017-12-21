from objects import glob
from constants import serverPackets, clientPackets

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

	# Parse the data
	data = clientPackets.matchFrames(packetData)

	with glob.matches.matches[matchID] as match:
		# Change slot id in packetData
		slotID = match.getUserSlotID(userID)

		# Update the score
		match.updateScore(slotID, data["totalScore"])
		match.updateHP(slotID, data["currentHp"])

		# Enqueue frames to who's playing
		glob.streams.broadcast(match.playingStreamName, serverPackets.matchFrames(slotID, packetData))