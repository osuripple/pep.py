"""
This file has been _rewritten_ taking by reference code from
miniircd (https://github.com/jrosdahl/miniircd)
by Joel Rosdahl, licensed under the GNU GPL 2 License.

Most of the reference code from miniircd was used for the low-level logic.
The high-level code has been rewritten to make it compatible with pep.py.
"""
import hashlib
import re
import select
import socket
import sys
import time
import traceback

import raven

from common.log import logUtils as log
from common.ripple import userUtils
from helpers import chatHelper as chat
from objects import glob


class Client:
	__linesep_regexp = re.compile(r"\r?\n")

	def __init__(self, server, sock):
		"""
		Initialize a Client object

		:param server: server object
		:param sock: socket connection object
		:return:
		"""
		self.__timestamp = time.time()
		self.__readbuffer = ""
		self.__writebuffer = ""
		self.__sentPing = False
		self.__handleCommand = self.passHandler

		self.server = server
		self.socket = sock
		(self.ip, self.port) = sock.getpeername()
		self.IRCUsername = ""
		self.banchoUsername = ""
		self.supposedUsername = ""
		self.supposedUserID = 0
		self.joinedChannels = []

	def messageChannel(self, channel, command, message, includeSelf=False):
		line = ":{} {}".format(command, message)
		for _, value in self.server.clients.items():
			if channel in value.joinedChannels and (value != self or includeSelf):
				value.message(line)

	def message(self, msg):
		"""
		Add a message (basic string) to client buffer.
		This is the lowest possible level.

		:param msg: message to add
		:return:
		"""
		self.__writebuffer += msg + "\r\n"


	def writeBufferSize(self):
		"""
		Return this client's write buffer size

		:return: write buffer size
		"""
		return len(self.__writebuffer)


	def reply(self, msg):
		"""
		Add an IRC-like message to client buffer.

		:param msg: message (without IRC stuff)
		:return:
		"""
		self.message(":{} {}".format(self.server.host, msg))


	def replyCode(self, code, message, nickname="", channel=""):
		"""
		Add an IRC-like message to client buffer with code

		:param code: response code
		:param message: response message
		:param nickname: receiver nickname
		:param channel: optional
		:return:
		"""
		if nickname == "":
			nickname = self.IRCUsername
		if channel != "":
			channel = " "+channel
		self.reply("{code:03d} {nickname}{channel} :{message}".format(code=code, nickname=nickname, channel=channel, message=message))


	def reply403(self, channel):
		"""
		Add a 403 reply (no such channel) to client buffer.

		:param channel:
		:return:
		"""
		self.replyCode(403, "{} :No such channel".format(channel))


	def reply461(self, command):
		"""
		Add a 461 reply (not enough parameters) to client buffer

		:param command: name of the command that had not enough parameters
		:return:
		"""
		self.replyCode(403, "{} :Not enough parameters".format(command))


	def disconnect(self, quitmsg = "Client quit", callLogout = True):
		"""
		Disconnects this client from the IRC server

		:param quitmsg: IRC quit message. Default: 'Client quit'
		:param callLogout: if True, call logoutEvent on bancho
		:return:
		"""
		# Send error to client and close socket
		self.message("ERROR :{}".format(quitmsg))
		self.socket.close()
		log.info("[IRC] Disconnected connection from {}:{} ({})".format(self.ip, self.port, quitmsg))

		# Remove socket from server
		self.server.removeClient(self, quitmsg)

		# Bancho logout
		if callLogout and self.banchoUsername != "":
			chat.IRCDisconnect(self.IRCUsername)


	def readSocket(self):
		"""
		Read data coming from this client socket

		:return:
		"""
		try:
			# Try to read incoming data from socket
			data = self.socket.recv(2 ** 10)
			log.debug("[IRC] [{}:{}] -> {}".format(self.ip, self.port, data))
			quitmsg = "EOT"
		except socket.error as x:
			# Error while reading data, this client will be disconnected
			data = bytes()
			quitmsg = x

		if data:
			# Parse received data if needed
			self.__readbuffer += data.decode("latin_1")
			self.parseBuffer()
			self.__timestamp = time.time()
			self.__sentPing = False
		else:
			# No data, disconnect this socket
			self.disconnect(quitmsg)


	def parseBuffer(self):
		"""
		Parse self.__readbuffer, get command, arguments and call its handler

		:return:
		"""
		# Get lines from buffer
		lines = self.__linesep_regexp.split(self.__readbuffer)
		self.__readbuffer = lines[-1]
		lines = lines[:-1]

		# Process every line
		for line in lines:
			if not line:
				# Empty line. Ignore.
				continue

			# Get arguments
			x = line.split(" ", 1)

			# Command is the first argument, always uppercase
			command = x[0].upper()

			if len(x) == 1:
				# Command only, no arguments
				arguments = []
			else:
				# We have some arguments
				# Weird sorcery
				if len(x[1]) > 0 and x[1][0] == ":":
					arguments = [x[1][1:]]
				else:
					y = x[1].split(" :", 1)
					arguments = y[0].split()
					if len(y) == 2:
						arguments.append(y[1])

			# Handle command with its arguments
			self.__handleCommand(command, arguments)


	def writeSocket(self):
		"""
		Write buffer to socket

		:return:
		"""
		try:
			sent = self.socket.send(self.__writebuffer.encode())
			log.debug("[IRC] [{}:{}] <- {}".format(self.ip, self.port, self.__writebuffer[:sent]))
			self.__writebuffer = self.__writebuffer[sent:]
		except socket.error as x:
			self.disconnect(str(x))

	def checkAlive(self):
		"""
		Check if this client is still connected.
		If the client is dead, disconnect it.

		:return:
		"""
		now = time.time()
		if self.__timestamp + 180 < now:
			self.disconnect("ping timeout")
			return
		if not self.__sentPing and self.__timestamp + 90 < now:
			if self.__handleCommand == self.mainHandler:
				# Registered.
				self.message("PING :{}".format(self.server.host))
				self.__sentPing = True
			else:
				# Not registered.
				self.disconnect("ping timeout")


	def sendLusers(self):
		"""
		Send lusers response to this client

		:return:
		"""
		self.replyCode(251, "There are {} users and 0 services on 1 server".format(len(glob.tokens.tokens)))

	def sendMotd(self):
		"""
		Send MOTD to this client

		:return:
		"""
		self.replyCode(375, "- {} Message of the day - ".format(self.server.host))
		if len(self.server.motd) == 0:
			self.replyCode(422, "MOTD File is missing")
		else:
			for i in self.server.motd:
				self.replyCode(372, "- {}".format(i))
		self.replyCode(376, "End of MOTD command")

	"""""""""
	HANDLERS
	"""""""""
	def dummyHandler(self, command, arguments):
		pass

	def passHandler(self, command, arguments):
		"""PASS command handler"""
		if command == "PASS":
			if len(arguments) == 0:
				self.reply461("PASS")
			else:
				# IRC token check
				m = hashlib.md5()
				m.update(arguments[0].encode("utf-8"))
				tokenHash = m.hexdigest()
				supposedUser = glob.db.fetch("SELECT users.username, users.id FROM users LEFT JOIN irc_tokens ON users.id = irc_tokens.userid WHERE irc_tokens.token = %s LIMIT 1", [tokenHash])
				if supposedUser:
					self.supposedUsername = chat.fixUsernameForIRC(supposedUser["username"])
					self.supposedUserID = supposedUser["id"]
					self.__handleCommand = self.registerHandler
				else:
					# Wrong IRC Token
					self.reply("464 :Password incorrect")
		elif command == "QUIT":
			self.disconnect()


	def registerHandler(self, command, arguments):
		"""NICK and USER commands handler"""
		if command == "NICK":
			if len(arguments) < 1:
				self.reply("431 :No nickname given")
				return
			nick = arguments[0]

			# Make sure this is the first time we set our nickname
			if self.IRCUsername != "":
				self.reply("432 * %s :Erroneous nickname" % nick)
				return

			# Make sure the IRC token was correct:
			# (self.supposedUsername is already fixed for IRC)
			if nick.lower() != self.supposedUsername.lower():
				self.reply("464 :Password incorrect")
				return

			# Make sure that the user is not banned/restricted:
			if not userUtils.isAllowed(self.supposedUserID):
				self.reply("465 :You're banned")
				return

			# Make sure we are not connected to Bancho
			token = glob.tokens.getTokenFromUsername(chat.fixUsernameForBancho(nick), True)
			if token is not None:
				self.reply("433 * {} :Nickname is already in use".format(nick))
				return

			# Everything seems fine, set username (nickname)
			self.IRCUsername = nick	# username for IRC
			self.banchoUsername = chat.fixUsernameForBancho(self.IRCUsername)	# username for bancho

			# Disconnect other IRC clients from the same user
			for _, value in self.server.clients.items():
				if value.IRCUsername.lower() == self.IRCUsername.lower() and value != self:
					value.disconnect(quitmsg="Connected from another client")
					return
		elif command == "USER":
			# Ignore USER command, we use nickname only
			return
		elif command == "QUIT":
			# Disconnect if we have received a QUIT command
			self.disconnect()
			return
		else:
			# Ignore any other command while logging in
			return

		# If we now have a valid username, connect to bancho and send IRC welcome stuff
		if self.IRCUsername != "":
			# Bancho connection
			chat.IRCConnect(self.banchoUsername)

			# IRC reply
			self.replyCode(1, "Welcome to the Internet Relay Network")
			self.replyCode(2, "Your host is {}, running version pep.py-{}".format(self.server.host, glob.VERSION))
			self.replyCode(3, "This server was created since the beginning")
			self.replyCode(4, "{} pep.py-{} o o".format(self.server.host, glob.VERSION))
			self.sendLusers()
			self.sendMotd()
			self.__handleCommand = self.mainHandler

	def quitHandler(self, _, arguments):
		"""QUIT command handler"""
		self.disconnect(self.IRCUsername if len(arguments) < 1 else arguments[0])

	def joinHandler(self, _, arguments):
		"""JOIN command handler"""
		if len(arguments) < 1:
			self.reply461("JOIN")
			return

		# Get bancho token object
		token = glob.tokens.getTokenFromUsername(self.banchoUsername)
		if token is None:
			return

		# TODO: Part all channels
		if arguments[0] == "0":
			'''for (channelname, channel) in self.channels.items():
				self.message_channel(channel, "PART", channelname, True)
				self.channel_log(channel, "left", meta=True)
				server.remove_member_from_channel(self, channelname)
			self.channels = {}
			return'''
			return

		# Get channels to join list
		channels = arguments[0].split(",")

		for channel in channels:
			# Make sure we are not already in that channel
			# (we already check this bancho-side, but we need to do it
			# also here k maron)
			if channel.lower() in token.joinedChannels:
				continue

			# Attempt to join the channel
			response = chat.IRCJoinChannel(self.banchoUsername, channel)
			if response == 0:
				# Joined successfully
				self.joinedChannels.append(channel)

				# Let everyone in this channel know that we've joined
				self.messageChannel(channel, "{} JOIN".format(self.IRCUsername), channel, True)

				# Send channel description (topic)
				description = glob.channels.channels[channel].description
				if description == "":
					self.replyCode(331, "No topic is set", channel=channel)
				else:
					self.replyCode(332, description, channel=channel)

				# Build connected users list
				if "chat/{}".format(channel) not in glob.streams.streams:
					self.reply403(channel)
					continue
				users = glob.streams.streams["chat/{}".format(channel)].clients
				usernames = []
				for user in users:
					if user not in glob.tokens.tokens:
						continue
					usernames.append(chat.fixUsernameForIRC(glob.tokens.tokens[user].username))
				usernames = " ".join(usernames)

				# Send IRC users list
				self.replyCode(353, usernames, channel="= {}".format(channel))
				self.replyCode(366, "End of NAMES list", channel=channel)
			elif response == 403:
				# Channel doesn't exist (or no read permissions)
				self.reply403(channel)
				continue

	def partHandler(self, _, arguments):
		"""PART command handler"""
		if len(arguments) < 1:
			self.reply461("PART")
			return

		# Get bancho token object
		token = glob.tokens.getTokenFromUsername(self.banchoUsername)
		if token is None:
			return

		# Get channels to part list
		channels = arguments[0].split(",")

		for channel in channels:
			# Make sure we in that channel
			# (we already check this bancho-side, but we need to do it
			# also here k maron)
			if channel.lower() not in token.joinedChannels:
				continue

			# Attempt to part the channel
			response = chat.IRCPartChannel(self.banchoUsername, channel)
			if response == 0:
				# No errors, remove channel from joinedChannels
				self.joinedChannels.remove(channel)
			elif response == 403:
				self.reply403(channel)
			elif response == 442:
				self.replyCode(442, "You're not on that channel", channel=channel)



	def noticePrivmsgHandler(self, command, arguments):
		"""NOTICE and PRIVMSG commands handler (same syntax)"""
		# Syntax check
		if len(arguments) == 0:
			self.replyCode(411, "No recipient given ({})".format(command))
			return
		if len(arguments) == 1:
			self.replyCode(412, "No text to send")
			return
		recipientIRC = arguments[0]
		message = arguments[1]

		# Send the message to bancho and reply
		if not recipientIRC.startswith("#"):
			recipientBancho = chat.fixUsernameForBancho(recipientIRC)
		else:
			recipientBancho = recipientIRC
		response = chat.sendMessage(self.banchoUsername, recipientBancho, message, toIRC=False)
		if response == 404:
			self.replyCode(404, "Cannot send to channel", channel=recipientIRC)
			return
		elif response == 403:
			self.replyCode(403, "No such channel", channel=recipientIRC)
			return
		elif response == 401:
			self.replyCode(401, "No such nick/channel", channel=recipientIRC)
			return

		# Send the message to IRC and bancho
		if recipientIRC.startswith("#"):
			# Public message (IRC)
			if recipientIRC not in glob.channels.channels:
				self.replyCode(401, "No such nick/channel", channel=recipientIRC)
				return
			for _, value in self.server.clients.items():
				if recipientIRC in value.joinedChannels and value != self:
					value.message(":{} PRIVMSG {} :{}".format(self.IRCUsername, recipientIRC, message))
		else:
			# Private message (IRC)
			for _, value in self.server.clients.items():
				if value.IRCUsername == recipientIRC:
					value.message(":{} PRIVMSG {} :{}".format(self.IRCUsername, recipientIRC, message))

	def motdHandler(self, command, arguments):
		"""MOTD command handler"""
		self.sendMotd()

	def lusersHandler(self, command, arguments):
		"""LUSERS command handler"""
		self.sendLusers()

	def pingHandler(self, _, arguments):
		"""PING command handler"""
		if len(arguments) < 1:
			self.replyCode(409, "No origin specified")
			return
		self.reply("PONG {} :{}".format(self.server.host, arguments[0]))

	def pongHandler(self, command, arguments):
		"""(fake) PONG command handler"""
		pass

	def awayHandler(self, _, arguments):
		"""AWAY command handler"""
		response = chat.IRCAway(self.banchoUsername, " ".join(arguments))
		self.replyCode(response, "You are no longer marked as being away" if response == 305 else "You have been marked as being away")

	def mainHandler(self, command, arguments):
		"""
		Handler for post-login commands
		"""
		handlers = {
			"AWAY": self.awayHandler,
			#"ISON": ison_handler,
			"JOIN": self.joinHandler,
			#"LIST": list_handler,
			"LUSERS": self.lusersHandler,
			#"MODE": mode_handler,
			"MOTD": self.motdHandler,
			#"NICK": nick_handler,
			#"NOTICE": notice_and_privmsg_handler,
			"PART": self.partHandler,
			"PING": self.pingHandler,
			"PONG": self.pongHandler,
			"PRIVMSG": self.noticePrivmsgHandler,
			"QUIT": self.quitHandler,
			#"TOPIC": topic_handler,
			#"WALLOPS": wallops_handler,
			#"WHO": who_handler,
			#"WHOIS": whois_handler,
			"USER": self.dummyHandler,
		}
		try:
			handlers[command](command, arguments)
		except KeyError:
			self.replyCode(421, "Unknown command ({})".format(command))


