from objects import glob
from constants import serverPackets
from constants import exceptions

def handle(userToken, packetData):
	# get token data
	userID = userToken.userID

	# Send spectator frames to every spectator
	for i in userToken.spectators:
		# Send to every user but host
		if i != userID:
			try:
				# Get spectator token object
				spectatorToken = glob.tokens.getTokenFromUserID(i)

				# Make sure the token exists
				if spectatorToken is None:
					raise exceptions.stopSpectating

				# Make sure this user is spectating us
				if spectatorToken.spectating != userID:
					raise exceptions.stopSpectating

				# Everything seems fine, send spectator frames to this spectator
				spectatorToken.enqueue(serverPackets.spectatorFrames(packetData[7:]))
			except exceptions.stopSpectating:
				# Remove this user from spectators
				userToken.removeSpectator(i)
				userToken.enqueue(serverPackets.removeSpectator(i))
