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

	def broadcast(self, data):
		"""
		Send some data to all clients connected to this stream

		:param data: data to send
		:return:
		"""
		for i in self.clients:
			if i in glob.tokens.tokens:
				glob.tokens.tokens[i].enqueue(data)
			else:
				self.removeClient(token=i)