class Server:
	def __init__(self, port):
		self.host = glob.conf.config["irc"]["hostname"]
		self.port = port
		self.clients = {}  # Socket - - > Client instance.
		self.motd = ["Welcome to pep.py's embedded IRC server!", "This is a VERY simple IRC server and it's still in beta.", "Expect things to crash and not work as expected :("]

	def forceDisconnection(self, username, isBanchoUsername=True):
		"""
		Disconnect someone from IRC if connected

		:param username: victim
		:param isBanchoUsername: if True, username is a bancho username, else convert it to a bancho username
		:return:
		"""
		for _, value in self.clients.items():
			if (value.IRCUsername == username and not isBanchoUsername) or (value.banchoUsername == username and isBanchoUsername):
				value.disconnect(callLogout=False)
				break # or dictionary changes size during iteration

	def banchoJoinChannel(self, username, channel):
		"""
		Let every IRC client connected to a specific client know that 'username' joined the channel from bancho

		:param username: username of bancho user
		:param channel: joined channel name
		:return:
		"""
		username = chat.fixUsernameForIRC(username)
		for _, value in self.clients.items():
			if channel in value.joinedChannels:
				value.message(":{} JOIN {}".format(username, channel))

	def banchoPartChannel(self, username, channel):
		"""
		Let every IRC client connected to a specific client know that 'username' parted the channel from bancho

		:param username: username of bancho user
		:param channel: joined channel name
		:return:
		"""
		username = chat.fixUsernameForIRC(username)
		for _, value in self.clients.items():
			if channel in value.joinedChannels:
				value.message(":{} PART {}".format(username, channel))

	def banchoMessage(self, fro, to, message):
		"""
		Send a message to IRC when someone sends it from bancho

		:param fro: sender username
		:param to: receiver username
		:param message: text of the message
		:return:
		"""
		fro = chat.fixUsernameForIRC(fro)
		to = chat.fixUsernameForIRC(to)
		if to.startswith("#"):
			# Public message
			for _, value in self.clients.items():
				if to in value.joinedChannels and value.IRCUsername != fro:
					value.message(":{} PRIVMSG {} :{}".format(fro, to, message))
		else:
			# Private message
			for _, value in self.clients.items():
				if value.IRCUsername == to and value.IRCUsername != fro:
					value.message(":{} PRIVMSG {} :{}".format(fro, to, message))


	def removeClient(self, client, _):
		"""
		Remove a client from connected clients

		:param client: client object
		:return:
		"""
		if client.socket in self.clients:
			del self.clients[client.socket]

	def start(self):
		"""
		Start IRC server main loop

		:return:
		"""
		# Sentry
		sentryClient = None
		if glob.sentry:
			sentryClient = raven.Client(glob.conf.config["sentry"]["ircdsn"])

		serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		try:
			serversocket.bind(("0.0.0.0", self.port))
		except socket.error as e:
			log.error("[IRC] Could not bind port {}:{}".format(self.port, e))
			sys.exit(1)
		serversocket.listen(5)
		lastAliveCheck = time.time()

		# Main server loop
		while True:
			try:
				(iwtd, owtd, ewtd) = select.select(
					[serversocket] + [x.socket for x in self.clients.values()],
					[x.socket for x in self.clients.values()
					 if x.writeBufferSize() > 0],
					[],
					1)

				# Handle incoming connections
				for x in iwtd:
					if x in self.clients:
						self.clients[x].readSocket()
					else:
						(conn, addr) = x.accept()
						try:
							self.clients[conn] = Client(self, conn)
							log.info("[IRC] Accepted connection from {}:{}".format(addr[0], addr[1]))
						except socket.error:
							try:
								conn.close()
							except:
								pass

				# Handle outgoing connections
				for x in owtd:
					if x in self.clients:  # client may have been disconnected
						self.clients[x].writeSocket()

				# Make sure all IRC clients are still connected
				now = time.time()
				if lastAliveCheck + 10 < now:
					for client in list(self.clients.values()):
						client.checkAlive()
					lastAliveCheck = now
			except:
				log.error("[IRC] Unknown error!\n```\n{}\n{}```".format(sys.exc_info(), traceback.format_exc()))
				if glob.sentry and sentryClient is not None:
					sentryClient.captureException()

def main(port=6667):
	"""
	Create and start an IRC server

	:param port: IRC port. Default: 6667
	:return:
	"""
	glob.ircServer = Server(port)
	glob.ircServer.start()
