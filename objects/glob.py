"""Global objects and variables"""

from objects import tokenList
from objects import channelList
from objects import matchList
import threading

VERSION = "0.9"

db = None
conf = None
banchoConf = None
tokens = tokenList.tokenList()
channels = channelList.channelList()
matches = matchList.matchList()
memes = True
restarting = False
pool = None
requestTime = False
meme = threading.Lock()
