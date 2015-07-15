#!/usr/bin/env python3
import os.path
import string
import subprocess
import sys

from . import *
from .chapters import make_chapters_file

if 'win32' in sys.platform:
	mp4box_executable = 'MP4BOX.EXE'
else:
	mp4box_executable = 'MP4Box'

common_chapter_spec_element = '''CHAPTER${n}=$timestamp
CHAPTER${n}NAME=$name
'''

class MP4BoxException(Exception):
	pass

def MP4Box_command(input_filename, output_filename=None, **kwargs):
	if '+' in input_filename: raise MP4BoxException("MP4Box is intolerant of filenames with special characters: '{}'".format(input_filename))
	dirname, basename = os.path.split(input_filename)
	filepart, ext = os.path.splitext(basename)
	if not output_filename:
		output_filename = filepart+'_Cut'+'.MP4'
	commands = kwargs.pop('commands', [])
	if 'cut' in kwargs:
		cut = kwargs.pop('cut')
		if not isinstance(cut, (list, tuple)):
			raise MP4BoxException("{} not valid splits".format(cut))
		try:
			commands += [ '-split-chunk', '{}:{}'.format(cut[0] or '', cut[1] or '') ]
		except:
			raise MP4BoxException("{} not valid splits".format(cut))
	if 'chapters' in kwargs: # these are pairs
		chapters_filename = basename+'.chapters'
		if make_chapters_file(kwargs.pop('chapters')):
			commands += [ '-chap', chapters_filename ]
			commands += [ '-add-item', chapters_filename ]
	commands += [ '-new', output_filename ]
	return [ mp4box_executable, '-cat', input_filename ]+commands
def MP4Box_probe(filename):
	if '+' in filename: raise MP4BoxException("MP4Box is intolerant of filenames with special characters: '{}'".format(filename))
	command = [ mp4box_executable, '-info', filename, '-std' ]
	proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	out, err = proc.communicate()
	return not parse_output(out, err, proc.returncode)
def parse_output(out, err='', returncode=None):
	def _parse(b, prefix='STDOUT', encoding='ASCII'):
		line = b.decode(encoding).rstrip()
		if 'Bad Parameter' in line:
			error(line)
			raise MP4BoxException(line)
		elif "Edit list doesn't look like a track delay scheme" in line:
			warning(line)
		elif not line.startswith('Appending:') and not line.endswith('100)'): # ignore progress bar
			debug(prefix+' '+line)
	for b in err.splitlines():
		_parse(b, 'STDERR')
	'''MP4Box sends most output to stderr'''
	#for b in out.splitlines():
	#	_parse(b)
	return returncode or 0
def MP4Box(input_filename, **kwargs):
	fps = 29.970
	debug('TODO: for the purposes of converting frame numbers, FPS is fixed at {}'.format(fps))
	dirname, basename = os.path.split(input_filename)
	filepart, ext = os.path.splitext(basename)
	if not os.path.isfile(input_filename):
		error("Failed to open '{}'".format(input_filename))
		return -1
	output_file_pattern = kwargs.pop('output_file_pattern', filepart+'-{:03d}'+'.MP4')
	debug("Running probe...")
	if not MP4Box_probe(input_filename):
		error("Failed to open '{}'".format(input_filename))
		return -1
	if 'frames' in kwargs:
		debug("Converting frames")
		kwargs['cuts'] = [ (int(b)/fps if b else '', int(e)/fps if e else '') for (b, e) in kwargs.pop('frames') ]
	if 'splits' in kwargs:
		splits = kwargs.pop('splits')
		debug("Splitting {} times".format(len(splits)))
		returncodes = []
		a = returncodes.append
		for n, (b, e) in enumerate(splits, start=1):
			ofn = output_file_pattern.format(n)
			command = MP4Box_command(input_filename, output_filename=ofn, cut=(b,e), **kwargs)
			debug("Running "+" ".join(command))
			proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			out, err = proc.communicate()
			r = parse_output(out, err, proc.returncode)
			if r:
				debug("part {} exited normally".format(n))
			else:
				error("part {} exited {}".format(n, r))
			a(r)
		return -1 if any((0 != r) for r in returncodes) else 0
	else:
		command = MP4Box_command(input_filename, **kwargs)
		debug("Running "+" ".join(command))
		proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out, err = proc.communicate()
		return parse_output(out, err, proc.returncode)