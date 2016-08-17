"""Global objects and variables"""

from objects import tokenList
from objects import channelList
from objects import matchList
from objects import fileLocks

try:
	with open("version") as f:
		VERSION = f.read()
	if VERSION == "":
		raise
except:
	VERSION = "¯\_(xd)_/¯"

db = None
conf = None
banchoConf = None
tokens = tokenList.tokenList()
channels = channelList.channelList()
matches = matchList.matchList()
restarting = False
fLocks = fileLocks.fileLocks()
verifiedCache = {}
cloudflare = False
chatFilters = None

debug = False
outputRequestTime = False
outputPackets = False
discord = False
gzip = False
localize = False
sentry = False
