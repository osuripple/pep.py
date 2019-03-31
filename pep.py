import os
import sys
import threading
from multiprocessing.pool import ThreadPool
import tornado.gen
import tornado.httpserver
import tornado.ioloop
import tornado.web
from raven.contrib.tornado import AsyncSentryClient
import redis

from common import generalUtils, agpl
from common.constants import bcolors
from common.db import dbConnector
from common.ddog import datadogClient
from common.log import logUtils as log
from common.redis import pubSub
from common.web import schiavo
from handlers import apiFokabotMessageHandler
from handlers import apiIsOnlineHandler
from handlers import apiOnlineUsersHandler
from handlers import apiServerStatusHandler
from handlers import apiVerifiedStatusHandler
from handlers import ciTriggerHandler
from handlers import mainHandler
from handlers import heavyHandler
from helpers import configHelper
from helpers import consoleHelper
from helpers import systemHelper as system
from irc import ircserver
from objects import banchoConfig
from objects import chatFilters
from objects import fokabot
from objects import glob
from pubSubHandlers import changeUsernameHandler, setMainMenuIconHandler

from pubSubHandlers import disconnectHandler
from pubSubHandlers import banHandler
from pubSubHandlers import notificationHandler
from pubSubHandlers import updateSilenceHandler
from pubSubHandlers import updateStatsHandler


def make_app():
	return tornado.web.Application([
		(r"/", mainHandler.handler),
		(r"/api/v1/isOnline", apiIsOnlineHandler.handler),
		(r"/api/v1/onlineUsers", apiOnlineUsersHandler.handler),
		(r"/api/v1/serverStatus", apiServerStatusHandler.handler),
		(r"/api/v1/ciTrigger", ciTriggerHandler.handler),
		(r"/api/v1/verifiedStatus", apiVerifiedStatusHandler.handler),
		(r"/api/v1/fokabotMessage", apiFokabotMessageHandler.handler),
		(r"/stress", heavyHandler.handler)
	])


