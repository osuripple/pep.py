from common.log import logUtils as log
from constants import clientPackets, serverPackets
from constants import exceptions
from objects import glob


def handle(userToken, packetData):
	try:
		# get usertoken data
		userID = userToken.userID

		# Read packet data
		packetData = clientPackets.createMatch(packetData)

		# Make sure the name is valid
		matchName = packetData["matchName"].strip()
		if not matchName:
			raise exceptions.matchCreateError()

		# Create a match object
		# TODO: Player number check
		matchID = glob.matches.createMatch(matchName, packetData["matchPassword"].strip(), packetData["beatmapID"], packetData["beatmapName"], packetData["beatmapMD5"], packetData["gameMode"], userID)

		# Make sure the match has been created
		if matchID not in glob.matches.matches:
			raise exceptions.matchCreateError()

		with glob.matches.matches[matchID] as match:
			# Join that match
			userToken.joinMatch(matchID)

			# Give host to match creator
			match.setHost(userID)
			match.sendUpdates()
			match.changePassword(packetData["matchPassword"])
	except exceptions.matchCreateError:
		log.error("Error while creating match!")
		userToken.enqueue(serverPackets.matchJoinFail())
