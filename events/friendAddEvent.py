from common.log import logUtils as log
from common.ripple import userUtils
from constants import clientPackets


def handle(userToken, packetData):
	# Friend add packet
	packetData = clientPackets.addRemoveFriend(packetData)
	userUtils.addFriend(userToken.userID, packetData["friendID"])

	# Console output
	log.info("{} have added {} to their friends".format(userToken.username, str(packetData["friendID"])))
