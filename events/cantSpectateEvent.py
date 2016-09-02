from objects import glob
from constants import serverPackets
from constants import exceptions
from helpers import logHelper as log

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
