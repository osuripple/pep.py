from objects import glob

class channel:
	def __init__(self, name, description, publicRead, publicWrite, temp, hidden):
		"""
		Create a new chat channel object

		:param name: channel name
		:param description: channel description
		:param publicRead: if True, this channel can be read by everyone. If False, it can be read only by mods/admins
		:param publicWrite: same as public read, but regards writing permissions
		:param temp: if True, this channel will be deleted when there's no one in this channel
		:param hidden: if True, thic channel won't be shown in channels list
		"""
		self.name = name
		self.description = description
		self.publicRead = publicRead
		self.publicWrite = publicWrite
		self.moderated = False
		self.temp = temp
		self.hidden = hidden

		# Client name (#spectator/#multiplayer)
		self.clientName = self.name
		if self.name.startswith("#spect_"):
			self.clientName = "#spectator"
		elif self.name.startswith("#multi_"):
			self.clientName = "#multiplayer"

		# Make Foka join the channel
		fokaToken = glob.tokens.getTokenFromUserID(999)
		if fokaToken is not None:
			fokaToken.joinChannel(self)