if __name__ == "__main__":
	# AGPL license agreement
	try:
		agpl.check_license("ripple", "pep.py")
	except agpl.LicenseError as e:
		print(str(e))
		sys.exit(1)

	try:
		# Server start
		consoleHelper.printServerStartHeader(True)

		# Read config.ini
		consoleHelper.printNoNl("> Loading config file... ")
		glob.conf = configHelper.config("config.ini")

		if glob.conf.default:
			# We have generated a default config.ini, quit server
			consoleHelper.printWarning()
			consoleHelper.printColored("[!] config.ini not found. A default one has been generated.", bcolors.YELLOW)
			consoleHelper.printColored("[!] Please edit your config.ini and run the server again.", bcolors.YELLOW)
			sys.exit()

		# If we haven't generated a default config.ini, check if it's valid
		if not glob.conf.checkConfig():
			consoleHelper.printError()
			consoleHelper.printColored("[!] Invalid config.ini. Please configure it properly", bcolors.RED)
			consoleHelper.printColored("[!] Delete your config.ini to generate a default one", bcolors.RED)
			sys.exit()
		else:
			consoleHelper.printDone()

		# Create data folder if needed
		consoleHelper.printNoNl("> Checking folders... ")
		paths = [".data"]
		for i in paths:
			if not os.path.exists(i):
				os.makedirs(i, 0o770)
		consoleHelper.printDone()

		# Connect to db
		try:
			consoleHelper.printNoNl("> Connecting to MySQL database... ")
			glob.db = dbConnector.db(glob.conf.config["db"]["host"], glob.conf.config["db"]["username"], glob.conf.config["db"]["password"], glob.conf.config["db"]["database"], int(glob.conf.config["db"]["workers"]))
			consoleHelper.printNoNl(" ")
			consoleHelper.printDone()
		except:
			# Exception while connecting to db
			consoleHelper.printError()
			consoleHelper.printColored("[!] Error while connection to database. Please check your config.ini and run the server again", bcolors.RED)
			raise

		# Connect to redis
		try:
			consoleHelper.printNoNl("> Connecting to redis... ")
			glob.redis = redis.Redis(glob.conf.config["redis"]["host"], glob.conf.config["redis"]["port"], glob.conf.config["redis"]["database"], glob.conf.config["redis"]["password"])
			glob.redis.ping()
			consoleHelper.printNoNl(" ")
			consoleHelper.printDone()
		except:
			# Exception while connecting to db
			consoleHelper.printError()
			consoleHelper.printColored("[!] Error while connection to redis. Please check your config.ini and run the server again", bcolors.RED)
			raise

		# Empty redis cache
		try:
			# TODO: Make function or some redis meme
			glob.redis.set("ripple:online_users", 0)
			glob.redis.eval("return redis.call('del', unpack(redis.call('keys', ARGV[1])))", 0, "peppy:*")
		except redis.exceptions.ResponseError:
			# Script returns error if there are no keys starting with peppy:*
			pass

		# Save peppy version in redis
		glob.redis.set("peppy:version", glob.VERSION)

		# Load bancho_settings
		try:
			consoleHelper.printNoNl("> Loading bancho settings from DB... ")
			glob.banchoConf = banchoConfig.banchoConfig()
			consoleHelper.printDone()
		except:
			consoleHelper.printError()
			consoleHelper.printColored("[!] Error while loading bancho_settings. Please make sure the table in DB has all the required rows", bcolors.RED)
			raise

		# Delete old bancho sessions
		consoleHelper.printNoNl("> Deleting cached bancho sessions from DB... ")
		glob.tokens.deleteBanchoSessions()
		consoleHelper.printDone()

		# Create threads pool
		try:
			consoleHelper.printNoNl("> Creating threads pool... ")
			glob.pool = ThreadPool(int(glob.conf.config["server"]["threads"]))
			consoleHelper.printDone()
		except ValueError:
			consoleHelper.printError()
			consoleHelper.printColored("[!] Error while creating threads pool. Please check your config.ini and run the server again", bcolors.RED)

		try:
			consoleHelper.printNoNl("> Loading chat filters... ")
			glob.chatFilters = chatFilters.chatFilters()
			consoleHelper.printDone()
		except:
			consoleHelper.printError()
			consoleHelper.printColored("[!] Error while loading chat filters. Make sure there is a filters.txt file present", bcolors.RED)
			raise

		# Start fokabot
		consoleHelper.printNoNl("> Connecting FokaBot... ")
		fokabot.connect()
		consoleHelper.printDone()

		# Initialize chat channels
		print("> Initializing chat channels... ")
		glob.channels.loadChannels()
		consoleHelper.printDone()

		# Initialize stremas
		consoleHelper.printNoNl("> Creating packets streams... ")
		glob.streams.add("main")
		glob.streams.add("lobby")
		consoleHelper.printDone()

		# Initialize user timeout check loop
		consoleHelper.printNoNl("> Initializing user timeout check loop... ")
		glob.tokens.usersTimeoutCheckLoop()
		consoleHelper.printDone()

		# Initialize spam protection reset loop
		consoleHelper.printNoNl("> Initializing spam protection reset loop... ")
		glob.tokens.spamProtectionResetLoop()
		consoleHelper.printDone()

		# Initialize multiplayer cleanup loop
		consoleHelper.printNoNl("> Initializing multiplayer cleanup loop... ")
		glob.matches.cleanupLoop()
		consoleHelper.printDone()

		# Localize warning
		glob.localize = generalUtils.stringToBool(glob.conf.config["localize"]["enable"])
		if not glob.localize:
			consoleHelper.printColored("[!] Warning! Users localization is disabled!", bcolors.YELLOW)

		# Discord
		if generalUtils.stringToBool(glob.conf.config["discord"]["enable"]):
			glob.schiavo = schiavo.schiavo(glob.conf.config["discord"]["boturl"], "**pep.py**")
		else:
			consoleHelper.printColored("[!] Warning! Discord logging is disabled!", bcolors.YELLOW)

		# Gzip
		glob.gzip = generalUtils.stringToBool(glob.conf.config["server"]["gzip"])
		glob.gziplevel = int(glob.conf.config["server"]["gziplevel"])
		if not glob.gzip:
			consoleHelper.printColored("[!] Warning! Gzip compression is disabled!", bcolors.YELLOW)

		# Debug mode
		glob.debug = generalUtils.stringToBool(glob.conf.config["debug"]["enable"])
		glob.outputPackets = generalUtils.stringToBool(glob.conf.config["debug"]["packets"])
		glob.outputRequestTime = generalUtils.stringToBool(glob.conf.config["debug"]["time"])
		if glob.debug:
			consoleHelper.printColored("[!] Warning! Server running in debug mode!", bcolors.YELLOW)

		# Make app
		glob.application = make_app()

		# Set up sentry
		try:
			glob.sentry = generalUtils.stringToBool(glob.conf.config["sentry"]["enable"])
			if glob.sentry:
				glob.application.sentry_client = AsyncSentryClient(glob.conf.config["sentry"]["banchodsn"], release=glob.VERSION)
			else:
				consoleHelper.printColored("[!] Warning! Sentry logging is disabled!", bcolors.YELLOW)
		except:
			consoleHelper.printColored("[!] Error while starting sentry client! Please check your config.ini and run the server again", bcolors.RED)

		# Set up datadog
		try:
			if generalUtils.stringToBool(glob.conf.config["datadog"]["enable"]):
				glob.dog = datadogClient.datadogClient(
					glob.conf.config["datadog"]["apikey"],
					glob.conf.config["datadog"]["appkey"],
					[
						datadogClient.periodicCheck("online_users", lambda: len(glob.tokens.tokens)),
						datadogClient.periodicCheck("multiplayer_matches", lambda: len(glob.matches.matches)),

						#datadogClient.periodicCheck("ram_clients", lambda: generalUtils.getTotalSize(glob.tokens)),
						#datadogClient.periodicCheck("ram_matches", lambda: generalUtils.getTotalSize(glob.matches)),
						#datadogClient.periodicCheck("ram_channels", lambda: generalUtils.getTotalSize(glob.channels)),
						#datadogClient.periodicCheck("ram_file_buffers", lambda: generalUtils.getTotalSize(glob.fileBuffers)),
						#datadogClient.periodicCheck("ram_file_locks", lambda: generalUtils.getTotalSize(glob.fLocks)),
						#datadogClient.periodicCheck("ram_datadog", lambda: generalUtils.getTotalSize(glob.datadogClient)),
						#datadogClient.periodicCheck("ram_verified_cache", lambda: generalUtils.getTotalSize(glob.verifiedCache)),
						#datadogClient.periodicCheck("ram_irc", lambda: generalUtils.getTotalSize(glob.ircServer)),
						#datadogClient.periodicCheck("ram_tornado", lambda: generalUtils.getTotalSize(glob.application)),
						#datadogClient.periodicCheck("ram_db", lambda: generalUtils.getTotalSize(glob.db)),
					])
			else:
				consoleHelper.printColored("[!] Warning! Datadog stats tracking is disabled!", bcolors.YELLOW)
		except:
			consoleHelper.printColored("[!] Error while starting Datadog client! Please check your config.ini and run the server again", bcolors.RED)

		# IRC start message and console output
		glob.irc = generalUtils.stringToBool(glob.conf.config["irc"]["enable"])
		if glob.irc:
			# IRC port
			ircPort = 0
			try:
				ircPort = int(glob.conf.config["irc"]["port"])
			except ValueError:
				consoleHelper.printColored("[!] Invalid IRC port! Please check your config.ini and run the server again", bcolors.RED)
			log.logMessage("IRC server started!", discord="bunker", of="info.txt", stdout=False)
			consoleHelper.printColored("> IRC server listening on 127.0.0.1:{}...".format(ircPort), bcolors.GREEN)
			threading.Thread(target=lambda: ircserver.main(port=ircPort)).start()
		else:
			consoleHelper.printColored("[!] Warning! IRC server is disabled!", bcolors.YELLOW)

		# Server port
		serverPort = 0
		try:
			serverPort = int(glob.conf.config["server"]["port"])
		except ValueError:
			consoleHelper.printColored("[!] Invalid server port! Please check your config.ini and run the server again", bcolors.RED)

		# Server start message and console output
		log.logMessage("Server started!", discord="bunker", of="info.txt", stdout=False)
		consoleHelper.printColored("> Tornado listening for HTTP(s) clients on 127.0.0.1:{}...".format(serverPort), bcolors.GREEN)

		# Connect to pubsub channels
		pubSub.listener(glob.redis, {
			"peppy:disconnect": disconnectHandler.handler(),
			"peppy:change_username": changeUsernameHandler.handler(),
			"peppy:reload_settings": lambda x: x == b"reload" and glob.banchoConf.reload(),
			"peppy:update_cached_stats": updateStatsHandler.handler(),
			"peppy:silence": updateSilenceHandler.handler(),
			"peppy:ban": banHandler.handler(),
			"peppy:notification": notificationHandler.handler(),
			"peppy:set_main_menu_icon": setMainMenuIconHandler.handler(),
		}).start()

		# Start tornado
		glob.application.listen(serverPort)
		tornado.ioloop.IOLoop.instance().start()
	finally:
		system.dispose()