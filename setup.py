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

	('testarium/web/templates', ['main.html']),

	('testarium/web/static/fonts',
		['FontAwesome.otf',
		 'FontAwesome.ttf',
		 'fontawesome-webfont.eot',
		 'fontawesome-webfont.svg',
		 'fontawesome-webfont.ttf',
		 'fontawesome-webfont.woff',
		 'fontawesome-webfont.woff2',
		 'Gudea-Bold.otf',
		 'Gudea-Bold.ttf',
		 'Gudea-Italic.otf',
		 'Gudea-Italic.ttf',
		 'Gudea-Regular.otf',
		 'Gudea-Regular.ttf']),

	('testarium/web/static/images', ['back.jpg']),

	('testarium/web/static/scripts', 
		['d3.linegraph.js', 
		 'd3.v3.min.js',
		 'jquery-ui.min.js',
		 'jsrender.min.js',
		 'main.js',
		 'wavesurfer.min.js',
		 'wavesurfer.regions.js',
		 'wavesurfer.spectrogram.js']),

	('testarium/web/static/styles', 
		['main.css', 
		'd3.linegraph.css',
		'jquery-ui.min.css',
		'font-awesome.css']),
		
	('testarium/web/static', ['favicon.ico'])

]

	
setup(name='testarium',
	  url='http://testarium.makseq.com',
	  description='Research tool to perform experiments and store results in the repository',
	  author='Max Tkachenko, Danila Doroshin',
	  author_email='makseq@gmail.com',
	  license='GNU GPLv3',
      version='0.2.1',
      packages=['testarium', 'testarium/score', 'testarium/web'],
	  install_requires=['flask', 'colorama', 'pycrypto'],
	  include_package_data=True,
	  zip_safe=False,
	  keywords = ['testing', 'logging', 'research', 'science', 'repository'],
	  classifiers=[
		"Topic :: Scientific/Engineering",
		"Development Status :: 3 - Alpha",
		"License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
		"Operating System :: OS Independent",
		"Programming Language :: Python",
		"Intended Audience :: Science/Research"
	  ]
    )