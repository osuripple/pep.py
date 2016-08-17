from constants import clientPackets
from objects import glob

def handle(userToken, packetData):
	# Get usertoken data
	userID = userToken.userID

	# Read packet data
	packetData = clientPackets.changeSlot(packetData)

	# Get match
	match = glob.matches.matches[userToken.matchID]

	# Change slot
	match.userChangeSlot(userID, packetData["slotID"])
