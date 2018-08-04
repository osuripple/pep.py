from common.log import logUtils as log
from common.ripple import userUtils
from constants import exceptions
from constants import messageTemplates
from constants import serverPackets
from events import logoutEvent
from objects import fokabot
from objects import glob


def joinChannel(userID = 0, channel = "", token = None, toIRC = True, force=False):
	"""
	Join a channel

	:param userID: user ID of the user that joins the channel. Optional. token can be used instead.
	:param token: user token object of user that joins the channel. Optional. userID can be used instead.
	:param channel: channel name
	:param toIRC: if True, send this channel join event to IRC. Must be true if joining from bancho. Default: True
	:param force: whether to allow game clients to join #spect_ and #multi_ channels
	:return: 0 if joined or other IRC code in case of error. Needed only on IRC-side
	"""
	try:
		# Get token if not defined
		if token is None:
			token = glob.tokens.getTokenFromUserID(userID)
			# Make sure the token exists
			if token is None:
				raise exceptions.userNotFoundException
		else:
			token = token

		# Normal channel, do check stuff
		# Make sure the channel exists
		if channel not in glob.channels.channels:
			raise exceptions.channelUnknownException()

		# Make sure a game client is not trying to join a #multi_ or #spect_ channel manually
		channelObject = glob.channels.channels[channel]
		if channelObject.isSpecial and not token.irc and not force:
			raise exceptions.channelUnknownException()

		# Add the channel to our joined channel
		token.joinChannel(channelObject)

		# Send channel joined (IRC)
		if glob.irc and not toIRC:
			glob.ircServer.banchoJoinChannel(token.username, channel)

		# Console output
		log.info("{} joined channel {}".format(token.username, channel))

		# IRC code return
		return 0
	except exceptions.channelNoPermissionsException:
		log.warning("{} attempted to join channel {}, but they have no read permissions".format(token.username, channel))
		return 403
	except exceptions.channelUnknownException:
		log.warning("{} attempted to join an unknown channel ({})".format(token.username, channel))
		return 403
	except exceptions.userAlreadyInChannelException:
		log.warning("User {} already in channel {}".format(token.username, channel))
		return 403
	except exceptions.userNotFoundException:
		log.warning("User not connected to IRC/Bancho")
		return 403	# idk

def partChannel(userID = 0, channel = "", token = None, toIRC = True, kick = False, force=False):
	"""
	Part a channel

	:param userID: user ID of the user that parts the channel. Optional. token can be used instead.
	:param token: user token object of user that parts the channel. Optional. userID can be used instead.
	:param channel: channel name
	:param toIRC: if True, send this channel join event to IRC. Must be true if joining from bancho. Optional. Default: True
	:param kick: if True, channel tab will be closed on client. Used when leaving lobby. Optional. Default: False
	:param force: whether to allow game clients to part #spect_ and #multi_ channels
	:return: 0 if joined or other IRC code in case of error. Needed only on IRC-side
	"""
	try:
		# Make sure the client is not drunk and sends partChannel when closing a PM tab
		if not channel.startswith("#"):
			return

		# Get token if not defined
		if token is None:
			token = glob.tokens.getTokenFromUserID(userID)
			# Make sure the token exists
			if token is None:
				raise exceptions.userNotFoundException()
		else:
			token = token

		# Determine internal/client name if needed
		# (toclient is used clientwise for #multiplayer and #spectator channels)
		channelClient = channel
		if channel == "#spectator":
			if token.spectating is None:
				s = userID
			else:
				s = token.spectatingUserID
			channel = "#spect_{}".format(s)
		elif channel == "#multiplayer":
			channel = "#multi_{}".format(token.matchID)
		elif channel.startswith("#spect_"):
			channelClient = "#spectator"
		elif channel.startswith("#multi_"):
			channelClient = "#multiplayer"

		# Make sure the channel exists
		if channel not in glob.channels.channels:
			raise exceptions.channelUnknownException()

		# Make sure a game client is not trying to join a #multi_ or #spect_ channel manually
		channelObject = glob.channels.channels[channel]
		if channelObject.isSpecial and not token.irc and not force:
			raise exceptions.channelUnknownException()

		# Make sure the user is in the channel
		if channel not in token.joinedChannels:
			raise exceptions.userNotInChannelException()

		# Part channel (token-side and channel-side)
		token.partChannel(channelObject)

		# Delete temporary channel if everyone left
		if "chat/{}".format(channelObject.name) in glob.streams.streams:
			if channelObject.temp and len(glob.streams.streams["chat/{}".format(channelObject.name)].clients) - 1 == 0:
				glob.channels.removeChannel(channelObject.name)

		# Force close tab if needed
		# NOTE: Maybe always needed, will check later
		if kick:
			token.enqueue(serverPackets.channelKicked(channelClient))

		# IRC part
		if glob.irc and toIRC:
			glob.ircServer.banchoPartChannel(token.username, channel)

		# Console output
		log.info("{} parted channel {} ({})".format(token.username, channel, channelClient))

		# Return IRC code
		return 0
	except exceptions.channelUnknownException:
		log.warning("{} attempted to part an unknown channel ({})".format(token.username, channel))
		return 403
	except exceptions.userNotInChannelException:
		log.warning("{} attempted to part {}, but he's not in that channel".format(token.username, channel))
		return 442
	except exceptions.userNotFoundException:
		log.warning("User not connected to IRC/Bancho")
		return 442	# idk

