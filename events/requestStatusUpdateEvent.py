from constants import serverPackets
from helpers import logHelper as log

def handle(userToken, packetData):
	log.debug("Requested status update")

	# Update cache and send new stats
	userToken.updateCachedStats()
	userToken.enqueue(serverPackets.userStats(userToken.userID))
