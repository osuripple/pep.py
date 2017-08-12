from common.log import logUtils as log
from constants import clientPackets
from constants import exceptions
from objects import glob

def handle(userToken, packetData):
	try:
		# Start spectating packet
		packetData = clientPackets.startSpectating(packetData)

		# If the user id is less than 0, treat this as a stop spectating packet
		if packetData["userID"] < 0:
			userToken.stopSpectating()
			return

		# Get host token
		targetToken = glob.tokens.getTokenFromUserID(packetData["userID"])
		if targetToken is None:
			raise exceptions.tokenNotFoundException

		# Start spectating new user
		userToken.startSpectating(targetToken)
	except exceptions.tokenNotFoundException:
		# Stop spectating if token not found
		log.warning("Spectator start: token not found")
		userToken.stopSpectating()
