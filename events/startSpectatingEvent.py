from constants import clientPackets
from constants import serverPackets
from constants import exceptions
from objects import glob
from helpers import userHelper
from helpers import logHelper as log

def handle(userToken, packetData):
	try:
		# Get usertoken data
		userID = userToken.userID
		username = userToken.username

		# Start spectating packet
		packetData = clientPackets.startSpectating(packetData)

		# Stop spectating old user if needed
		if userToken.spectating != 0:
			oldTargetToken = glob.tokens.getTokenFromUserID(userToken.spectating)
			oldTargetToken.enqueue(serverPackets.removeSpectator(userID))
			userToken.stopSpectating()

		# Start spectating new user
		userToken.startSpectating(packetData["userID"])

		# Get host token
		targetToken = glob.tokens.getTokenFromUserID(packetData["userID"])
		if targetToken == None:
			raise exceptions.tokenNotFoundException

		# Add us to host's spectators
		targetToken.addSpectator(userID)

		# Send spectator join packet to host
		targetToken.enqueue(serverPackets.addSpectator(userID))

		# Join #spectator channel
		userToken.enqueue(serverPackets.channelJoinSuccess(userID, "#spectator"))

		if len(targetToken.spectators) == 1:
			# First spectator, send #spectator join to host too
			targetToken.enqueue(serverPackets.channelJoinSuccess(userID, "#spectator"))

		# send fellowSpectatorJoined to all spectators
		for c in targetToken.spectators:
			if c is not userID:
				#targetToken.enqueue(serverPackets.fellowSpectatorJoined(c))
				specToken = glob.tokens.getTokenFromUserID(c)
				specToken.enqueue(serverPackets.fellowSpectatorJoined(userID))

		# Console output
		log.info("{} are spectating {}".format(username, userHelper.getUsername(packetData["userID"])))
	except exceptions.tokenNotFoundException:
		# Stop spectating if token not found
		log.warning("Spectator start: token not found")
		userToken.stopSpectating()
