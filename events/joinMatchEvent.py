from common.log import logUtils as log
from constants import clientPackets
from constants import exceptions
from constants import serverPackets
from objects import glob


def handle(userToken, packetData):
	# read packet data
	packetData = clientPackets.joinMatch(packetData)
	matchID = packetData["matchID"]
	password = packetData["password"]

	# Get match from ID
	try:
		# Make sure the match exists
		if matchID not in glob.matches.matches:
			return

		# Hash password if needed
		# if password != "":
		#	password = generalUtils.stringMd5(password)

		# Check password
		with glob.matches.matches[matchID] as match:
			if match.matchPassword != "" and match.matchPassword != password:
				raise exceptions.matchWrongPasswordException()

			# Password is correct, join match
			userToken.joinMatch(matchID)
	except exceptions.matchWrongPasswordException:
		userToken.enqueue(serverPackets.matchJoinFail())
		log.warning("{} has tried to join a mp room, but he typed the wrong password".format(userToken.username))