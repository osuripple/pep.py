import datetime
import gzip
import sys
import traceback

import tornado.gen
import tornado.web
from raven.contrib.tornado import SentryMixin

from common.log import logUtils as log
from common.web import requestsManager
from constants import exceptions
from constants import packetIDs
from constants import serverPackets
from events import cantSpectateEvent
from events import changeActionEvent
from events import changeMatchModsEvent
from events import changeMatchPasswordEvent
from events import changeMatchSettingsEvent
from events import changeSlotEvent
from events import channelJoinEvent
from events import channelPartEvent
from events import createMatchEvent
from events import friendAddEvent
from events import friendRemoveEvent
from events import joinLobbyEvent
from events import joinMatchEvent
from events import loginEvent
from events import logoutEvent
from events import matchChangeTeamEvent
from events import matchCompleteEvent
from events import matchFailedEvent
from events import matchFramesEvent
from events import matchHasBeatmapEvent
from events import matchInviteEvent
from events import matchLockEvent
from events import matchNoBeatmapEvent
from events import matchPlayerLoadEvent
from events import matchReadyEvent
from events import matchSkipEvent
from events import matchStartEvent
from events import matchTransferHostEvent
from events import partLobbyEvent
from events import partMatchEvent
from events import requestStatusUpdateEvent
from events import sendPrivateMessageEvent
from events import sendPublicMessageEvent
from events import setAwayMessageEvent
from events import spectateFramesEvent
from events import startSpectatingEvent
from events import stopSpectatingEvent
from events import userPanelRequestEvent
from events import userStatsRequestEvent
from events import tournamentMatchInfoRequestEvent
from events import tournamentJoinMatchChannelEvent
from events import tournamentLeaveMatchChannelEvent
from helpers import packetHelper
from objects import glob
from common.sentry import sentry


