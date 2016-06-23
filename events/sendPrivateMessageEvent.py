from helpers import consoleHelper
from constants import bcolors
from constants import clientPackets
from constants import serverPackets
from objects import glob
from objects import fokabot
from constants import exceptions
from constants import messageTemplates
from helpers import generalFunctions
from helpers import userHelper
from helpers import logHelper as log
import time

def handle(userToken, packetData):
	"""
	Event called when someone sends a private message

	userToken -- request user token
	packetData -- request data bytes
	"""

	try:
		# Get usertoken username
		username = userToken.username
		userID = userToken.userID

		# Private message packet
		packetData = clientPackets.sendPrivateMessage(packetData)

		# Make sure the user is not silenced
		if userToken.isSilenced() == True:
			raise exceptions.userSilencedException

		# Check message length
		packetData["message"] = packetData["message"][:2048]+"..." if len(packetData["message"]) > 2048 else packetData["message"]

		if packetData["to"] == "FokaBot":
			# FokaBot command check
			fokaMessage = fokabot.fokabotResponse(username, packetData["to"], packetData["message"])
			if fokaMessage != False:
				userToken.enqueue(serverPackets.sendMessage("FokaBot", username, fokaMessage))
				log.pm("FokaBot -> {}: {}".format(packetData["to"], str(fokaMessage.encode("UTF-8"))))
		else:
			# Send packet message to target if it exists
			token = glob.tokens.getTokenFromUsername(packetData["to"])
			if token == None:
				raise exceptions.tokenNotFoundException()

			# Check message templates (mods/admins only)
			if packetData["message"] in messageTemplates.templates and userToken.rank >= 3:
				packetData["message"] = messageTemplates.templates[packetData["message"]]

			# Send message to target
			token.enqueue(serverPackets.sendMessage(username, packetData["to"], packetData["message"]))

			# Send away message to sender if needed
			if token.awayMessage != "":
				userToken.enqueue(serverPackets.sendMessage(packetData["to"], username, "This user is away: {}".format(token.awayMessage)))

		# Spam protection
		userToken.spamProtection()

		# Console and file output
		log.pm("{} -> {}: {}".format(username, packetData["to"], packetData["message"]))
	except exceptions.userSilencedException:
		userToken.enqueue(serverPackets.silenceEndTime(userToken.getSilenceSecondsLeft()))
		log.warning("{} tried to send a message during silence".format(username))
	except exceptions.tokenNotFoundException:
		# Token not found, user disconnected
		log.warning("{} tried to send a message to {}, but their token couldn't be found".format(username, packetData["to"]))
	except exceptions.messageTooLongException:
		# Message > 256 silence
		userToken.silence(2*3600, "Sending messages longer than 256 characters")
