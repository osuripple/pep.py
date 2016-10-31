"""FokaBot related functions"""
import random
import re

import time

from common import generalUtils
from common.constants import actions
from common.ripple import userUtils
from constants import fokabotCommands
from objects import glob
from common.log import logUtils as log

import threading
from helpers import chatHelper as chat
from constants import serverPackets

# Tillerino np regex, compiled only once to increase performance
npRegex = re.compile("^https?:\\/\\/osu\\.ppy\\.sh\\/b\\/(\\d*)")

def connect():
	"""Add FokaBot to connected users and send userpanel/stats packet to everyone"""
	token = glob.tokens.addToken(999)
	token.actionID = actions.IDLE
	glob.streams.broadcast("main", serverPackets.userPanel(999))
	glob.streams.broadcast("main", serverPackets.userStats(999))

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
		if generalUtils.strContains(message.lower(), i["trigger"].lower()):
			# message has triggered a command

			# Make sure the user has right permissions
			if i["privileges"] is not None:
				# Rank = x
				if userUtils.getPrivileges(userUtils.getID(fro)) & i["privileges"] == 0:
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

def zingheriLoop():
	log.debug("SONO STATI I ZINGHERI, I ZINGHERI!")
	clients = glob.streams.getClients("zingheri")
	for i in clients:
		log.debug(str(i))
		if i not in glob.tokens.tokens:
			continue
		token = glob.tokens.tokens[i]
		if token.userID == 999:
			continue
		if token.zingheri == -1:
			chat.sendMessage("FokaBot", token.username, "Knock knock, trick or treat?\nWho are you?\nI'm a {meme}. I'm a little {meme}.\n(reply with 'trick' or 'treat')".format(meme=random.choice(["shavit", "loctaf", "peppy", "foka", "elfo", "nano", "cupola autoportante"])))
			token.zingheri = 0
		elif token.zingheri == 1:
			if token.actionID == actions.PLAYING and (int(time.time()) - token.actionLatestUpdate >= 25):
				token.enqueue(serverPackets.zingheri("You'd better give me a treat next time ;)"))
				token.leaveStream("zingheri")
	threading.Timer(30, zingheriLoop).start()