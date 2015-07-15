#! /usr/bin/env python
from logging import debug, info, warning, error, critical
import os.path
import sys

from local.xcollections import Namespace

class Cut(Namespace):
	'''
	A cut has should have the following members:
		start
		end
		duration
		filename
	Optionally:
		name
		order
		file_duration (some cutting programs cannot accurately determine the end)
	'''
	@property
	def start(self):
		return self['start-time']
	@property
	def end(self):
		return self['stop-time']
	@property
	def duration(self):
		return float(self['stop-time']) - float(self['start-time'])
	@property
	def name(self):
		"""
		Filenames starting with this path are fixed
		"""
		if True:
			_, basename = os.path.dirsplit(self['entry_name'])
			while basename and basename.endswith('(2)'):
				basename = basename[:-3]
			return basename
		else:
			dirname, basename = os.path.split(self['filename'])
			if self['entry_name'].upper().startswith(basename.upper()):
				return self['entry_name'][len(basename):] or self['entry_name']
			else: return self['entry_name']

def _parse(filename):
	with open(filename) as fi:
		numbered_lines = [(ln, line.rstrip()) for ln, line in enumerate(fi)]
	header = ''
	while not header.startswith('#EXTM3U'):
		ln, header = numbered_lines.pop(0)
	number_cuts = 0
	cut = Cut(order=number_cuts)
	for ln, line in numbered_lines:
		if line:
			if line.startswith('#EXTINF'):
				_, text = line.split(':', 1)
				assert 'file_duration' not in cut
				if ',' in text:
					#cut['file_duration'], cut['entry_name'] = file_duration = text.split(',')
					cut['file_duration'], cut['entry_name'] = text.split(',', 1)
				else:
					cut['file_duration'] = text
			elif line.startswith('#EXTVLCOPT'):
				_, text = line.split(':', 1)
				if '=' in text:
					attrib, value = text.split('=', 1)
				assert attrib not in cut
				if attrib == 'stop-time':
					if not value or (float(value) < 0): # bug?
						error("Illegal stop-time={} ignored".format(value))
						continue
				cut[attrib] = value
			elif line.startswith('#'):
				warning("Line {} ignored".format(ln))
				info("Unrecognized comment or metadata: "+line)
			else:
				cut['filename'] = line
			if 'filename' in cut:
				if not 'start-time' in cut and 'stop-time' in cut:
					cut['start-time'] = '0'
				elif 'start-time' in cut and not 'stop-time' in cut:
					cut['stop-time'] = cut['file_duration']
				yield cut
				number_cuts += 1
				cut = Cut(order=number_cuts)
def extended_m3u_file(*args, **kwargs):
	return list(_parse(*args, **kwargs))