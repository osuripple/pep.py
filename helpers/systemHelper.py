from objects import glob
from constants import serverPackets
from helpers import consoleHelper
import psutil
import os
import sys
import threading
import signal
from helpers import logHelper as log
from constants import bcolors
import time
import math

def dispose():
	"""
	Perform some clean up. Called on shutdown.
	:return:
	"""
	print("> Disposing server... ")
	glob.fileBuffers.flushAll()
	consoleHelper.printColored("Goodbye!", bcolors.GREEN)

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
		glob.streams.broadcast("main", serverPackets.notification(message))

	# Schedule server restart packet
	threading.Timer(sendRestartTime, glob.streams.broadcast, ["main", serverPackets.banchoRestart(delay*2*1000)]).start()
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
	dispose()
	os.execv(sys.executable, [sys.executable] + sys.argv)

def shutdownServer():
	"""Shutdown pep.py"""
	log.info("Shutting down pep.py...")
	dispose()
	sig = signal.SIGKILL if runningUnderUnix() else signal.CTRL_C_EVENT
	os.kill(os.getpid(), sig)

def getSystemInfo():
	"""
	Get a dictionary with some system/server info

	return -- ["unix", "connectedUsers", "webServer", "cpuUsage", "totalMemory", "usedMemory", "loadAverage"]
	"""
	data = {"unix": runningUnderUnix(), "connectedUsers": len(glob.tokens.tokens), "matches": len(glob.matches.matches)}

	# General stats
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
	if data["unix"]:
		data["loadAverage"] = os.getloadavg()
	else:
		data["loadAverage"] = (0,0,0)

	return data
