std 	= 0
taiko 	= 1
ctb 	= 2
mania 	= 3

def getGameModeForDB(gameMode):
	"""
	Convert a gamemode number to string for database table/column

	gameMode -- gameMode int or variable (ex: gameMode.std)
	return -- game mode readable string for db
	"""
	if gameMode == std:
		return "std"
	elif gameMode == taiko:
		return "taiko"
	elif gameMode == ctb:
		return "ctb"
	else:
		return "mania"

def getGameModeForPrinting(gameMode):
	"""
	Convert a gamemode number to string for showing to a user (e.g. !last)

	gameMode -- gameMode int or variable (ex: gameMode.std)
	return -- game mode readable string for a human
	"""
	if gameMode == std:
		return "osu!"
	elif gameMode == taiko:
		return "Taiko"
	elif gameMode == ctb:
		return "CatchTheBeat"
	else:
		return "osu!mania"