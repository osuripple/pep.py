"""FokaBot related functions"""
from helpers import userHelper
from objects import glob
from constants import actions
from constants import serverPackets
from constants import fokabotCommands
import re
from helpers import generalFunctions

# Tillerino np regex, compiled only once to increase performance
npRegex = re.compile("^https?:\\/\\/osu\\.ppy\\.sh\\/b\\/(\\d*)")

def connect():
	"""Add FokaBot to connected users and send userpanel/stats packet to everyone"""
	token = glob.tokens.addToken(999)
	token.actionID = actions.IDLE
	glob.tokens.enqueueAll(serverPackets.userPanel(999))
	glob.tokens.enqueueAll(serverPackets.userStats(999))

def disconnect():
	"""Remove FokaBot from connected users"""
	glob.tokens.deleteToken(glob.tokens.getTokenFromUserID(999))

def fokabotResponse(fro, chan, message):
	"""
	Check if a message has triggered fokabot (and return its response)

	fro -- sender username (for permissions stuff with admin commands)
	chan -- channel name
	message -- message

	return -- fokabot's response string or False
	"""
	for i in fokabotCommands.commands:
		# Loop though all commands
		#if i["trigger"] in message:
		if generalFunctions.strContains(message, i["trigger"]):
			# message has triggered a command

			# Make sure the user has right permissions
			if i["privileges"] is not None:
				# Rank = x
				if userHelper.getPrivileges(userHelper.getID(fro)) & i["privileges"] == 0:
					return False

			# Check argument number
			message = message.split(" ")
			if i["syntax"] != "" and len(message) <= len(i["syntax"].split(" ")):
				return "Wrong syntax: {} {}".format(i["trigger"], i["syntax"])

			# Return response or execute callback
			if i["callback"] is None:
				return i["response"]
			else:
				return i["callback"](fro, chan, message[1:])

	# No commands triggered
	return False