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

import shutil, time, sys
import unittest
import subprocess

#--------------------------------
# Remove not unittest param
full_test = False
pos = 0
for v in sys.argv:
	if v == 'full':
		full_test = True
		break
	pos = pos + 1
if full_test: del sys.argv[pos]
#--------------------------------

setup = False

class TestGeneral(unittest.TestCase):
	def setUp(self):
		global setup
		if setup: return 

		if full_test:
			print 'Setup ...'		
			try: subprocess.call(['easy_install.exe', 'http://testarium.makseq.com/testarium-0.1.zip'])
			except: subprocess.call([r'c:\Python27\Scripts\easy_install.exe', 'http://testarium.makseq.com/testarium-0.1.zip'])
		
		print 'Remove .testarium directory ...'
		try: shutil.rmtree('.testarium')
		except: pass
		
		setup = True

	# General
	def test_general(self):
		# normal start
		import example_ok
		example_ok.main()
		example_ok.main()
	
	# MyRun
	def test_myrun(self):
		import example_ok
		
		# MyRun returns None
		reload(example_ok)
		def MyRun(config): return None
		example_ok.testarium.experiment.set_run(MyRun)
		example_ok.main()
		
		# MyRun returns -1
		reload(example_ok)
		def MyRun(config): return -1
		example_ok.testarium.experiment.set_run(MyRun)
		example_ok.main()
		
		# MyRun has broken body
		reload(example_ok)
		def MyRun(config): THIS_IS_BAD_PLACE
		example_ok.testarium.experiment.set_run(MyRun)
		example_ok.main()

	# MyScore
	def test_myscore(self):
		import example_ok
		
		# MyScore returns None
		reload(example_ok)
		def MyScore(dir): return None
		example_ok.testarium.experiment.set_score(MyScore)
		example_ok.main()
		
		# MyScore has broken body
		reload(example_ok)
		def MyScore(dir): return THIS_IS_BAD_PLACE
		example_ok.testarium.experiment.set_score(MyScore)
		example_ok.main()
		
	def test_mail(self):
		pass
	
		
if __name__ == '__main__':
	unittest.main()
	#suite = unittest.TestLoader().loadTestsFromTestCase(TestGeneral)
	#unittest.TextTestRunner(verbosity=2).run(suite)