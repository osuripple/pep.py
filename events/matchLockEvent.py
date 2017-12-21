from objects import glob
from constants import clientPackets

def handle(userToken, packetData):
	# Get token data
	userID = userToken.userID

	# Get packet data
	packetData = clientPackets.lockSlot(packetData)

	# Make sure the match exists
	matchID = userToken.matchID
	if matchID not in glob.matches.matches:
		return

	with glob.matches.matches[matchID] as match:
		# Host check
		if userID != match.hostUserID:
			return

		# Make sure we aren't locking our slot
		ourSlot = match.getUserSlotID(userID)
		if packetData["slotID"] == ourSlot:
			return

		# Lock/Unlock slot
		match.toggleSlotLocked(packetData["slotID"])
