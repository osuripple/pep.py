import threading
import time
import uuid

from common.constants import gameModes, actions
from common.log import logUtils as log
from common.ripple import userUtils
from constants import exceptions
from constants import serverPackets
from events import logoutEvent
from helpers import chatHelper as chat
from objects import glob


class token:
	def __init__(self, userID, token_ = None, ip ="", irc = False, timeOffset = 0, tournament = False):
		"""
		Create a token object and set userID and token

		:param userID: user associated to this token
		:param token_: 	if passed, set token to that value
						if not passed, token will be generated
		:param ip: client ip. optional.
		:param irc: if True, set this token as IRC client. Default: False.
		:param timeOffset: the time offset from UTC for this user. Default: 0.
		:param tournament: if True, flag this client as a tournement client. Default: True.
		"""
		# Set stuff
		self.userID = userID
		self.username = userUtils.getUsername(self.userID)
		self.safeUsername = userUtils.getSafeUsername(self.userID)
		self.privileges = userUtils.getPrivileges(self.userID)
		self.admin = userUtils.isInPrivilegeGroup(self.userID, "developer")\
					 or userUtils.isInPrivilegeGroup(self.userID, "community manager")\
					 or userUtils.isInPrivilegeGroup(self.userID, "chat mod")
		self.irc = irc
		self.kicked = False
		self.restricted = userUtils.isRestricted(self.userID)
		self.loginTime = int(time.time())
		self.pingTime = self.loginTime
		self.timeOffset = timeOffset
		self.streams = []
		self.tournament = tournament
		self.messagesBuffer = []

		# Default variables
		self.spectators = []

		# TODO: Move those two vars to a class
		self.spectating = None
		self.spectatingUserID = 0	# we need this in case we the host gets DCed

		self.location = [0,0]
		self.joinedChannels = []
		self.ip = ip
		self.country = 0
		self.location = [0,0]
		self.awayMessage = ""
		self.sentAway = []
		self.matchID = -1
		self.tillerino = [0,0,-1.0]	# beatmap, mods, acc
		self.silenceEndTime = 0
		self.queue = bytes()

		# Spam protection
		self.spamRate = 0

		# Stats cache
		self.actionID = actions.IDLE
		self.actionText = ""
		self.actionMd5 = ""
		self.actionMods = 0
		self.gameMode = gameModes.STD
		self.beatmapID = 0
		self.rankedScore = 0
		self.accuracy = 0.0
		self.playcount = 0
		self.totalScore = 0
		self.gameRank = 0
		self.pp = 0

		# Generate/set token
		if token_ is not None:
			self.token = token_
		else:
			self.token = str(uuid.uuid4())

		# Locks
		self.processingLock = threading.Lock()	# Acquired while there's an incoming packet from this user
		self._bufferLock = threading.Lock()		# Acquired while writing to packets buffer
		self._spectLock = threading.RLock()

		# Set stats
		self.updateCachedStats()

		# If we have a valid ip, save bancho session in DB so we can cache LETS logins
		if ip != "":
			userUtils.saveBanchoSession(self.userID, self.ip)

		# Join main stream
		self.joinStream("main")

	def enqueue(self, bytes_):
		"""
		Add bytes (packets) to queue

		:param bytes_: (packet) bytes to enqueue
		"""
		try:
			# Acquire the buffer lock
			self._bufferLock.acquire()

			# Never enqueue for IRC clients or Foka
			if self.irc or self.userID < 999:
				return

			# Avoid memory leaks
			if len(bytes_) < 10 * 10 ** 6:
				self.queue += bytes_
			else:
				log.warning("{}'s packets buffer is above 10M!! Lost some data!".format(self.username))
		finally:
			# Release the buffer lock
			self._bufferLock.release()

	def resetQueue(self):
		"""Resets the queue. Call when enqueued packets have been sent"""
		try:
			self._bufferLock.acquire()
			self.queue = bytes()
		finally:
			self._bufferLock.release()

	def joinChannel(self, channelObject):
		"""
		Join a channel

		:param channelObject: channel object
		:raises: exceptions.userAlreadyInChannelException()
				 exceptions.channelNoPermissionsException()
		"""
		if channelObject.name in self.joinedChannels:
			raise exceptions.userAlreadyInChannelException()
		if not channelObject.publicRead and not self.admin:
			raise exceptions.channelNoPermissionsException()
		self.joinedChannels.append(channelObject.name)
		self.joinStream("chat/{}".format(channelObject.name))
		self.enqueue(serverPackets.channelJoinSuccess(self.userID, channelObject.clientName))

	def partChannel(self, channelObject):
		"""
		Remove channel from joined channels list

		:param channelObject: channel object
		"""
		self.joinedChannels.remove(channelObject.name)
		self.leaveStream("chat/{}".format(channelObject.name))

	def setLocation(self, latitude, longitude):
		"""
		Set client location

		:param latitude: latitude
		:param longitude: longitude
		"""
		self.location = (latitude, longitude)

	def getLatitude(self):
		"""
		Get latitude

		:return: latitude
		"""
		return self.location[0]

	def getLongitude(self):
		"""
		Get longitude

		:return: longitude
		"""
		return self.location[1]

	def startSpectating(self, host):
		"""
		Set the spectating user to userID, join spectator stream and chat channel
		and send required packets to host

		:param host: host osuToken object
		"""
		try:
			self._spectLock.acquire()

			# Stop spectating old client
			self.stopSpectating()

			# Set new spectator host
			self.spectating = host.token
			self.spectatingUserID = host.userID

			# Add us to host's spectator list
			host.spectators.append(self.token)

			# Create and join spectator stream
			streamName = "spect/{}".format(host.userID)
			glob.streams.add(streamName)
			self.joinStream(streamName)
			host.joinStream(streamName)

			# Send spectator join packet to host
			host.enqueue(serverPackets.addSpectator(self.userID))

			# Create and join #spectator (#spect_userid) channel
			glob.channels.addTempChannel("#spect_{}".format(host.userID))
			chat.joinChannel(token=self, channel="#spect_{}".format(host.userID), force=True)
			if len(host.spectators) == 1:
				# First spectator, send #spectator join to host too
				chat.joinChannel(token=host, channel="#spect_{}".format(host.userID), force=True)

			# Send fellow spectator join to all clients
			glob.streams.broadcast(streamName, serverPackets.fellowSpectatorJoined(self.userID))

			# Get current spectators list
			for i in host.spectators:
				if i != self.token and i in glob.tokens.tokens:
					self.enqueue(serverPackets.fellowSpectatorJoined(glob.tokens.tokens[i].userID))

			# Log
			log.info("{} is spectating {}".format(self.username, host.username))
		finally:
			self._spectLock.release()

	def stopSpectating(self):
		"""
		Stop spectating, leave spectator stream and channel
		and send required packets to host

		:return:
		"""
		try:
			self._spectLock.acquire()

			# Remove our userID from host's spectators
			if self.spectating is None or self.spectatingUserID <= 0:
				return
			if self.spectating in glob.tokens.tokens:
				hostToken = glob.tokens.tokens[self.spectating]
			else:
				hostToken = None
			streamName = "spect/{}".format(self.spectatingUserID)

			# Remove us from host's spectators list,
			# leave spectator stream
			# and end the spectator left packet to host
			self.leaveStream(streamName)
			if hostToken is not None:
				hostToken.spectators.remove(self.token)
				hostToken.enqueue(serverPackets.removeSpectator(self.userID))

				# and to all other spectators
				for i in hostToken.spectators:
					if i in glob.tokens.tokens:
						glob.tokens.tokens[i].enqueue(serverPackets.fellowSpectatorLeft(self.userID))

				# If nobody is spectating the host anymore, close #spectator channel
				# and remove host from spect stream too
				if len(hostToken.spectators) == 0:
					chat.partChannel(token=hostToken, channel="#spect_{}".format(hostToken.userID), kick=True, force=True)
					hostToken.leaveStream(streamName)

				# Console output
				log.info("{} is no longer spectating {}. Current spectators: {}".format(self.username, self.spectatingUserID, hostToken.spectators))

			# Part #spectator channel
			chat.partChannel(token=self, channel="#spect_{}".format(self.spectatingUserID), kick=True, force=True)

			# Set our spectating user to 0
			self.spectating = None
			self.spectatingUserID = 0
		finally:
			self._spectLock.release()

	def updatePingTime(self):
		"""
		Update latest ping time to current time

		:return:
		"""
		self.pingTime = int(time.time())

	def joinMatch(self, matchID):
		"""
		Set match to matchID, join match stream and channel

		:param matchID: new match ID
		:return:
		"""
		# Make sure the match exists
		if matchID not in glob.matches.matches:
			return

		# Match exists, get object
		match = glob.matches.matches[matchID]

		# Stop spectating
		self.stopSpectating()

		# Leave other matches
		if self.matchID > -1 and self.matchID != matchID:
			self.leaveMatch()

		# Try to join match
		joined = match.userJoin(self)
		if not joined:
			self.enqueue(serverPackets.matchJoinFail())
			return

		# Set matchID, join stream, channel and send packet
		self.matchID = matchID
		self.joinStream(match.streamName)
		chat.joinChannel(token=self, channel="#multi_{}".format(self.matchID), force=True)
		self.enqueue(serverPackets.matchJoinSuccess(matchID))

		if match.isTourney:
			# Alert the user if we have just joined a tourney match
			self.enqueue(serverPackets.notification("You are now in a tournament match."))
			# If an user joins, then the ready status of the match changes and
			# maybe not all users are ready.
			match.sendReadyStatus()

	def leaveMatch(self):
		"""
		Leave joined match, match stream and match channel

		:return:
		"""
		# Make sure we are in a match
		if self.matchID == -1:
			return

		# Part #multiplayer channel and streams (/ and /playing)
		chat.partChannel(token=self, channel="#multi_{}".format(self.matchID), kick=True, force=True)
		self.leaveStream("multi/{}".format(self.matchID))
		self.leaveStream("multi/{}/playing".format(self.matchID))	# optional

		# Set usertoken match to -1
		leavingMatchID = self.matchID
		self.matchID = -1

		# Make sure the match exists
		if leavingMatchID not in glob.matches.matches:
			return

		# The match exists, get object
		match = glob.matches.matches[leavingMatchID]

		# Set slot to free
		match.userLeft(self)

		if match.isTourney:
			# If an user leaves, then the ready status of the match changes and
			# maybe all users are ready. Or maybe nobody is in the match anymore
			match.sendReadyStatus()

	def kick(self, message="You have been kicked from the server. Please login again.", reason="kick"):
		"""
		Kick this user from the server

		:param message: Notification message to send to this user.
						Default: "You have been kicked from the server. Please login again."
		:param reason: Kick reason, used in logs. Default: "kick"
		:return:
		"""
		# Send packet to target
		log.info("{} has been disconnected. ({})".format(self.username, reason))
		if message != "":
			self.enqueue(serverPackets.notification(message))
		self.enqueue(serverPackets.loginFailed())

		# Logout event
		logoutEvent.handle(self, deleteToken=self.irc)

	def silence(self, seconds = None, reason = "", author = 999):
		"""
		Silences this user (db, packet and token)

		:param seconds: silence length in seconds. If None, get it from db. Default: None
		:param reason: silence reason. Default: empty string
		:param author: userID of who has silenced the user. Default: 999 (FokaBot)
		:return:
		"""
		if seconds is None:
			# Get silence expire from db if needed
			seconds = max(0, userUtils.getSilenceEnd(self.userID) - int(time.time()))
		else:
			# Silence in db and token
			userUtils.silence(self.userID, seconds, reason, author)

		# Silence token
		self.silenceEndTime = int(time.time()) + seconds

		# Send silence packet to user
		self.enqueue(serverPackets.silenceEndTime(seconds))

		# Send silenced packet to everyone else
		glob.streams.broadcast("main", serverPackets.userSilenced(self.userID))

	def spamProtection(self, increaseSpamRate = True):
		"""
		Silences the user if is spamming.

		:param increaseSpamRate: set to True if the user has sent a new message. Default: True
		:return:
		"""
		# Increase the spam rate if needed
		if increaseSpamRate:
			self.spamRate += 1

		# Silence the user if needed
		if self.spamRate > 10:
			self.silence(1800, "Spamming (auto spam protection)")

	def isSilenced(self):
		"""
		Returns True if this user is silenced, otherwise False

		:return: True if this user is silenced, otherwise False
		"""
		return self.silenceEndTime-int(time.time()) > 0

	def getSilenceSecondsLeft(self):
		"""
		Returns the seconds left for this user's silence
		(0 if user is not silenced)

		:return: silence seconds left (or 0)
		"""
		return max(0, self.silenceEndTime-int(time.time()))

	def updateCachedStats(self):
		"""
		Update all cached stats for this token

		:return:
		"""
		stats = userUtils.getUserStats(self.userID, self.gameMode)
		log.debug(str(stats))
		if stats is None:
			log.warning("Stats query returned None")
			return
		self.rankedScore = stats["rankedScore"]
		self.accuracy = stats["accuracy"]/100
		self.playcount = stats["playcount"]
		self.totalScore = stats["totalScore"]
		self.gameRank = stats["gameRank"]
		self.pp = stats["pp"]

	def checkRestricted(self):
		"""
		Check if this token is restricted. If so, send fokabot message

		:return:
		"""
		oldRestricted = self.restricted
		self.restricted = userUtils.isRestricted(self.userID)
		if self.restricted:
			self.setRestricted()
		elif not self.restricted and oldRestricted != self.restricted:
			self.resetRestricted()

	def checkBanned(self):
		"""
		Check if this user is banned. If so, disconnect it.

		:return:
		"""
		if userUtils.isBanned(self.userID):
			self.enqueue(serverPackets.loginBanned())
			logoutEvent.handle(self, deleteToken=False)


	def setRestricted(self):
		"""
		Set this token as restricted, send FokaBot message to user
		and send offline packet to everyone

		:return:
		"""
		self.restricted = True
		chat.sendMessage("FokaBot", self.username, "Your account is currently in restricted mode. Please visit ripple's website for more information.")

	def resetRestricted(self):
		"""
		Send FokaBot message to alert the user that he has been unrestricted
		and he has to log in again.

		:return:
		"""
		chat.sendMessage("FokaBot", self.username, "Your account has been unrestricted! Please log in again.")

	def joinStream(self, name):
		"""
		Join a packet stream, or create it if the stream doesn't exist.

		:param name: stream name
		:return:
		"""
		glob.streams.join(name, token=self.token)
		if name not in self.streams:
			self.streams.append(name)

	def leaveStream(self, name):
		"""
		Leave a packets stream

		:param name: stream name
		:return:
		"""
		glob.streams.leave(name, token=self.token)
		if name in self.streams:
			self.streams.remove(name)

	def leaveAllStreams(self):
		"""
		Leave all joined packet streams

		:return:
		"""
		for i in self.streams:
			self.leaveStream(i)

	def awayCheck(self, userID):
		"""
		Returns True if userID doesn't know that we are away
		Returns False if we are not away or if userID already knows we are away

		:param userID: original sender userID
		:return:
		"""
		if self.awayMessage == "" or userID in self.sentAway:
			return False
		self.sentAway.append(userID)
		return True

	def addMessageInBuffer(self, chan, message):
		"""
		Add a message in messages buffer (10 messages, truncated at 50 chars).
		Used as proof when the user gets reported.

		:param chan: channel
		:param message: message content
		:return:
		"""
		if len(self.messagesBuffer) > 9:
			self.messagesBuffer = self.messagesBuffer[1:]
		self.messagesBuffer.append("{time} - {user}@{channel}: {message}".format(time=time.strftime("%H:%M", time.localtime()), user=self.username, channel=chan, message=message[:50]))

	def getMessagesBufferString(self):
		"""
		Get the content of the messages buffer as a string

		:return: messages buffer content as a string
		"""
		return "\n".join(x for x in self.messagesBuffer)