from objects import glob
from constants import serverPackets
from constants import exceptions
from helpers import logHelper as log
from helpers import chatHelper as chat

def handle(userToken, _):
	try:
		# get user token data
		userID = userToken.userID
		username = userToken.username

		# Remove our userID from host's spectators
		target = userToken.spectating
		targetToken = glob.tokens.getTokenFromUserID(target)
		if targetToken == None:
			raise exceptions.tokenNotFoundException
		targetToken.removeSpectator(userID)

		# Part #spectator channel
		chat.partChannel(token=userToken, channel="#spect_{}".format(target))

		# Send the spectator left packet to host
		targetToken.enqueue(serverPackets.removeSpectator(userID))
		for c in targetToken.spectators:
			spec = glob.tokens.getTokenFromUserID(c)
			spec.enqueue(serverPackets.fellowSpectatorLeft(userID))

		#targetToken.enqueue(serverPackets.fellowSpectatorLeft(userID))

		# Console output
		log.info("{} are no longer spectating {}".format(username, target))
	except exceptions.tokenNotFoundException:
		log.warning("Spectator stop: token not found")
	finally:
		# Set our spectating user to 0
		userToken.stopSpectating()
