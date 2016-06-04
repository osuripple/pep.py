from helpers import userHelper
from constants import clientPackets
from helpers import logHelper as log

def handle(userToken, packetData):
	# Friend remove packet
	packetData = clientPackets.addRemoveFriend(packetData)
	userHelper.removeFriend(userToken.userID, packetData["friendID"])

	# Console output
	log.info("{} have removed {} from their friends".format(userToken.username, str(packetData["friendID"])))
