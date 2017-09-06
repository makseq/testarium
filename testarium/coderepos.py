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

import subprocess, sys, os


class CodeRepos:
    def commit(self, commitName, comment): pass

    def changebranch(self, branchName): pass


class Mercurial(CodeRepos):
    def commit(self, commitName, comment):
        subprocess.call(['hg', 'commit', '-m', commitName + ' ' + str(comment)], stdout=open(os.devnull, 'w'))

    def changebranch(self, branchName):
        # self.commit('branch changed to ', branchName)
        return None


class Git(CodeRepos):
    def commit(self, commitName, comment):
        subprocess.call(['git', 'commit', '-a', '-m', commitName + ' ' + str(comment)], stdout=open(os.devnull, 'w'))

    def changebranch(self, branchName):
        # self.commit('branch changed to ', branchName)
        return None
