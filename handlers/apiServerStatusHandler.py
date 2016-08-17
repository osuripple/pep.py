import json
from objects import glob
import bottle

@bottle.route("/api/v1/serverStatus")
def GETApiServerStatus():
	statusCode = 400
	data = {"message": "unknown error"}
	try:
		# Get online users count
		data["result"] = -1 if glob.restarting == True else 1

		# Status code and message
		statusCode = 200
		data["message"] = "ok"
	finally:
		# Add status code to data
		data["status"] = statusCode

		# Send response
		bottle.response.status = statusCode
		bottle.response.add_header("Content-Type", "application/json")
		yield json.dumps(data)
