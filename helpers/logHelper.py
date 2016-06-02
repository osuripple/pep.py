from constants import bcolors
from helpers import discordBotHelper
from helpers import generalFunctions

def logMessage(message, alertType = INFO, messageColor = bcolors.ENDC, discord = False, alertDev = False, of = None):
	"""
	Logs a message to stdout/discord/file

	message -- message to log
	alertType -- can be any string. Standard types: INFO, WARNING and ERRORS. Defalt: INFO
	messageColor -- message color (see constants.bcolors). Default = bcolots.ENDC (no color)
	discord -- if True, the message will be logged on #bunker channel on discord. Default: False
	alertDev -- if True, devs will receive an hl on discord. Default: False
	of -- if not None but a string, log the message to that file (inside .data folder). Eg: "warnings.txt" Default: None (don't log to file)
	"""

	# Get type color from alertType
	if alertType == "INFO":
		typeColor = bcolors.GREEN
	elif alertType == "WARNING":
		typeColor = bcolors.YELLOW
	elif typeColor == "ERROR":
		typeColor = bcolors.RED
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

	# Always log to console
	print(finalMessageConsole)

	# Log to discord if needed
	if discord == True:
		discordBotHelper.sendConfidential(message, alertDev)

	# Log to file if needed
	if of != None:
		# TODO: Lock
		with open(".data/{}".format(of), "a") as f:
			f.write(finalMessage)

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
