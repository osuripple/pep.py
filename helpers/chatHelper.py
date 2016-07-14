from objects import glob
from helpers import logHelper as log
from constants import exceptions
from constants import serverPackets
from objects import fokabot
from helpers import discordBotHelper
from helpers import userHelper
from events import logoutEvent
from events import channelJoinEvent
from constants import messageTemplates

def joinChannel(userID = 0, channel = "", token = None, toIRC = True):
	"""
	Join a channel

	userID -- 	user ID of the user that joins the channel. Optional.
				token can be used instead.
	token --	user token object of user that joins the channel. Optional.
					userID can be used instead.
	channel -- name of channe
	toIRC -- if True, send this channel join event to IRC. Must be true if joining from bancho.
			Optional. Defaukt: True
	return -- 	returns	0 if joined or other IRC code in case of error. Needed only on IRC-side
	"""
	try:
		# Get token if not defined
		if token == None:
			token = glob.tokens.getTokenFromUserID(userID)
			# Make sure the token exists
			if token == None:
				raise exceptions.userNotFoundException
		else:
			token = token
			userID = token.userID

		# Get usertoken data
		username = token.username

		# Normal channel, do check stuff
		# Make sure the channel exists
		if channel not in glob.channels.channels:
			raise exceptions.channelUnknownException

		# Check channel permissions
		channelObject = glob.channels.channels[channel]
		if channelObject.publicRead == False and token.admin == False:
			raise exceptions.channelNoPermissionsException

		# Add our userID to users in that channel
		channelObject.userJoin(userID)

		# Add the channel to our joined channel
		token.joinChannel(channel)

		# Send channel joined (bancho). We use clientName here because of #multiplayer and #spectator channels
		token.enqueue(serverPackets.channelJoinSuccess(userID, channelObject.clientName))

		# Send channel joined (IRC)
		if glob.irc == True and toIRC == True:
			glob.ircServer.banchoJoinChannel(username, channel)

		# Console output
		log.info("{} joined channel {}".format(username, channel))

		# IRC code return
		return 0
	except exceptions.channelNoPermissionsException:
		log.warning("{} attempted to join channel {}, but they have no read permissions".format(username, channel))
		return 403
	except exceptions.channelUnknownException:
		log.warning("{} attempted to join an unknown channel ({})".format(username, channel))
		return 403
	except exceptions.userNotFoundException:
		log.warning("User not connected to IRC/Bancho")
		return 403	# idk

def partChannel(userID = 0, channel = "", token = None, toIRC = True, kick = False):
	"""
	Part a channel

	userID -- 	user ID of the user that parts the channel. Optional.
				token can be used instead.
	token --	user token object of user that parts the channel. Optional.
					userID can be used instead.
	channel -- name of channel
	toIRC -- if True, send this channel join event to IRC. Must be true if joining from bancho.
			Optional. Defaukt: True
	kick -- if True, channel tab will be closed on client. Used when leaving lobby. Optional. Default: False
	return -- 	returns	0 if joined or other IRC code in case of error. Needed only on IRC-side
	"""
	try:
		# Get token if not defined
		if token == None:
			token = glob.tokens.getTokenFromUserID(userID)
			# Make sure the token exists
			if token == None:
				raise exceptions.userNotFoundException
		else:
			token = token
			userID = token.userID

		# Get usertoken data
		username = token.username

		# Determine internal/client name if needed
		# (toclient is used clientwise for #multiplayer and #spectator channels)
		channelClient = channel
		if channel == "#spectator":
			if token.spectating == 0:
				s = userID
			else:
				s = token.spectating
			channel = "#spect_{}".format(s)
		elif channel == "#multiplayer":
			channel = "#multi_{}".format(token.matchID)
		elif channel.startswith("#spect_"):
			channelClient = "#spectator"
		elif channel.startswith("#multi_"):
			channelClient = "#multiplayer"

		# Make sure the channel exists
		if channel not in glob.channels.channels:
			raise exceptions.channelUnknownException

		# Part channel (token-side and channel-side)
		channelObject = glob.channels.channels[channel]
		token.partChannel(channel)
		channelObject.userPart(userID)

		# Force close tab if needed
		# NOTE: Maybe always needed, will check later
		if kick == True:
			token.enqueue(serverPackets.channelKicked(channelObject.clientName))

		# IRC part
		if glob.irc == True and toIRC == True:
			glob.ircServer.banchoPartChannel(username, channel)

		# Console output
		log.info("{} parted channel {}".format(username, channel))

		# Return IRC code
		return 0
	except exceptions.channelUnknownException:
		log.warning("{} attempted to part an unknown channel ({})".format(username, channel))
		return 403
	except exceptions.userNotFoundException:
		log.warning("User not connected to IRC/Bancho")
		return 442	# idk




