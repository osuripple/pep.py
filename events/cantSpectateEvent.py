from common.log import logUtils as log
from constants import exceptions
from constants import serverPackets
from objects import glob


def handle(userToken, _):
	# get usertoken data
	userID = userToken.userID

	try:
		# We don't have the beatmap, we can't spectate
		target = userToken.spectating
		targetToken = glob.tokens.getTokenFromUserID(target)

		# Send the packet to host
		targetToken.enqueue(serverPackets.noSongSpectator(userID))
	except exceptions.tokenNotFoundException:
		# Stop spectating if token not found
		log.warning("Spectator can't spectate: token not found")
		userToken.stopSpectating()