def sendMessage(fro = "", to = "", message = "", token = None, toIRC = True):
	"""
	Send a message to osu!bancho and IRC server

	:param fro: sender username. Optional. token can be used instead
	:param to: receiver channel (if starts with #) or username
	:param message: text of the message
	:param token: sender token object. Optional. fro can be used instead
	:param toIRC: if True, send the message to IRC. If False, send it to Bancho only. Default: True
	:return: 0 if joined or other IRC code in case of error. Needed only on IRC-side
	"""
	try:
		#tokenString = ""
		# Get token object if not passed
		if token is None:
			token = glob.tokens.getTokenFromUsername(fro)
			if token is None:
				raise exceptions.userNotFoundException()
		else:
			# token object alredy passed, get its string and its username (fro)
			fro = token.username
			#tokenString = token.token

		# Make sure this is not a tournament client
		# if token.tournament:
		# 	raise exceptions.userTournamentException()

		# Make sure the user is not in restricted mode
		if token.restricted:
			raise exceptions.userRestrictedException()

		# Make sure the user is not silenced
		if token.isSilenced():
			raise exceptions.userSilencedException()

		# Redirect !report to FokaBot
		if message.startswith("!report"):
			to = "FokaBot"

		# Determine internal name if needed
		# (toclient is used clientwise for #multiplayer and #spectator channels)
		toClient = to
		if to == "#spectator":
			if token.spectating is None:
				s = token.userID
			else:
				s = token.spectatingUserID
			to = "#spect_{}".format(s)
		elif to == "#multiplayer":
			to = "#multi_{}".format(token.matchID)
		elif to.startswith("#spect_"):
			toClient = "#spectator"
		elif to.startswith("#multi_"):
			toClient = "#multiplayer"

		# Make sure the message is valid
		if not message.strip():
			raise exceptions.invalidArgumentsException()

		# Truncate message if > 2048 characters
		message = message[:2048]+"..." if len(message) > 2048 else message

		# Check for word filters
		message = glob.chatFilters.filterMessage(message)

		# Build packet bytes
		packet = serverPackets.sendMessage(token.username, toClient, message)

		# Send the message
		isChannel = to.startswith("#")
		if isChannel:
			# CHANNEL
			# Make sure the channel exists
			if to not in glob.channels.channels:
				raise exceptions.channelUnknownException()

			# Make sure the channel is not in moderated mode
			if glob.channels.channels[to].moderated and not token.admin:
				raise exceptions.channelModeratedException()

			# Make sure we are in the channel
			if to not in token.joinedChannels:
				# I'm too lazy to put and test the correct IRC error code here...
				# but IRC is not strict at all so who cares
				raise exceptions.channelNoPermissionsException()

			# Make sure we have write permissions
			if not glob.channels.channels[to].publicWrite and not token.admin:
				raise exceptions.channelNoPermissionsException()

			# Add message in buffer
			token.addMessageInBuffer(to, message)

			# Everything seems fine, build recipients list and send packet
			glob.streams.broadcast("chat/{}".format(to), packet, but=[token.token])
		else:
			# USER
			# Make sure recipient user is connected
			recipientToken = glob.tokens.getTokenFromUsername(to)
			if recipientToken is None:
				raise exceptions.userNotFoundException()

			# Make sure the recipient is not a tournament client
			#if recipientToken.tournament:
			#	raise exceptions.userTournamentException()

			# Make sure the recipient is not restricted or we are FokaBot
			if recipientToken.restricted and fro.lower() != "fokabot":
				raise exceptions.userRestrictedException()

			# TODO: Make sure the recipient has not disabled PMs for non-friends or he's our friend

			# Away check
			if recipientToken.awayCheck(token.userID):
				sendMessage(to, fro, "\x01ACTION is away: {}\x01".format(recipientToken.awayMessage))

			# Check message templates (mods/admins only)
			if message in messageTemplates.templates and token.admin:
				sendMessage(fro, to, messageTemplates.templates[message])

			# Everything seems fine, send packet
			recipientToken.enqueue(packet)

		# Send the message to IRC
		if glob.irc and toIRC:
			messageSplitInLines = message.encode("latin-1").decode("utf-8").split("\n")
			for line in messageSplitInLines:
				if line == messageSplitInLines[:1] and line == "":
					continue
				glob.ircServer.banchoMessage(fro, to, line)

		# Spam protection (ignore FokaBot)
		if token.userID > 999:
			token.spamProtection()

		# Fokabot message
		if isChannel or to.lower() == "fokabot":
			fokaMessage = fokabot.fokabotResponse(token.username, to, message)
			if fokaMessage:
				sendMessage("FokaBot", to if isChannel else fro, fokaMessage)

		# File and discord logs (public chat only)
		if to.startswith("#") and not (message.startswith("\x01ACTION is playing") and to.startswith("#spect_")):
			log.chat("{fro} @ {to}: {message}".format(fro=token.username, to=to, message=message.encode("latin-1").decode("utf-8")))
			glob.schiavo.sendChatlog("**{fro} @ {to}:** {message}".format(fro=token.username, to=to, message=message.encode("latin-1").decode("utf-8")))
		return 0
	except exceptions.userSilencedException:
		token.enqueue(serverPackets.silenceEndTime(token.getSilenceSecondsLeft()))
		log.warning("{} tried to send a message during silence".format(token.username))
		return 404
	except exceptions.channelModeratedException:
		log.warning("{} tried to send a message to a channel that is in moderated mode ({})".format(token.username, to))
		return 404
	except exceptions.channelUnknownException:
		log.warning("{} tried to send a message to an unknown channel ({})".format(token.username, to))
		return 403
	except exceptions.channelNoPermissionsException:
		log.warning("{} tried to send a message to channel {}, but they have no write permissions".format(token.username, to))
		return 404
	except exceptions.userRestrictedException:
		log.warning("{} tried to send a message {}, but the recipient is in restricted mode".format(token.username, to))
		return 404
	except exceptions.userTournamentException:
		log.warning("{} tried to send a message {}, but the recipient is a tournament client".format(token.username, to))
		return 404
	except exceptions.userNotFoundException:
		log.warning("User not connected to IRC/Bancho")
		return 401
	except exceptions.invalidArgumentsException:
		log.warning("{} tried to send an invalid message to {}".format(token.username, to))
		return 404


