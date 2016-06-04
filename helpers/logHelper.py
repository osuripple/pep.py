from constants import bcolors
from helpers import discordBotHelper
from helpers import generalFunctions
from helpers.systemHelper import runningUnderUnix
from objects import glob

ENDL = "\n" if runningUnderUnix() else "\r\n"
def logMessage(message, alertType = "INFO", messageColor = bcolors.ENDC, discord = False, alertDev = False, of = None, stdout = True):
	"""
	Logs a message to stdout/discord/file

	message -- message to log
	alertType -- can be any string. Standard types: INFO, WARNING and ERRORS. Defalt: INFO
	messageColor -- message color (see constants.bcolors). Default = bcolots.ENDC (no color)
	discord -- if True, the message will be logged on #bunker channel on discord. Default: False
	alertDev -- if True, devs will receive an hl on discord. Default: False
	of -- if not None but a string, log the message to that file (inside .data folder). Eg: "warnings.txt" Default: None (don't log to file)
	stdout -- if True, print the message to stdout. Default: True
	"""
	# Get type color from alertType
	if alertType == "INFO":
		typeColor = bcolors.GREEN
	elif alertType == "WARNING":
		typeColor = bcolors.YELLOW
	elif alertType == "ERROR":
		typeColor = bcolors.RED
	elif alertType == "CHAT":
		typeColor = bcolors.BLUE
	else:
		typeColor = bcolors.ENDC

	# Message without colors
	finalMessage = "[{time}] {type} - {message}".format(time=generalFunctions.getTimestamp(), type=alertType, message=message)

	# Message with colors
	finalMessageConsole = "{typeColor}[{time}] {type}{endc} - {messageColor}{message}{endc}".format(
		time=generalFunctions.getTimestamp(),
		type=alertType,
		message=message,

		typeColor=typeColor,
		messageColor=messageColor,
		endc=bcolors.ENDC)

	# Log to console
	if stdout == True:
		print(finalMessageConsole)

	# Log to discord if needed
	if discord == True:
		discordBotHelper.sendConfidential(message, alertDev)

	# Log to file if needed
	if of != None:
		# TODO: Lock
		with open(".data/{}".format(of), "a") as f:
			f.write(finalMessage+ENDL)

def warning(message, discord = False, alertDev = False):
	"""
	Log a warning to stdout, warnings.log (always) and discord (optional)

	message -- warning message
	discord -- if True, send warning to #bunker. Optional. Default = False.
	alertDev -- if True, send al hl to devs on discord. Optional. Default = False.
	"""
	logMessage(message, "WARNING", bcolors.YELLOW, discord, alertDev, "warnings.txt")

def error(message, discord = False, alertDev = True):
	"""
	Log an error to stdout, errors.log (always) and discord (optional)

	message -- error message
	discord -- if True, send error to #bunker. Optional. Default = False.
	alertDev -- if True, send al hl to devs on discord. Optional. Default = False.
	"""
	logMessage(message, "ERROR", bcolors.RED, discord, alertDev, "errors.txt")

def info(message, discord = False, alertDev = False):
	"""
	Log an error to stdout (and info.log)

	message -- info message
	discord -- if True, send error to #bunker. Optional. Default = False.
	alertDev -- if True, send al hl to devs on discord. Optional. Default = False.
	"""
	logMessage(message, "INFO", bcolors.ENDC, discord, alertDev, "info.txt")

def debug(message):
	"""
	Log a debug message to stdout and debug.log if server is running in debug mode

	message -- debug message
	"""
	if glob.debug == True:
		logMessage(message, "DEBUG", bcolors.PINK, of="debug.txt")

def chat(message):
	"""
	Log public messages to stdout and chatlog_public.txt

	message -- chat message
	"""
	logMessage(message, "CHAT", bcolors.BLUE, of="chatlog_public.txt")

def pm(message):
	"""
	Log private messages to stdout and chatlog_private.txt

	message -- chat message
	"""
	logMessage(message, "CHAT", bcolors.BLUE, of="chatlog_private.txt")
