import os

class chatFilters:
	def __init__(self, fileName="filters.txt"):
		self.filters = {}
		self.loadFilters(fileName)

	def loadFilters(self, fileName="filters.txt"):
		# Reset chat filters
		self.filters = {}

		# Open filters.txt
		#with open(os.path.dirname(os.path.realpath(__file__)) + "/../"+fileName+".txt", "r") as f:
		with open("filters.txt", "r") as f:
			# Read all lines
			data = f.readlines()

			# Process each line
			for line in data:
				# Get old/new word and save it in dictionary
				lineSplit = line.split("=")
				self.filters[lineSplit[0]] = lineSplit[1].replace("\n", "")

	def filterMessage(self, message):
		# Split words by spaces
		messageTemp = message.split(" ")

		# Check each word
		for word in messageTemp:
			# If the word is filtered, replace it
			if word in self.filters:
				message = message.replace(word, self.filters[word])

		# Return filtered message
		return message