def sendMessage(fro = "", to = "", message = "", token = None, toIRC = True):
	"""
	Send a message to osu!bancho and IRC server

	fro -- 	sender username. Optional.
			You can use token instead of this if you wish.
	to -- receiver channel (if starts with #) or username
	message -- text of the message
	token -- 	sender token object.
					You can use this instead of fro if you are sending messages from bancho.
					Optional.
	toIRC --	if True, send the message to IRC. If False, send it to Bancho only.
			Optional. Default: True
	"""
	try:
		tokenString = ""
		# Get token object if not passed
		if token == None:
			token = glob.tokens.getTokenFromUsername(fro)
			if token == None:
				raise exceptions.userNotFoundException
		else:
			# token object alredy passed, get its string and its username (fro)
			fro = token.username
			tokenString = token.token

		# Set some variables
		userID = token.userID
		username = token.username
		recipients = []

		# Make sure the user is not in restricted mode
		if token.restricted == True:
			raise exceptions.userRestrictedException

		# Make sure the user is not silenced
		if token.isSilenced() == True:
			raise exceptions.userSilencedException

		# Determine internal name if needed
		# (toclient is used clientwise for #multiplayer and #spectator channels)
		toClient = to
		if to == "#spectator":
			if token.spectating == 0:
				s = userID
			else:
				s = token.spectating
			to = "#spect_{}".format(s)
		elif to == "#multiplayer":
			to = "#multi_{}".format(token.matchID)
		elif to.startswith("#spect_"):
			toClient = "#spectator"
		elif to.startswith("#multi_"):
			toClient = "#multiplayer"

		# Truncate message if > 2048 characters
		message = message[:2048]+"..." if len(message) > 2048 else message

		# Build packet bytes
		packet = serverPackets.sendMessage(username, toClient, message)

		# Send the message
		isChannel = to.startswith("#")
		if isChannel == True:
			# CHANNEL
			# Make sure the channel exists
			if to not in glob.channels.channels:
				raise exceptions.channelUnknownException

			# Make sure the channel is not in moderated mode
			if glob.channels.channels[to].moderated == True and token.admin == False:
				raise exceptions.channelModeratedException

			# Make sure we have write permissions
			if glob.channels.channels[to].publicWrite == False and token.admin == False:
				raise exceptions.channelNoPermissionsException

			# Everything seems fine, build recipients list and send packet
			recipients = glob.channels.channels[to].getConnectedUsers()[:]
			for key, value in glob.tokens.tokens.items():
				# Skip our client and irc clients
				if key == tokenString or value.irc == True:
					continue
				# Send to this client if it's connected to the channel
				if value.userID in recipients:
					value.enqueue(packet)
		else:
			# USER
			# Make sure recipient user is connected
			recipientToken = glob.tokens.getTokenFromUsername(to)
			if recipientToken == None:
				raise exceptions.userNotFoundException

			# Make sure the recipient is not restricted or we are FokaBot
			if recipientToken.restricted == True and fro.lower() != "fokabot":
				raise exceptions.userRestrictedException

			# TODO: Make sure the recipient has not disabled PMs for non-friends or he's our friend

			# Check message templates (mods/admins only)
			if message in messageTemplates.templates and token.admin == True:
				sendMessage(fro, to, messageTemplates.templates[message])

			# Everything seems fine, send packet
			recipientToken.enqueue(packet)

		# Send the message to IRC
		if glob.irc == True and toIRC == True:
			glob.ircServer.banchoMessage(fro, to, message)

		# Spam protection (ignore FokaBot)
		if userID > 999:
			token.spamProtection()

		# Fokabot message
		if isChannel == True or to.lower() == "fokabot":
			fokaMessage = fokabot.fokabotResponse(username, to, message)
			if fokaMessage != False:
				sendMessage("FokaBot", to if isChannel else fro, fokaMessage)

		# File and discord logs (public chat only)
		if to.startswith("#") == True:
			log.chat("{fro} @ {to}: {message}".format(fro=username, to=to, message=str(message.encode("utf-8"))))
			discordBotHelper.sendChatlog("**{fro} @ {to}:** {message}".format(fro=username, to=to, message=str(message.encode("utf-8"))[2:-1]))
		return 0
	except exceptions.userSilencedException:
		token.enqueue(serverPackets.silenceEndTime(token.getSilenceSecondsLeft()))
		log.warning("{} tried to send a message during silence".format(username))
		return 404
	except exceptions.channelModeratedException:
		log.warning("{} tried to send a message to a channel that is in moderated mode ({})".format(username, to))
		return 404
	except exceptions.channelUnknownException:
		log.warning("{} tried to send a message to an unknown channel ({})".format(username, to))
		return 403
	except exceptions.channelNoPermissionsException:
		log.warning("{} tried to send a message to channel {}, but they have no write permissions".format(username, to))
		return 404
	except exceptions.userRestrictedException:
		log.warning("{} tried to send a message {}, but the recipient is in restricted mode".format(username, to))
		return 404
	except exceptions.userNotFoundException:
		log.warning("User not connected to IRC/Bancho")
		return 401



""" IRC-Bancho Connect/Disconnect/Join/Part interfaces"""
def IRCConnect(username):
	userID = userHelper.getID(username)
	if userID == False:
		log.warning("{} doesn't exist".format(username))
		return
	glob.tokens.deleteOldTokens(userID)
	glob.tokens.addToken(userID, irc=True)
	glob.tokens.enqueueAll(serverPackets.userPanel(userID))
	log.info("{} logged in from IRC".format(username))

def IRCDisconnect(username):
	token = glob.tokens.getTokenFromUsername(username)
	if token == None:
		log.warning("{} doesn't exist".format(username))
		return
	logoutEvent.handle(token)
	log.info("{} disconnected from IRC".format(username))

def IRCJoinChannel(username, channel):
	userID = userHelper.getID(username)
	if userID == False:
		log.warning("{} doesn't exist".format(username))
		return
	# NOTE: This should have also `toIRC` = False` tho,
	# since we send JOIN message later on ircserver.py.
	# Will test this later
	return joinChannel(userID, channel)

def IRCPartChannel(username, channel):
	userID = userHelper.getID(username)
	if userID == False:
		log.warning("{} doesn't exist".format(username))
		return
	return partChannel(userID, channel)
