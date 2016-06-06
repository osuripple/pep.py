'''
import threading

class task:
	def __init__(self, function, args = (), kwargs = {}):
		self.function = function
		self.args = args
		self.kwargs = kwargs

class logThread:
	def __init__(self):
		self.thread = threading.Thread()
		self.queue = []

	def enqueue(self, function, args = (), kwargs = {}):
		self.queue.append(task(function, args, kwargs))

	def run(self):
		for i in self.queue:
			self.thread = threading.Thread(i.function, i.args, i.kwargs)
			self.thread.run()
			self.thread.join()
		self.queue = []
'''
