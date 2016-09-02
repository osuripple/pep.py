from constants import serverPackets
from constants import clientPackets
from objects import glob
from events import joinMatchEvent
from constants import exceptions
from helpers import logHelper as log

def handle(userToken, packetData):
	try:
		# get usertoken data
		userID = userToken.userID

		# Read packet data
		packetData = clientPackets.createMatch(packetData)

		# Create a match object
		# TODO: Player number check
		matchID = glob.matches.createMatch(packetData["matchName"], packetData["matchPassword"], packetData["beatmapID"], packetData["beatmapName"], packetData["beatmapMD5"], packetData["gameMode"], userID)

		# Make sure the match has been created
		if matchID not in glob.matches.matches:
			raise exceptions.matchCreateError

		# Get match object
		match = glob.matches.matches[matchID]

		# Join that match
		joinMatchEvent.joinMatch(userToken, matchID, packetData["matchPassword"])

		# Give host to match creator
		match.setHost(userID)

		# Send match create packet to everyone in lobby
		for i in glob.matches.usersInLobby:
			# Make sure this user is still connected
			token = glob.tokens.getTokenFromUserID(i)
			if token is not None:
				token.enqueue(serverPackets.createMatch(matchID))

		# Console output
		log.info("MPROOM{}: Room created!".format(matchID))
	except exceptions.matchCreateError:
		log.error("Error while creating match!")
