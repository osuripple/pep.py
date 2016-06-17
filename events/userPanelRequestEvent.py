from constants import clientPackets
from constants import serverPackets
from helpers import logHelper as log

def handle(userToken, packetData):
	# Read userIDs list
	packetData = clientPackets.userPanelRequest(packetData)

	# Process lists with length <= 32
	if len(packetData) > 256:
		log.warning("Received userPanelRequest with length > 256")
		return

	for i in packetData["users"]:
		# Enqueue userpanel packets relative to this user
		log.debug("Sending panel for user {}".format(i))
		userToken.enqueue(serverPackets.userPanel(i))
