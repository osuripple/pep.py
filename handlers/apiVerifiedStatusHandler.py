import json
from objects import glob
from constants import exceptions
import bottle

@bottle.route("/api/v1/verifiedStatus")
def GETApiVerifiedStatus():
	statusCode = 400
	data = {"message": "unknown error"}
	try:
		# Check arguments
		if "u" not in bottle.request.query:
			raise exceptions.invalidArgumentsException()

		# Get userID and its verified cache thing
		# -1: Not in cache
		# 0: Not verified (multiacc)
		# 1: Verified
		userID = bottle.request.query["u"]
		callback = None
		if "callback" in bottle.request.query:
			callback = bottle.request.query["callback"]
		data["result"] = -1 if userID not in glob.verifiedCache else glob.verifiedCache[userID]

		# Status code and message
		statusCode = 200
		data["message"] = "ok"
	except exceptions.invalidArgumentsException:
		statusCode = 400
		data["message"] = "missing required arguments"
	finally:
		# Add status code to data
		data["status"] = statusCode

		# Send response
		bottle.response.add_header("Access-Control-Allow-Origin", "*")
		bottle.response.add_header("Content-Type", "application/json")

		# jquery meme
		output = ""
		if callback != None:
			output += callback+"("
		output += json.dumps(data)
		if callback != None:
			output += ")"

		bottle.response.status = statusCode
		yield output
