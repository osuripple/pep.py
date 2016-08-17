from constants import exceptions
import json
from objects import glob
from helpers import chatHelper
import bottle

@bottle.route("/api/v1/fokabotMessage")
def GETApiFokabotMessage():
	statusCode = 400
	data = {"message": "unknown error"}
	try:
		# Check arguments
		if "k" not in bottle.request.query or "to" not in bottle.request.query or "msg" not in bottle.request.query:
			raise exceptions.invalidArgumentsException()

		# Check ci key
		key = bottle.request.query["k"]
		if key is None or key != glob.conf.config["server"]["cikey"]:
			raise exceptions.invalidArgumentsException()

		# Send chat message
		chatHelper.sendMessage("FokaBot", bottle.request.query["to"], bottle.request.query["msg"])

		# Status code and message
		statusCode = 200
		data["message"] = "ok"
	except exceptions.invalidArgumentsException:
		statusCode = 400
		data["message"] = "invalid parameters"
	finally:
		# Add status code to data
		data["status"] = statusCode

		# Send response
		bottle.response.status = statusCode
		bottle.response.add_header("Content-Type", "application/json")
		yield json.dumps(data)
