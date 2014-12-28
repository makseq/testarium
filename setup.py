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

from setuptools import setup

data_files = [

	('testarium/web/templates', ['log.html', 'main.html']),

	('testarium/web/static/images', ['back.jpg']),

	('testarium/web/static/scripts', 
		['d3.linegraph.js', 
		'd3.v3.min.js', 
		'jquery-1.11.0.min.js', 
		'jquery-ui.js', 
		'main.js']),

	('testarium/web/static/styles', 
		['main.css', 
		'd3.linegraph.css']),
		
	('testarium/web/static', ['favicon.ico'])

]

	
setup(name='testarium',
	  url='http://testarium.makseq.com',
	  description='Research tool to perform experiments and store results in the repository',
	  author='Max Tkachenko',
	  author_email='makseq@gmail.com',
	  license='GNU GPLv3',
      version='0.1',
      packages=['testarium', 'testarium/score', 'testarium/web'],
	  install_requires=['flask', 'colorama', 'pycrypto', 'hashlib'],
	  include_package_data=True,
	  zip_safe=False
    )