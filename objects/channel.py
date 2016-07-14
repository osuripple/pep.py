from objects import glob

class channel:
	"""
	A chat channel

	name -- channel name
	description -- channel description
	connectedUsers -- connected users IDs list
	publicRead -- bool
	publicWrite -- bool
	moderated -- bool
	"""

	def __init__(self, __name, __description, __publicRead, __publicWrite, temp):
		"""
		Create a new chat channel object

		__name -- channel name
		__description -- channel description
		__publicRead -- bool, if true channel can be read by everyone, if false it can be read only by mods/admins
		__publicWrite -- bool, same as public read but relative to write permissions
		temp -- if True, channel will be deleted when there's no one in the channel. Optional. Default = False.
		"""

		self.name = __name
		self.description = __description
		self.publicRead = __publicRead
		self.publicWrite = __publicWrite
		self.moderated = False
		self.temp = temp
		self.connectedUsers = [999]	# Fokabot is always connected to every channels (otherwise it doesn't show up in IRC users list)

		# Client name (#spectator/#multiplayer)
		self.clientName = self.name
		if self.name.startswith("#spect_"):
			self.clientName = "#spectator"
		elif self.name.startswith("#multi_"):
			self.clientName = "#multiplayer"


	def userJoin(self, __userID):
		"""
		Add a user to connected users

		__userID -- user ID that joined the channel
		"""

		if __userID not in self.connectedUsers:
			self.connectedUsers.append(__userID)


	def userPart(self, __userID):
		"""
		Remove a user from connected users

		__userID -- user ID that left the channel
		"""

		if __userID in self.connectedUsers:
			self.connectedUsers.remove(__userID)

		# Remove temp channels if empty or there's only fokabot connected
		l = len(self.connectedUsers)
		if self.temp == True and ((l == 0) or (l == 1 and 999 in self.connectedUsers)):
			glob.channels.removeChannel(self.name)


	def getConnectedUsers(self):
		"""
		Get connected user IDs list

		return -- connectedUsers list
		"""
		return self.connectedUsers


	def getConnectedUsersCount(self):
		"""
		Count connected users

		return -- connected users number
		"""
		return len(self.connectedUsers)
