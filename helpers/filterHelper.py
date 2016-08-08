import os

class chatFilters():
	oldWords = () # have to use tuples as a
	newWords = () # dictionary broke fairly hard.

	def loadFilters(self):
		filterFile = open(os.path.dirname(os.path.realpath(__file__)) + "/filters.txt", "r")

		for line in filterFile:

			lineSplit = line.split("=")

			#self.filters[lineSplit[0]] = lineSplit[1]
			self.oldWords += (lineSplit[0],)
			self.newWords += (lineSplit[1].replace("\n", ""),)


	def checkFilters(self, message):
		if " " in message:
			messageTemp = message.split(" ") # split word by spaces
		else:
			messageTemp = message

		for word in messageTemp:
			if word in self.oldWords:
				oldIdx = self.oldWords.index(word)

				message = message.replace(word, self.newWords[oldIdx]) # replace the bad word with our filtered word

		return message
