from constants import clientPackets
from objects import glob

def handle(userToken, packetData):
	# Read token and packet data
	userID = userToken.userID
	packetData = clientPackets.matchInvite(packetData)

	# Get match ID and match object
	matchID = userToken.matchID

	# Make sure we are in a match
	if matchID == -1:
		return

	# Make sure the match exists
	if matchID not in glob.matches.matches:
		return

	# Send invite
	with glob.matches.matches[matchID] as match:
		match.invite(userID, packetData["userID"])
