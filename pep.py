"""Hello, pep.py here, ex-owner of ripple and prime minister of Ripwot."""
import os
import sys
import threading
from multiprocessing.pool import ThreadPool

import tornado.gen
import tornado.httpserver
import tornado.ioloop
import tornado.web
from raven.contrib.tornado import AsyncSentryClient

from common import generalUtils
from common.constants import bcolors
from common.db import dbConnector
from common.log import logUtils as log
from common.ripple import userUtils
from common.web import schiavo
from handlers import apiFokabotMessageHandler
from handlers import apiIsOnlineHandler
from handlers import apiOnlineUsersHandler
from handlers import apiServerStatusHandler
from handlers import apiVerifiedStatusHandler
from handlers import ciTriggerHandler
from handlers import mainHandler
from helpers import configHelper
from helpers import consoleHelper
from helpers import systemHelper as system
from irc import ircserver
from objects import banchoConfig
from objects import chatFilters
from objects import fokabot
from objects import glob


def make_app():
	return tornado.web.Application([
		(r"/", mainHandler.handler),
		(r"/api/v1/isOnline", apiIsOnlineHandler.handler),
		(r"/api/v1/onlineUsers", apiOnlineUsersHandler.handler),
		(r"/api/v1/serverStatus", apiServerStatusHandler.handler),
		(r"/api/v1/ciTrigger", ciTriggerHandler.handler),
		(r"/api/v1/verifiedStatus", apiVerifiedStatusHandler.handler),
		(r"/api/v1/fokabotMessage", apiFokabotMessageHandler.handler)
	])

if __name__ == "__main__":
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
			consoleHelper.printNoNl("> Connecting to MySQL database...")
			glob.db = dbConnector.db(glob.conf.config["db"]["host"], glob.conf.config["db"]["username"], glob.conf.config["db"]["password"], glob.conf.config["db"]["database"], int(glob.conf.config["db"]["workers"]))
			consoleHelper.printNoNl(" ")
			consoleHelper.printDone()
		except:
			# Exception while connecting to db
			consoleHelper.printError()
			consoleHelper.printColored("[!] Error while connection to database. Please check your config.ini and run the server again", bcolors.RED)
			raise

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
		except:
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

		# Initialize chat channels
		print("> Initializing chat channels... ")
		glob.channels.loadChannels()
		consoleHelper.printDone()

		# Initialize stremas
		consoleHelper.printNoNl("> Creating main stream... ")
		glob.streams.add("main")
		consoleHelper.printDone()

		# Start fokabot
		consoleHelper.printNoNl("> Connecting FokaBot... ")
		fokabot.connect()
		consoleHelper.printDone()

		# Initialize user timeout check loop
		consoleHelper.printNoNl("> Initializing user timeout check loop... ")
		glob.tokens.usersTimeoutCheckLoop()
		consoleHelper.printDone()

		# Initialize spam protection reset loop
		consoleHelper.printNoNl("> Initializing spam protection reset loop... ")
		glob.tokens.spamProtectionResetLoop()
		consoleHelper.printDone()

		# Cache user ids
		consoleHelper.printNoNl("> Caching user IDs... ")
		userUtils.cacheUserIDs()
		consoleHelper.printDone()

		# Localize warning
		glob.localize = generalUtils.stringToBool(glob.conf.config["localize"]["enable"])
		if not glob.localize:
			consoleHelper.printColored("[!] Warning! Users localization is disabled!", bcolors.YELLOW)

		# Discord
		if generalUtils.stringToBool(glob.conf.config["discord"]["enable"]):
			glob.schiavo = schiavo.schiavo(glob.conf.config["discord"]["boturl"])
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
				glob.application.sentry_client = AsyncSentryClient(glob.conf.config["sentry"]["banchodns"], release=glob.VERSION)
			else:
				consoleHelper.printColored("[!] Warning! Sentry logging is disabled!", bcolors.YELLOW)
		except:
			consoleHelper.printColored("[!] Error while starting sentry client! Please check your config.ini and run the server again", bcolors.RED)

		# Cloudflare memes
		glob.cloudflare = generalUtils.stringToBool(glob.conf.config["server"]["cloudflare"])

		# IRC start message and console output
		glob.irc = generalUtils.stringToBool(glob.conf.config["irc"]["enable"])
		if glob.irc:
			# IRC port
			try:
				ircPort = int(glob.conf.config["irc"]["port"])
			except:
				consoleHelper.printColored("[!] Invalid IRC port! Please check your config.ini and run the server again", bcolors.RED)
			log.logMessage("IRC server started!", discord=True, of="info.txt", stdout=False)
			consoleHelper.printColored("> IRC server listening on 127.0.0.1:{}...".format(ircPort), bcolors.GREEN)
			threading.Thread(target=lambda: ircserver.main(port=ircPort)).start()
		else:
			consoleHelper.printColored("[!] Warning! IRC server is disabled!", bcolors.YELLOW)

		# Server port
		try:
			serverPort = int(glob.conf.config["server"]["port"])
		except:
			consoleHelper.printColored("[!] Invalid server port! Please check your config.ini and run the server again", bcolors.RED)

		# Server start message and console output
		log.logMessage("Server started!", discord=True, of="info.txt", stdout=False)
		consoleHelper.printColored("> Tornado listening for HTTP(s) clients on 127.0.0.1:{}...".format(serverPort), bcolors.GREEN)

		# Start tornado
		glob.application.listen(serverPort)
		tornado.ioloop.IOLoop.instance().start()
	finally:
		system.dispose()