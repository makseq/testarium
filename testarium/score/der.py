#!/usr/bin/env python
'''
Testarium
Copyright (C) 2014 Maxim Tkachenko

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

'''
More description:
http://www.xavieranguera.com/phdthesis/node108.html
ref = reference (original, true)
hyp = hypothesis (processed)
'''
import os, sys, json

skipnames = set(['pau', 'spau', 'none'])

#-------------------------------------------------------------------------------
def readFile(fileName):
	data = []
	with open(fileName, 'r') as fd:
		for line in fd:
			if not line or line.isspace() or line[0]=='#':
				continue
			lineObj = line.split()
			begin = float(lineObj[0])
			end = float(lineObj[1])
			id = lineObj[2]
			data.append((begin, end, id))

	n = len(getTotalSpeakers(data))
	#if n==1 or n>=3: return []
	if n!=2: return []

	return data

#-------------------------------------------------------------------------------
def getTotalSpeakers(data):
	names = set()
	for d in data:
		if not d[2] in skipnames:
			for c in d[2]:
				if c != '+':
					names.add(c)
	return names

#-------------------------------------------------------------------------------
def getNumberOfSpeaker(a, b, data):
	ids = set()
	for d in data:
		if (d[0] >= a and d[0] < b) or (d[1] > a and d[1] <= b) \
		or (d[0] <= a and d[1] >= b): 
			if d[2] in skipnames: continue
			for c in d[2]:
				if c != '+':
					ids.add(c)
	return ids

#-------------------------------------------------------------------------------
def mergeMarkers(refData, hypData):
	s = set()
	
	for ref in refData:
		s.add(ref[0])
		s.add(ref[1])
	for hyp in hypData:
		s.add(hyp[0])
		s.add(hyp[1])

	s = list(s)
	s.sort()
	if len(s) < 2: return []
	begin = s[0:-1]
	end = s[1:]
	return zip(begin, end)

#-------------------------------------------------------------------------------
def createAllNames(names):
	namesOfNames = [[i for i in names] for j in names]

	f = lambda ss,cs: (s+[c] for s in ss for c in cs if not c in s)
	shiftedNames = reduce(
		f,
		namesOfNames, # { D1,D2,...,Dn }
		[ [] ]
	)
	shiftedNames = list(shiftedNames)
	return shiftedNames

#-------------------------------------------------------------------------------
def remapSpeakers(data, shift):
	if shift == 0: return data
	
	# analyze speakers names and create shifted names
	names = getTotalSpeakers(data)
	shiftedNames = createAllNames(names)

	# create remap dict
	remap = dict(zip(names, shiftedNames[shift]))

	newdata = []
	for d in data:
		if d[2] in skipnames:
			newdata.append( (d[0], d[1], d[2]) )
		else:
			name = list(d[2])
			for i in xrange(0, len(name)):
				if name[i] != '+':
					name[i] = remap[ name[i] ]
			name = ''.join(name)
			newdata.append( (d[0], d[1], name) )

	return newdata
	

#-------------------------------------------------------------------------------
def DER(refData, hypDataOrig):
	
	markers = mergeMarkers(refData, hypDataOrig)
	if not markers:
		print 'Error: no markers'
		return (-2, 0, 0)

	totalSpeakers = getTotalSpeakers(hypDataOrig)
	nom = 0
	#Tscore = time * 1e7
	best = float('inf')
	bestShift = -1
	bestNom = 0.0
	bestTscore = 0.0
	
	for shift in xrange(0, len(createAllNames(totalSpeakers))):
		hypData = remapSpeakers(hypDataOrig, shift)
		nom = 0
		total = 0
		for m in markers:
			dur = m[1] - m[0]
			refIDs = getNumberOfSpeaker(m[0], m[1], refData)
			hypIDs = getNumberOfSpeaker(m[0], m[1], hypData)

			if not refIDs and not hypIDs: continue

			nom += dur * (max(len(refIDs), len(hypIDs)) - len(refIDs & hypIDs))
			total += dur * len(refIDs)

		score = nom / total

		#if score >= 0.0  and score <= 1.0 \
		if score >= 0.0 and best > score:
			best = score
			bestShift = shift
			bestNom = nom
			bestTscore = total

	if (bestShift == -1):
		print 'Error! No best score!'
		return (-1, 0, 0)

	return (0, bestNom, bestTscore)

#-------------------------------------------------------------------------------
def Go(dirRef, dirHyp):
	refList = os.listdir(dirRef)
	nom = 0
	den = 0
	skipped = 0
	for refFile in refList:
		#print ''
		fileparts = os.path.splitext(refFile)
		if fileparts[1] != '.lab':
			continue

		refPath = dirRef + '/' + refFile
		hypPath = dirHyp + '/' + fileparts[0] + '.lab'

		if os.path.isfile(hypPath) == False:
			print 'Hyp not found', hypPath
			skipped += 1
			continue
		
		# bad ref file
		refData = readFile(refPath)
		if not refData:
			print 'Bad ref file:', refPath
			skipped += 1
			continue
		
		# bad hyp file
		hypData = readFile(hypPath)
		if not hypData:
			print 'Bad hyp file:', refPath
			skipped += 1
			continue

		# calculate DER 
		der = DER(refData, hypData)
		if der[0] < 0:
			print '!!! Error: ' + refFile
			skipped += 1
		else:
			nom += der[1]
			den += der[2]
			if (der[2] < 1e-7): pass
				#print 'Processed: ' + refFile.decode('1251') + '\nDER = '+ str(1.0)
			else: pass
				#print 'Processed: ' + refFile.decode('1251') + '\nDER = '+ str(der[1] / der[2])

	if skipped != 0: print 'Skipped files =', skipped
	if (den < 1e-7): 
		print 'Denominator = 0, is data empty?'
		den = 1.0
		nom = 1.0

	err = nom / float(den)
	return (err, skipped)
	
def Score(dir):
	config = json.loads(open(dir + '/config.json', 'r').read())
	r = Go(config['referenceLab'], config['batchDirectory'])
	return {'score':r[0], 'skipped':r[1]}

#-------------------------------------------------------------------------------
if __name__ == '__main__':
	if (len(sys.argv) < 3): print 'usage: der_anguera.py reference_dir hyp_dir' ; exit()
	
	der = Go(sys.argv[1], sys.argv[2])
	print 'Total DER =', der[0]
