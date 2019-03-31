import threading
import time

import redis

from common.ripple import userUtils
from common.log import logUtils as log
from common.sentry import sentry
from constants import serverPackets
from constants.exceptions import periodicLoopException
from events import logoutEvent
from objects import glob
from objects import osuToken


class tokenList:
	def __init__(self):
		self.tokens = {}
		self._lock = threading.Lock()

	def __enter__(self):
		self._lock.acquire()

	def __exit__(self, exc_type, exc_val, exc_tb):
		self._lock.release()

	def addToken(self, userID, ip = "", irc = False, timeOffset=0, tournament=False):
		"""
		Add a token object to tokens list

		:param userID: user id associated to that token
		:param ip: ip address of the client
		:param irc: if True, set this token as IRC client
		:param timeOffset: the time offset from UTC for this user. Default: 0.
		:param tournament: if True, flag this client as a tournement client. Default: True.
		:return: token object
		"""
		newToken = osuToken.token(userID, ip=ip, irc=irc, timeOffset=timeOffset, tournament=tournament)
		self.tokens[newToken.token] = newToken
		glob.redis.incr("ripple:online_users")
		return newToken

	def deleteToken(self, token):
		"""
		Delete a token from token list if it exists

		:param token: token string
		:return:
		"""
		if token in self.tokens:
			if self.tokens[token].ip != "":
				userUtils.deleteBanchoSessions(self.tokens[token].userID, self.tokens[token].ip)
			t = self.tokens.pop(token)
			del t
			glob.redis.decr("ripple:online_users")

	def getUserIDFromToken(self, token):
		"""
		Get user ID from a token

		:param token: token to find
		:return: False if not found, userID if found
		"""
		# Make sure the token exists
		if token not in self.tokens:
			return False

		# Get userID associated to that token
		return self.tokens[token].userID

	def getTokenFromUserID(self, userID, ignoreIRC=False, _all=False):
		"""
		Get token from a user ID

		:param userID: user ID to find
		:param ignoreIRC: if True, consider bancho clients only and skip IRC clients
		:param _all: if True, return a list with all clients that match given username, otherwise return
					only the first occurrence.
		:return: False if not found, token object if found
		"""
		# Make sure the token exists
		ret = []
		userID = int(userID)
		for _, value in self.tokens.items():
			if value.userID == userID:
				if ignoreIRC and value.irc:
					continue
				if _all:
					ret.append(value)
				else:
					return value

		# Return full list or None if not found
		if _all:
			return ret
		else:
			return None

	def getTokenFromUsername(self, username, ignoreIRC=False, safe=False, _all=False):
		"""
		Get an osuToken object from an username

		:param username: normal username or safe username
		:param ignoreIRC: if True, consider bancho clients only and skip IRC clients
		:param safe: 	if True, username is a safe username,
						compare it with token's safe username rather than normal username
		:param _all: if True, return a list with all clients that match given username, otherwise return
					only the first occurrence.
		:return: osuToken object or None
		"""
		# lowercase
		who = username.lower() if not safe else username

		# Make sure the token exists
		ret = []
		for _, value in self.tokens.items():
			if (not safe and value.username.lower() == who) or (safe and value.safeUsername == who):
				if ignoreIRC and value.irc:
					continue
				if _all:
					ret.append(value)
				else:
					return value

		# Return full list or None if not found
		if _all:
			return ret
		else:
			return None

	def deleteOldTokens(self, userID):
		"""
		Delete old userID's tokens if found

		:param userID: tokens associated to this user will be deleted
		:return:
		"""
		# Delete older tokens
		delete = []
		for key, value in list(self.tokens.items()):
			if value.userID == userID:
				# Delete this token from the dictionary
				#self.tokens[key].kick("You have logged in from somewhere else. You can't connect to Bancho/IRC from more than one device at the same time.", "kicked, multiple clients")
				delete.append(self.tokens[key])

		for i in delete:
			logoutEvent.handle(i)

	def multipleEnqueue(self, packet, who, but = False):
		"""
		Enqueue a packet to multiple users

		:param packet: packet bytes to enqueue
		:param who: userIDs array
		:param but: if True, enqueue to everyone but users in `who` array
		:return:
		"""
		for _, value in self.tokens.items():
			shouldEnqueue = False
			if value.userID in who and not but:
				shouldEnqueue = True
			elif value.userID not in who and but:
				shouldEnqueue = True

			if shouldEnqueue:
				value.enqueue(packet)

	def enqueueAll(self, packet):
		"""
		Enqueue packet(s) to every connected user

		:param packet: packet bytes to enqueue
		:return:
		"""
		for _, value in self.tokens.items():
			value.enqueue(packet)

	@sentry.capture()
	def usersTimeoutCheckLoop(self):
		"""
		Start timed out users disconnect loop.
		This function will be called every `checkTime` seconds and so on, forever.
		CALL THIS FUNCTION ONLY ONCE!
		:return:
		"""
		try:
			log.debug("Checking timed out clients")
			exceptions = []
			timedOutTokens = []		# timed out users
			timeoutLimit = int(time.time()) - 100
			for key, value in self.tokens.items():
				# Check timeout (fokabot is ignored)
				if value.pingTime < timeoutLimit and value.userID != 999 and not value.irc and not value.tournament:
					# That user has timed out, add to disconnected tokens
					# We can't delete it while iterating or items() throws an error
					timedOutTokens.append(key)

			# Delete timed out users from self.tokens
			# i is token string (dictionary key)
			for i in timedOutTokens:
				log.debug("{} timed out!!".format(self.tokens[i].username))
				self.tokens[i].enqueue(serverPackets.notification("Your connection to the server timed out."))
				try:
					logoutEvent.handle(self.tokens[i], None)
				except Exception as e:
					exceptions.append(e)
					log.error(
						"Something wrong happened while disconnecting a timed out client. Reporting to Sentry "
						"when the loop ends."
					)
			del timedOutTokens

			# Re-raise exceptions if needed
			if exceptions:
				raise periodicLoopException(exceptions)
		finally:
			# Schedule a new check (endless loop)
			threading.Timer(100, self.usersTimeoutCheckLoop).start()

	@sentry.capture()
	def spamProtectionResetLoop(self):
		"""
		Start spam protection reset loop.
		Called every 10 seconds.
		CALL THIS FUNCTION ONLY ONCE!

		:return:
		"""
		try:
			# Reset spamRate for every token
			for _, value in self.tokens.items():
				value.spamRate = 0
		finally:
			# Schedule a new check (endless loop)
			threading.Timer(10, self.spamProtectionResetLoop).start()

	def deleteBanchoSessions(self):
		"""
		Remove all `peppy:sessions:*` redis keys.
		Call at bancho startup to delete old cached sessions

		:return:
		"""
		try:
			# TODO: Make function or some redis meme
			glob.redis.eval("return redis.call('del', unpack(redis.call('keys', ARGV[1])))", 0, "peppy:sessions:*")
		except redis.RedisError:
			pass


	def tokenExists(self, username = "", userID = -1):
		"""
		Check if a token exists
		Use username or userid, not both at the same time.

		:param username: Optional.
		:param userID: Optional.
		:return: True if it exists, otherwise False
		"""
		if userID > -1:
			return True if self.getTokenFromUserID(userID) is not None else False
		else:
			return True if self.getTokenFromUsername(username) is not None else False