from helpers import userHelper
from constants import clientPackets
from helpers import logHelper as log

def handle(userToken, packetData):
	# Friend add packet
	packetData = clientPackets.addRemoveFriend(packetData)
	userHelper.addFriend(userToken.userID, packetData["friendID"])

	# Console output
	log.info("{} have added {} to their friends".format(userToken.username, str(packetData["friendID"])))
