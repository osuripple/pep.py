from constants import clientPackets
from objects import glob

def handle(userToken, packetData):
	# Get usertoken data
	userID = userToken.userID

	# Read packet data
	packetData = clientPackets.changeSlot(packetData)

	with glob.matches.matches[userToken.matchID] as match:
		# Change slot
		match.userChangeSlot(userID, packetData["slotID"])