""" IRC-Bancho Connect/Disconnect/Join/Part interfaces"""
def fixUsernameForBancho(username):
	"""
	Convert username from IRC format (without spaces) to Bancho format (with spaces)

	:param username: username to convert
	:return: converted username
	"""
	# If there are no spaces or underscores in the name
	# return it
	if " " not in username and "_" not in username:
		return username

	# Exact match first
	result = glob.db.fetch("SELECT id FROM users WHERE username = %s LIMIT 1", [username])
	if result is not None:
		return username

	# Username not found, replace _ with space
	return username.replace("_", " ")

def fixUsernameForIRC(username):
	"""
	Convert an username from Bancho format to IRC format (underscores instead of spaces)

	:param username: username to convert
	:return: converted username
	"""
	return username.replace(" ", "_")

def IRCConnect(username):
	"""
	Handle IRC login bancho-side.
	Add token and broadcast login packet.

	:param username: username
	:return:
	"""
	userID = userUtils.getID(username)
	if not userID:
		log.warning("{} doesn't exist".format(username))
		return
	glob.tokens.deleteOldTokens(userID)
	glob.tokens.addToken(userID, irc=True)
	glob.streams.broadcast("main", serverPackets.userPanel(userID))
	log.info("{} logged in from IRC".format(username))

def IRCDisconnect(username):
	"""
	Handle IRC logout bancho-side.
	Remove token and broadcast logout packet.

	:param username: username
	:return:
	"""
	token = glob.tokens.getTokenFromUsername(username)
	if token is None:
		log.warning("{} doesn't exist".format(username))
		return
	logoutEvent.handle(token)
	log.info("{} disconnected from IRC".format(username))

def IRCJoinChannel(username, channel):
	"""
	Handle IRC channel join bancho-side.

	:param username: username
	:param channel: channel name
	:return: IRC return code
	"""
	userID = userUtils.getID(username)
	if not userID:
		log.warning("{} doesn't exist".format(username))
		return
	# NOTE: This should have also `toIRC` = False` tho,
	# since we send JOIN message later on ircserver.py.
	# Will test this later
	return joinChannel(userID, channel)

def IRCPartChannel(username, channel):
	"""
	Handle IRC channel part bancho-side.

	:param username: username
	:param channel: channel name
	:return: IRC return code
	"""
	userID = userUtils.getID(username)
	if not userID:
		log.warning("{} doesn't exist".format(username))
		return
	return partChannel(userID, channel)

def IRCAway(username, message):
	"""
	Handle IRC away command bancho-side.

	:param username:
	:param message: away message
	:return: IRC return code
	"""
	userID = userUtils.getID(username)
	if not userID:
		log.warning("{} doesn't exist".format(username))
		return
	glob.tokens.getTokenFromUserID(userID).awayMessage = message
	return 305 if message == "" else 306