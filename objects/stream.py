from common.log import logUtils as log
from objects import glob

class stream:
	def __init__(self, name):
		"""
		Initialize a stream object

		:param name: stream name
		"""
		self.name = name
		self.clients = []

	def addClient(self, client=None, token=None):
		"""
		Add a client to this stream if not already in

		:param client: client (osuToken) object
		:param token: client uuid string
		:return:
		"""
		if client is None and token is None:
			return
		if client is not None:
			token = client.token
		if token not in self.clients:
			log.info("{} has joined stream {}".format(token, self.name))
			self.clients.append(token)

	def removeClient(self, client=None, token=None):
		"""
		Remove a client from this stream if in

		:param client: client (osuToken) object
		:param token: client uuid string
		:return:
		"""
		if client is None and token is None:
			return
		if client is not None:
			token = client.token
		if token in self.clients:
			log.info("{} has left stream {}".format(token, self.name))
			self.clients.remove(token)

	def broadcast(self, data, but=None):
		"""
		Send some data to all (or some) clients connected to this stream

		:param data: data to send
		:param but: array of tokens to ignore. Default: None (send to everyone)
		:return:
		"""
		if but is None:
			but = []
		for i in self.clients:
			if i in glob.tokens.tokens:
				if i not in but:
					glob.tokens.tokens[i].enqueue(data)
			else:
				self.removeClient(token=i)

	def dispose(self):
		"""
		Tell every client in this stream to leave the stream

		:return:
		"""
		for i in self.clients:
			if i in glob.tokens.tokens:
				glob.tokens.tokens[i].leaveStream(self.name)