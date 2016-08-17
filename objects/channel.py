from objects import glob

class channel:
	"""
	A chat channel
	"""

	def __init__(self, name, description, publicRead, publicWrite, temp, hidden):
		"""
		Create a new chat channel object

		name -- channel name
		description -- channel description
		publicRead -- bool, if true channel can be read by everyone, if false it can be read only by mods/admins
		publicWrite -- bool, same as public read but relative to write permissions
		temp -- if True, channel will be deleted when there's no one in the channel
		hidden -- if True, channel won't be shown in channels list
		"""

		self.name = name
		self.description = description
		self.publicRead = publicRead
		self.publicWrite = publicWrite
		self.moderated = False
		self.temp = temp
		self.connectedUsers = [999]	# Fokabot is always connected to every channels (otherwise it doesn't show up in IRC users list)
		self.hidden = hidden

		# Client name (#spectator/#multiplayer)
		self.clientName = self.name
		if self.name.startswith("#spect_"):
			self.clientName = "#spectator"
		elif self.name.startswith("#multi_"):
			self.clientName = "#multiplayer"


	def userJoin(self, userID):
		"""
		Add a user to connected users

		userID -- user ID that joined the channel
		"""

		if userID not in self.connectedUsers:
			self.connectedUsers.append(userID)


	def userPart(self, userID):
		"""
		Remove a user from connected users

		userID -- user ID that left the channel
		"""

		if userID in self.connectedUsers:
			self.connectedUsers.remove(userID)

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
