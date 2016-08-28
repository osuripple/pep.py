from objects import glob
from constants import serverPackets
import psutil
import os
import sys
import threading
import signal
from helpers import logHelper as log
import time
import math

def runningUnderUnix():
	"""
	Get if the server is running under UNIX or NT

	return --- True if running under UNIX, otherwise False
	"""

	return True if os.name == "posix" else False


def scheduleShutdown(sendRestartTime, restart, message = "", delay=20):
	"""
	Schedule a server shutdown/restart

	sendRestartTime -- time (seconds) to wait before sending server restart packets to every client
	restart -- if True, server will restart. if False, server will shudown
	message -- if set, send that message to every client to warn about the shutdown/restart
	"""

	# Console output
	log.info("Pep.py will {} in {} seconds!".format("restart" if restart else "shutdown", sendRestartTime+delay))
	log.info("Sending server restart packets in {} seconds...".format(sendRestartTime))

	# Send notification if set
	if message != "":
		glob.tokens.enqueueAll(serverPackets.notification(message))

	# Schedule server restart packet
	threading.Timer(sendRestartTime, glob.tokens.enqueueAll, [serverPackets.banchoRestart(delay*2*1000)]).start()
	glob.restarting = True

	# Restart/shutdown
	if restart:
		action = restartServer
	else:
		action = shutdownServer

	# Schedule actual server shutdown/restart some seconds after server restart packet, so everyone gets it
	threading.Timer(sendRestartTime+delay, action).start()


def restartServer():
	"""Restart pep.py script"""
	log.info("Restarting pep.py...")
	os.execv(sys.executable, [sys.executable] + sys.argv)


def shutdownServer():
	"""Shutdown pep.py"""
	log.info("Shutting down pep.py...")
	sig = signal.SIGKILL if runningUnderUnix() else signal.CTRL_C_EVENT
	os.kill(os.getpid(), sig)


def getSystemInfo():
	"""
	Get a dictionary with some system/server info

	return -- ["unix", "connectedUsers", "webServer", "cpuUsage", "totalMemory", "usedMemory", "loadAverage"]
	"""

	data = {}

	# Get if server is running under unix/nt
	data["unix"] = runningUnderUnix()

	# General stats
	data["connectedUsers"] = len(glob.tokens.tokens)
	data["matches"] = len(glob.matches.matches)
	delta = time.time()-glob.startTime
	days = math.floor(delta/86400)
	delta -= days*86400

	hours = math.floor(delta/3600)
	delta -= hours*3600

	minutes = math.floor(delta/60)
	delta -= minutes*60

	seconds = math.floor(delta)

	data["uptime"] = "{}d {}h {}m {}s".format(days, hours, minutes, seconds)
	data["cpuUsage"] = psutil.cpu_percent()
	memory = psutil.virtual_memory()
	data["totalMemory"] = "{0:.2f}".format(memory.total/1074000000)
	data["usedMemory"] = "{0:.2f}".format(memory.active/1074000000)

	# Unix only stats
	if data["unix"] == True:
		data["loadAverage"] = os.getloadavg()
	else:
		data["loadAverage"] = (0,0,0)

	return data
