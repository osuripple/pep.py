from objects import match
from objects import glob
from constants import serverPackets

class matchList:
	matches = {}
	usersInLobby = []
	lastID = 1

	def __init__(self):
		"""Initialize a matchList object"""
		self.matches = {}
		self.usersInLobby = []
		self.lastID = 1

	def createMatch(self, matchName, matchPassword, beatmapID, beatmapName, beatmapMD5, gameMode, hostUserID):
		"""
		Add a new match to matches list

		matchName -- match name, string
		matchPassword -- match md5 password. Leave empty for no password
		beatmapID -- beatmap ID
		beatmapName -- beatmap name, string
		beatmapMD5 -- beatmap md5 hash, string
		gameMode -- game mode ID. See gameModes.py
		hostUserID -- user id of who created the match
		return -- match ID
		"""
		# Add a new match to matches list
		matchID = self.lastID
		self.lastID+=1
		self.matches[matchID] = match.match(matchID, matchName, matchPassword, beatmapID, beatmapName, beatmapMD5, gameMode, hostUserID)
		return matchID


	def lobbyUserJoin(self, userID):
		"""
		Add userID to users in lobby

		userID -- user who joined mp lobby
		"""

		# Make sure the user is not already in mp lobby
		if userID not in self.usersInLobby:
			# We don't need to join #lobby, client will automatically send a packet for it
			self.usersInLobby.append(userID)


	def lobbyUserPart(self, userID):
		"""
		Remove userID from users in lobby

		userID -- user who left mp lobby
		"""

		# Make sure the user is in mp lobby
		if userID in self.usersInLobby:
			# Part lobby and #lobby channel
			self.usersInLobby.remove(userID)


	def disposeMatch(self, __matchID):
		"""
		Destroy match object with id = __matchID

		__matchID -- ID of match to dispose
		"""

		# Make sure the match exists
		if __matchID not in self.matches:
			return

		# Remove match object
		self.matches.pop(__matchID)

		# Send match dispose packet to everyone in lobby
		for i in self.usersInLobby:
			token = glob.tokens.getTokenFromUserID(i)
			if token != None:
				token.enqueue(serverPackets.disposeMatch(__matchID))
