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

import flask, os, json, collections, copy
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash


DEBUG = True
t = 'None'

# answer for api
def answer(status=0, msg="", object=None):
	if status==0 and not msg and object is None:
		status = -1000
		msg = "nothing happened"

	a = { "status" : status, "msg" : msg }
	a.update({'request': request.args})

	if not object is None: a.update({"result" : object})
	return json.dumps(a)


class WebServer:
	
	def __init__(self, testarium):
		self.app = Flask(__name__)
		self.app.config.from_object(__name__)
		
		self.t = testarium
		self.t.Load(True)
		global t
		t = self.t

	def Start(self, port):

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


		###  API ###

		#-----------------------------------------------
		@self.app.route('/api/info')
		def API_info():
			t.Load(True)
			cfg =  copy.deepcopy(t.config)
			try: del cfg['mail.password']
			except: pass

			res = {
				"config" : cfg,
				"common" : {
					"root" : t.common.root,
					"best_score_max" : t.common.best_score_max
				},
				"branches" : [b for b in t.branches],
				"active_branch" : t.ActiveBranch().name
			}
			return answer(object=res)

		#-----------------------------------------------
		@self.app.route('/api/branches')
		def API_branches():
			t.Load(True)
			res = [b for b in t.branches]
			return answer(object=res)

		#-----------------------------------------------
		@self.app.route('/api/branches/<name>/commits')
		def API_branches_commits(name):
			t.Load(True)
			t.ChangeBranch(name)

			number = 100
			commitName = ''
			if 'n'      in request.args: number = int(request.args['n'])
			if 'name'   in request.args: commitName = request.args['name']; number = -1

			# where
			if 'where' in request.args:
				where = request.args['where']
				commits, keyError = t.Where(where)

			# simple select
			else:
				commits = t.SelectCommits(name, commitName, number)
				keyError = None

			printing = [c.Print(web=True) for c in commits]
			res = [collections.OrderedDict(zip(col, val)) for col, val in printing]

			status = 0
			msg = "ok"
			if keyError:
				status=-150
				msg="There was KeyError: '" + str(keyError) + "'. Not all commits contain this key or key is wrong"
			return answer(status=status, msg=msg, object=res)


		### ROOT ###

		#-----------------------------------------------
		@self.app.route('/')
		def root():
			self.t.Load(True)
			self.t.ChangeBranch(self.t.activeBranch.name)

			number = 100
			name = ''

			try: number = int(request.args['n'])
			except: pass
			try: name = request.args['name']; number = -1
			except: pass

			commits = self.t.SelectCommits(t.activeBranch.name, name, number)
			return render_template('main.html', t=self.t, commits=commits)

		# app start
		self.app.run(port=port, host='0.0.0.0')
