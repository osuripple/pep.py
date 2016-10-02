from common.log import logUtils as log
from constants import clientPackets
from constants import serverPackets


def handle(userToken, packetData):
	# Read userIDs list
	packetData = clientPackets.userStatsRequest(packetData)

	# Process lists with length <= 32
	if len(packetData) > 32:
		log.warning("Received userStatsRequest with length > 32")
		return

	for i in packetData["users"]:
		log.debug("Sending stats for user {}".format(i))

		# Skip our stats
		if i == userToken.userID:
			continue

		# Enqueue stats packets relative to this user
		userToken.enqueue(serverPackets.userStats(i))
