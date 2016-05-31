"""Hello, pep.py here, ex-owner of ripple and prime minister of Ripwot."""
import sys
import os
from multiprocessing.pool import ThreadPool

# Tornado
import tornado.ioloop
import tornado.web
import tornado.httpserver
import tornado.gen

# pep.py files
from constants import bcolors
from helpers import configHelper
from helpers import discordBotHelper
from objects import glob
from objects import fokabot
from objects import banchoConfig
from handlers import mainHandler
from helpers import consoleHelper
from helpers import databaseHelperNew
from helpers import generalFunctions

def make_app():
	return tornado.web.Application([
		(r"/", mainHandler.handler)
	])

# Ci trigger
'''@app.route("/ci-trigger")
@app.route("/api/ci-trigger")
def ciTrigger():
	# Ci restart trigger

	# Get ket from GET
	key = flask.request.args.get('k')

	# Get request ip
	requestIP = flask.request.headers.get('X-Real-IP')
	if requestIP == None:
		requestIP = flask.request.remote_addr

	# Check key
	if key is None or key != glob.conf.config["ci"]["key"]:
		consoleHelper.printColored("[!] Invalid ci trigger from {}".format(requestIP), bcolors.RED)
		return flask.jsonify({"response" : "-1"})

	# Ci event triggered, schedule server shutdown
	consoleHelper.printColored("[!] Ci event triggered from {}".format(requestIP), bcolors.PINK)
	systemHelper.scheduleShutdown(5, False, "A new Bancho update is available and the server will be restarted in 5 seconds. Thank you for your patience.")

	return flask.jsonify({"response" : 1})


@app.route("/api/server-status")
def serverStatus():
	# Server status api
	# 1: Online
	# -1: Restarting
	return flask.jsonify({
		"response" : 200,
		"status" : -1 if glob.restarting == True else 1
	})

@app.route("/api/v1/isOnline")
def apiIsOnline():
	username = request.args.get("u")
	if username == None:
		result = False
	else:
		token = glob.tokens.getTokenFromUsername(username)
		result = True if token != None else False
	return flask.jsonify({
		"result": result
	})

@app.route("/api/v1/onlineUsers")
def apiOnlineUsers():
	return flask.jsonify({
		"result": len(glob.tokens.tokens)
	})

# Main bancho server
@app.route("/", methods=['GET', 'POST'])
def banchoServer():
	if flask.request.method == 'POST':


	else:
		# Not a POST request, send html page
		return responseHelper.HTMLResponse()'''


if __name__ == "__main__":
	# Server start
	consoleHelper.printServerStartHeader(True)

	# Read config.ini
	consoleHelper.printNoNl("> Loading config file... ")
	glob.conf = configHelper.config("config.ini")

	if glob.conf.default == True:
		# We have generated a default config.ini, quit server
		consoleHelper.printWarning()
		consoleHelper.printColored("[!] config.ini not found. A default one has been generated.", bcolors.YELLOW)
		consoleHelper.printColored("[!] Please edit your config.ini and run the server again.", bcolors.YELLOW)
		sys.exit()

	# If we haven't generated a default config.ini, check if it's valid
	if glob.conf.checkConfig() == False:
		consoleHelper.printError()
		consoleHelper.printColored("[!] Invalid config.ini. Please configure it properly", bcolors.RED)
		consoleHelper.printColored("[!] Delete your config.ini to generate a default one", bcolors.RED)
		sys.exit()
	else:
		consoleHelper.printDone()


	# Connect to db
	try:
		print("> Connecting to MySQL db... ")
		glob.db = databaseHelperNew.db(glob.conf.config["db"]["host"], glob.conf.config["db"]["username"], glob.conf.config["db"]["password"], glob.conf.config["db"]["database"], int(glob.conf.config["db"]["workers"]))
		consoleHelper.printDone()
	except:
		# Exception while connecting to db
		consoleHelper.printError()
		consoleHelper.printColored("[!] Error while connection to database. Please check your config.ini and run the server again", bcolors.RED)
		raise

	# Create threads pool
	try:
		consoleHelper.printNoNl("> Creating threads pool... ")
		glob.pool = ThreadPool(int(glob.conf.config["server"]["threads"]))
		consoleHelper.printDone()
	except:
		consoleHelper.printError()
		consoleHelper.printColored("[!] Error while creating threads pool. Please check your config.ini and run the server again", bcolors.RED)

	# Load bancho_settings
	try:
		consoleHelper.printNoNl("> Loading bancho settings from DB... ")
		glob.banchoConf = banchoConfig.banchoConfig()
		consoleHelper.printDone()
	except:
		consoleHelper.printError()
		consoleHelper.printColored("[!] Error while loading bancho_settings. Please make sure the table in DB has all the required rows", bcolors.RED)
		raise

	# Create data folder if needed
	consoleHelper.printNoNl("> Checking folders... ")
	paths = [".data"]
	for i in paths:
		if not os.path.exists(i):
			os.makedirs(i, 0o770)
	consoleHelper.printDone()

	# Initialize chat channels
	consoleHelper.printNoNl("> Initializing chat channels... ")
	glob.channels.loadChannels()
	consoleHelper.printDone()

	# Start fokabot
	consoleHelper.printNoNl("> Connecting FokaBot... ")
	fokabot.connect()
	consoleHelper.printDone()

	# Initialize user timeout check loop
	try:
		consoleHelper.printNoNl("> Initializing user timeout check loop... ")
		glob.tokens.usersTimeoutCheckLoop(int(glob.conf.config["server"]["timeouttime"]), int(glob.conf.config["server"]["timeoutlooptime"]))
		consoleHelper.printDone()
	except:
		consoleHelper.printError()
		consoleHelper.printColored("[!] Error while initializing user timeout check loop", bcolors.RED)
		consoleHelper.printColored("[!] Make sure that 'timeouttime' and 'timeoutlooptime' in config.ini are numbers", bcolors.RED)
		raise

	# Localize warning
	if(generalFunctions.stringToBool(glob.conf.config["server"]["localizeusers"]) == False):
		consoleHelper.printColored("[!] Warning! users localization is disabled!", bcolors.YELLOW)

	# Get server parameters from config.ini
	serverPort = int(glob.conf.config["server"]["port"])
	glob.requestTime = generalFunctions.stringToBool(glob.conf.config["server"]["outputrequesttime"])

	# Server start message and console output
	discordBotHelper.sendConfidential("w00t p00t! (pep.py started)")
	consoleHelper.printColored("> Tornado listening for clients on 127.0.0.1:{}...".format(serverPort), bcolors.GREEN)

	# Start tornado
	app = tornado.httpserver.HTTPServer(make_app())
	app.listen(serverPort)
	tornado.ioloop.IOLoop.instance().start()