class handler(requestsManager.asyncRequestHandler):
	@tornado.web.asynchronous
	@tornado.gen.engine
	@sentry.captureTornado
	def asyncPost(self):
		# Track time if needed
		if glob.outputRequestTime:
			# Start time
			st = datetime.datetime.now()

		# Client's token string and request data
		requestTokenString = self.request.headers.get("osu-token")
		requestData = self.request.body

		# Server's token string and request data
		responseTokenString = "ayy"
		responseData = bytes()

		if requestTokenString is None:
			# No token, first request. Handle login.
			responseTokenString, responseData = loginEvent.handle(self)
		else:
			userToken = None	# default value
			try:
				# This is not the first packet, send response based on client's request
				# Packet start position, used to read stacked packets
				pos = 0

				# Make sure the token exists
				if requestTokenString not in glob.tokens.tokens:
					raise exceptions.tokenNotFoundException()

				# Token exists, get its object and lock it
				userToken = glob.tokens.tokens[requestTokenString]
				userToken.processingLock.acquire()

				# Keep reading packets until everything has been read
				while pos < len(requestData):
					# Get packet from stack starting from new packet
					leftData = requestData[pos:]

					# Get packet ID, data length and data
					packetID = packetHelper.readPacketID(leftData)
					dataLength = packetHelper.readPacketLength(leftData)
					packetData = requestData[pos:(pos+dataLength+7)]

					# Console output if needed
					if glob.outputPackets and packetID != 4:
						log.debug("Incoming packet ({})({}):\n\nPacket code: {}\nPacket length: {}\nSingle packet data: {}\n".format(requestTokenString, userToken.username, str(packetID), str(dataLength), str(packetData)))

					# Event handler
					def handleEvent(ev):
						def wrapper():
							ev.handle(userToken, packetData)
						return wrapper

					eventHandler = {
						packetIDs.client_changeAction: handleEvent(changeActionEvent),
						packetIDs.client_logout: handleEvent(logoutEvent),
						packetIDs.client_friendAdd: handleEvent(friendAddEvent),
						packetIDs.client_friendRemove: handleEvent(friendRemoveEvent),
						packetIDs.client_userStatsRequest: handleEvent(userStatsRequestEvent),
						packetIDs.client_requestStatusUpdate: handleEvent(requestStatusUpdateEvent),
						packetIDs.client_userPanelRequest: handleEvent(userPanelRequestEvent),

						packetIDs.client_channelJoin: handleEvent(channelJoinEvent),
						packetIDs.client_channelPart: handleEvent(channelPartEvent),
						packetIDs.client_sendPublicMessage: handleEvent(sendPublicMessageEvent),
						packetIDs.client_sendPrivateMessage: handleEvent(sendPrivateMessageEvent),
						packetIDs.client_setAwayMessage: handleEvent(setAwayMessageEvent),

						packetIDs.client_startSpectating: handleEvent(startSpectatingEvent),
						packetIDs.client_stopSpectating: handleEvent(stopSpectatingEvent),
						packetIDs.client_cantSpectate: handleEvent(cantSpectateEvent),
						packetIDs.client_spectateFrames: handleEvent(spectateFramesEvent),

						packetIDs.client_joinLobby: handleEvent(joinLobbyEvent),
						packetIDs.client_partLobby: handleEvent(partLobbyEvent),
						packetIDs.client_createMatch: handleEvent(createMatchEvent),
						packetIDs.client_joinMatch: handleEvent(joinMatchEvent),
						packetIDs.client_partMatch: handleEvent(partMatchEvent),
						packetIDs.client_matchChangeSlot: handleEvent(changeSlotEvent),
						packetIDs.client_matchChangeSettings: handleEvent(changeMatchSettingsEvent),
						packetIDs.client_matchChangePassword: handleEvent(changeMatchPasswordEvent),
						packetIDs.client_matchChangeMods: handleEvent(changeMatchModsEvent),
						packetIDs.client_matchReady: handleEvent(matchReadyEvent),
						packetIDs.client_matchNotReady: handleEvent(matchReadyEvent),
						packetIDs.client_matchLock: handleEvent(matchLockEvent),
						packetIDs.client_matchStart: handleEvent(matchStartEvent),
						packetIDs.client_matchLoadComplete: handleEvent(matchPlayerLoadEvent),
						packetIDs.client_matchSkipRequest: handleEvent(matchSkipEvent),
						packetIDs.client_matchScoreUpdate: handleEvent(matchFramesEvent),
						packetIDs.client_matchComplete: handleEvent(matchCompleteEvent),
						packetIDs.client_matchNoBeatmap: handleEvent(matchNoBeatmapEvent),
						packetIDs.client_matchHasBeatmap: handleEvent(matchHasBeatmapEvent),
						packetIDs.client_matchTransferHost: handleEvent(matchTransferHostEvent),
						packetIDs.client_matchFailed: handleEvent(matchFailedEvent),
						packetIDs.client_matchChangeTeam: handleEvent(matchChangeTeamEvent),
						packetIDs.client_invite: handleEvent(matchInviteEvent),

						packetIDs.client_tournamentMatchInfoRequest: handleEvent(tournamentMatchInfoRequestEvent),
						packetIDs.client_tournamentJoinMatchChannel: handleEvent(tournamentJoinMatchChannelEvent),
						packetIDs.client_tournamentLeaveMatchChannel: handleEvent(tournamentLeaveMatchChannelEvent),
					}

					# Packets processed if in restricted mode.
					# All other packets will be ignored if the user is in restricted mode
					packetsRestricted = [
						packetIDs.client_logout,
						packetIDs.client_userStatsRequest,
						packetIDs.client_requestStatusUpdate,
						packetIDs.client_userPanelRequest,
						packetIDs.client_changeAction,
						packetIDs.client_channelJoin,
						packetIDs.client_channelPart,
					]

					# Process/ignore packet
					if packetID != 4:
						if packetID in eventHandler:
							if not userToken.restricted or (userToken.restricted and packetID in packetsRestricted):
								eventHandler[packetID]()
							else:
								log.warning("Ignored packet id from {} ({}) (user is restricted)".format(requestTokenString, packetID))
						else:
							log.warning("Unknown packet id from {} ({})".format(requestTokenString, packetID))

					# Update pos so we can read the next stacked packet
					# +7 because we add packet ID bytes, unused byte and data length bytes
					pos += dataLength+7

				# Token queue built, send it
				responseTokenString = userToken.token
				responseData = userToken.queue
				userToken.resetQueue()
			except exceptions.tokenNotFoundException:
				# Token not found. Disconnect that user
				responseData = serverPackets.loginError()
				responseData += serverPackets.notification("Whoops! Something went wrong, please login again.")
				log.warning("Received packet from unknown token ({}).".format(requestTokenString))
				log.info("{} has been disconnected (invalid token)".format(requestTokenString))
			finally:
				# Unlock token
				if userToken is not None:
					# Update ping time for timeout
					userToken.updatePingTime()
					# Release processing lock
					userToken.processingLock.release()
					# Delete token if kicked
					if userToken.kicked:
						glob.tokens.deleteToken(userToken)

		if glob.outputRequestTime:
			# End time
			et = datetime.datetime.now()

			# Total time:
			tt = float((et.microsecond-st.microsecond)/1000)
			log.debug("Request time: {}ms".format(tt))

		# Send server's response to client
		# We don't use token object because we might not have a token (failed login)
		if glob.gzip:
			# First, write the gzipped response
			self.write(gzip.compress(responseData, int(glob.conf.config["server"]["gziplevel"])))

			# Then, add gzip headers
			self.add_header("Vary", "Accept-Encoding")
			self.add_header("Content-Encoding", "gzip")
		else:
			# First, write the response
			self.write(responseData)

		# Add all the headers AFTER the response has been written
		self.set_status(200)
		self.add_header("cho-token", responseTokenString)
		self.add_header("cho-protocol", "19")
		self.add_header("Connection", "keep-alive")
		self.add_header("Keep-Alive", "timeout=5, max=100")
		self.add_header("Content-Type", "text/html; charset=UTF-8")

	@tornado.web.asynchronous
	@tornado.gen.engine
	def asyncGet(self):
		html = 	"<html><head><title>MA MAURO ESISTE?</title><style type='text/css'>body{width:30%}</style></head><body><pre>"
		html += "           _                 __<br>"
		html += "          (_)              /  /<br>"
		html += "   ______ __ ____   ____  /  /____<br>"
		html += "  /  ___/  /  _  \\/  _  \\/  /  _  \\<br>"
		html += " /  /  /  /  /_) /  /_) /  /  ____/<br>"
		html += "/__/  /__/  .___/  .___/__/ \\_____/<br>"
		html += "        /  /   /  /<br>"
		html += "       /__/   /__/<br>"
		html += "<b>PYTHON > ALL VERSION</b><br><br>"
		html += "<marquee style='white-space:pre;'><br>"
		html += "                          .. o  .<br>"
		html += "                         o.o o . o<br>"
		html += "                        oo...<br>"
		html += "                    __[]__<br>"
		html += "    phwr-->  _\\:D/_/o_o_o_|__     <span style=\"font-family: 'Comic Sans MS'; font-size: 8pt;\">u wot m8</span><br>"
		html += "             \\\"\"\"\"\"\"\"\"\"\"\"\"\"\"/<br>"
		html += "              \\ . ..  .. . /<br>"
		html += "^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^<br>"
		html += "</marquee><br><strike>reverse engineering a protocol impossible to reverse engineer since always</strike><br>we are actually reverse engineering bancho successfully. for the third time.<br><br><i>&copy; Ripple team, 2016</i></pre></body></html>"
		self.write(html)