from constants import clientPackets
from constants import serverPackets
from objects import glob
from constants import exceptions
from helpers import logHelper as log
from helpers import chatHelper as chat
from helpers import generalFunctions

def handle(userToken, packetData):
	# read packet data
	packetData = clientPackets.joinMatch(packetData)

	# Get match from ID
	joinMatch(userToken, packetData["matchID"], packetData["password"])

def joinMatch(userToken, matchID, password, isPasswordHashed = False):
	try:
		# Stop spectating
		userToken.stopSpectating()

		# Leave other matches
		userToken.partMatch()

		# Get usertoken data
		userID = userToken.userID

		# Make sure the match exists
		if matchID not in glob.matches.matches:
			raise exceptions.matchNotFoundException

		# Match exists, get object
		match = glob.matches.matches[matchID]

		# Hash password if needed
		if isPasswordHashed == False and password != "":
			password = generalFunctions.stringMd5(password)

		# Check password
		# TODO: Admins can enter every match
		if match.matchPassword != "":
			if match.matchPassword != password:
				raise exceptions.matchWrongPasswordException

		# Password is correct, join match
		result = match.userJoin(userID)

		# Check if we've joined the match successfully
		if result == False:
			raise exceptions.matchJoinErrorException

		# Match joined, set matchID for usertoken
		userToken.joinMatch(matchID)

		# Send packets
		userToken.enqueue(serverPackets.matchJoinSuccess(matchID))
		chat.joinChannel(token=userToken, channel="#multi_{}".format(matchID))
	except exceptions.matchNotFoundException:
		userToken.enqueue(serverPackets.matchJoinFail())
		log.warning("{} has tried to join a mp room, but it doesn't exist".format(userToken.username))
	except exceptions.matchWrongPasswordException:
		userToken.enqueue(serverPackets.matchJoinFail())
		log.warning("{} has tried to join a mp room, but he typed the wrong password".format(userToken.username))
	except exceptions.matchJoinErrorException:
		userToken.enqueue(serverPackets.matchJoinFail())
		log.warning("{} has tried to join a mp room, but an error has occured".format(userToken.username))
