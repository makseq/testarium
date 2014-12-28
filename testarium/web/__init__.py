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

from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
import flask, os
from testarium.utils import *
#from flask.ext.restful import fields, marshal_with
utils = __import__('testarium.utils')

DEBUG = True

class WebServer:
	
	def __init__(self, testarium):
		self.app = Flask(__name__)
		self.app.config.from_object(__name__)
		self.t = testarium
		self.t.Load(True)

	def Start(self, port):
		#-----------------------------------------------
		@self.app.route('/branch/set_active/<name>')
		def branch_set_active(name):
			try:
				branch = self.t.branches[name]
				self.t.activeBranch = branch
			except: pass
			return redirect('log')
	
		#-----------------------------------------------
		@self.app.route('/static/<path:filename>')
		def send_static(path, filename):
			return flask.send_from_directory('static', filename)
			
		#-----------------------------------------------
		@self.app.route('/favicon.ico')
		def send_favicon():
			return flask.send_file('static/favicon.ico')
			
		#-----------------------------------------------
		@self.app.route('/storage/<path:filename>')
		def send_storage(filename):
			workdir = os.getcwd()
			return flask.send_from_directory(workdir, filename)
	
		#-----------------------------------------------
		@self.app.route('/log', methods=['GET'])
		def log():
			activeName = self.t.activeBranch.name
			self.t.Load(True)
			self.t.ChangeBranch(activeName)
			
			number = 5
			name = ''
			
			try: number = int(request.args['number'])
			except: pass
			try: name = request.args['name']; number = -1
			except: pass
			
			commits = self.t.SelectCommits(self.t.activeBranch.name, name, number)
			return render_template('log.html', t=self.t, commits=commits)
			
		#-----------------------------------------------
		@self.app.route('/')
		def root():
			return redirect('log')
		
		# jinja filters
		self.app.jinja_env.filters['UrlGraph'] = utils.UrlGraph
		self.app.jinja_env.filters['UrlFile'] = utils.UrlFile
				
		# app start
		self.app.run(port=port, host='0.0.0.0')
		
		