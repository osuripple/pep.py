from objects import osuToken
from objects import glob
import time
import threading
from events import logoutEvent
from helpers import userHelper

class tokenList():
	"""
	List of connected osu tokens

	tokens -- dictionary. key: token string, value: token object
	"""

	def __init__(self):
		"""
		Initialize a tokens list
		"""
		self.tokens = {}

	def addToken(self, userID, ip = "", irc = False, timeOffset=0):
		"""
		Add a token object to tokens list

		userID -- user id associated to that token
		irc -- if True, set this token as IRC client
		return -- token object
		"""
		newToken = osuToken.token(userID, ip=ip, irc=irc, timeOffset=timeOffset)
		self.tokens[newToken.token] = newToken
		return newToken

	def deleteToken(self, token):
		"""
		Delete a token from token list if it exists

		token -- token string
		"""
		if token in self.tokens:
			# Delete session from DB
			if self.tokens[token].ip != "":
				userHelper.deleteBanchoSessions(self.tokens[token].userID, self.tokens[token].ip)

			# Pop token from list
			self.tokens.pop(token)

	def getUserIDFromToken(self, token):
		"""
		Get user ID from a token

		token -- token to find
		return -- false if not found, userID if found
		"""
		# Make sure the token exists
		if token not in self.tokens:
			return False

		# Get userID associated to that token
		return self.tokens[token].userID

	def getTokenFromUserID(self, userID):
		"""
		Get token from a user ID

		userID -- user ID to find
		return -- False if not found, token object if found
		"""
		# Make sure the token exists
		for _, value in self.tokens.items():
			if value.userID == userID:
				return value

		# Return none if not found
		return None

	def getTokenFromUsername(self, username):
		"""
		Get token from a username

		username -- username to find
		return -- False if not found, token object if found
		"""
		# lowercase
		who  = username.lower()

		# Make sure the token exists
		for _, value in self.tokens.items():
			if value.username.lower() == who:
				return value

		# Return none if not found
		return None

	def deleteOldTokens(self, userID):
		"""
		Delete old userID's tokens if found

		userID -- tokens associated to this user will be deleted
		"""

		# Delete older tokens
		for key, value in list(self.tokens.items()):
			if value.userID == userID:
				# Delete this token from the dictionary
				self.tokens[key].kick("You have logged in from somewhere else. You can't connect to Bancho/IRC from more than one device at the same time.")

	def multipleEnqueue(self, packet, who, but = False):
		"""
		Enqueue a packet to multiple users

		packet -- packet bytes to enqueue
		who -- userIDs array
		but -- if True, enqueue to everyone but users in who array
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

		packet -- packet bytes to enqueue
		"""
		for _, value in self.tokens.items():
			value.enqueue(packet)

	def usersTimeoutCheckLoop(self, timeoutTime = 100, checkTime = 100):
		"""
		Deletes all timed out users.
		If called once, will recall after checkTime seconds and so on, forever
		CALL THIS FUNCTION ONLY ONCE!

		timeoutTime - seconds of inactivity required to disconnect someone (Default: 100)
		checkTime - seconds between loops (Default: 100)
		"""
		timedOutTokens = []		# timed out users
		timeoutLimit = time.time()-timeoutTime
		for key, value in self.tokens.items():
			# Check timeout (fokabot is ignored)
			if value.pingTime < timeoutLimit and value.userID != 999 and value.irc == False:
				# That user has timed out, add to disconnected tokens
				# We can't delete it while iterating or items() throws an error
				timedOutTokens.append(key)

		# Delete timed out users from self.tokens
		# i is token string (dictionary key)
		for i in timedOutTokens:
			logoutEvent.handle(self.tokens[i], None)

		# Schedule a new check (endless loop)
		threading.Timer(checkTime, self.usersTimeoutCheckLoop, [timeoutTime, checkTime]).start()

	def spamProtectionResetLoop(self):
		"""
		Reset spam rate every 10 seconds.
		CALL THIS FUNCTION ONLY ONCE!
		"""
		# Reset spamRate for every token
		for _, value in self.tokens.items():
			value.spamRate = 0

		# Schedule a new check (endless loop)
		threading.Timer(10, self.spamProtectionResetLoop).start()

	def deleteBanchoSessions(self):
		"""
		Truncate bancho_sessions table.
		Call at bancho startup to delete old cached sessions
		"""
		glob.db.execute("TRUNCATE TABLE bancho_sessions")

	def tokenExists(self, username = "", userID = -1):
		"""
		Check if a token exists (aka check if someone is connected)

		username -- Optional.
		userID -- Optional.
		return -- True if it exists, otherwise False

		Use username or userid, not both at the same time.
		"""
		if userID > -1:
			return True if self.getTokenFromUserID(userID) is not None else False
		else:
			return True if self.getTokenFromUsername(username) is not None else False
