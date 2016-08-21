from constants import exceptions
import json
from objects import glob
import bottle

@bottle.route("/api/v1/isOnline")
def GETApiIsOnline():
	statusCode = 400
	data = {"message": "unknown error"}
	try:
		# Check arguments
		if "u" not in bottle.request.query and "id" not in bottle.request.query:
			raise exceptions.invalidArgumentsException()

		# Get online staus
		if "u" in bottle.request.query:
			username = bottle.request.query["u"]
			data["result"] = True if glob.tokens.getTokenFromUsername(username) != None else False
		else:
			try:
				userID = int(bottle.request.query["id"])
				data["result"] = True if glob.tokens.getTokenFromUserID(userID) != None else False
			except:
				raise exceptions.invalidArgumentsException()

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
		bottle.response.status = statusCode
		bottle.response.add_header("Content-Type", "application/json")
		yield json.dumps(data)
