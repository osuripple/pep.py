from constants import serverPackets
from helpers import logHelper as log

def handle(userToken, packetData):
	# Update cache and send new stats
	userToken.updateCachedStats()
	userToken.enqueue(serverPackets.userStats(userToken.userID))
