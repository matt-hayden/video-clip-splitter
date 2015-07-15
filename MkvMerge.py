#!/usr/bin/env python3
from datetime import timedelta
import os.path
import string
import subprocess
import sys

from . import *
from .chapters import make_chapters_file

if 'win32' in sys.platform:
	mkvmerge_executable = 'MKVMERGE.EXE'
else:
	mkvmerge_executable = 'mkvmerge'

mkvmerge_options_file_template = '''# MkvMerge file for $input_filename
# -*- coding: utf-8 -*-
# escaping: \\\\=\\ and \\h=#	empty argument: #EMPTY#

-o
$output_file_pattern

### this file
--attach-file
$options_filename

# Timestamps must either have the form HH:MM:SS.nnnnnnnnn for specifying 
# the duration in up to nano-second precision or be a number d followed by the 
# letter 's' for the duration in seconds. HH is the number of hours, MM the 
# number of minutes, SS the number of seconds and nnnnnnnnn the number of 
# nanoseconds. Both the number of hours and the number of nanoseconds can be 
# omitted. There can be up to nine digits after the decimal point.

$command_lines

# = ignores other sequential files
=$input_filename
'''

class MkvMergeException(SplitterException):
	pass

def MkvMerge_command(input_filename, output_file_pattern='', options_filename='', **kwargs):
	dirname, basename = os.path.split(input_filename)
	filepart, ext = os.path.splitext(basename)
	if not options_filename:
		options_filename = basename+'.MkvMerge.options'
	if not output_file_pattern:
		output_file_pattern = filepart+'.MKV'
	commands = kwargs.pop('commands', [])
	split_style = kwargs.pop('split_style', None)
	if 'title' in kwargs:
		commands += [ '--title', kwargs.pop('title') ]
	if 'splits' in kwargs:
		split_style = 'parts'
		my_pairs = [ (timedelta(seconds=float(b)) if b else '', timedelta(seconds=float(e)) if e else '') for (b, e) in kwargs.pop('splits') ]
	if 'frames' in kwargs:
		split_style = 'parts-frames'
		my_pairs = [ (b or '', e or '') for (b, e) in kwargs.pop('frames') ]
	if 'only_chapters' in kwargs:
		split_style = 'chapters'
		my_pairs = [ (b or '', e or '') for (b, e) in kwargs.pop('only_chapters') ]
	if split_style:
		commands += [ '--split' ]
		commands += [ split_style+':'+','.join(( '{}-{}'.format(*p) for p in my_pairs )) ]
	if 'chapters' in kwargs: # these are pairs
		chapters_filename = basename+'.chapters'
		if make_chapters_file(kwargs.pop('chapters')):
			commands += [ '--chapters', chapters_filename ]
			commands += [ '--attach-file', chapters_filename ]
	command_lines = '\n'.join(commands)
	t = string.Template(kwargs.pop('template', None) or mkvmerge_options_file_template)
	with open(options_filename, 'w') as ofo:
		ofo.write(t.substitute(locals()))
	return [ mkvmerge_executable, '@'+options_filename ]
def MkvMerge_probe(filename):
	proc = subprocess.Popen([ mkvmerge_executable, '-i', filename ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	out, err = proc.communicate()
	return not parse_output(out, err, proc.returncode)
def parse_output(out, err='', returncode=None):
	def _parse(b, prefix='STDOUT', encoding='ASCII'):
		line = b.decode(encoding).rstrip()
		if 'unsupported container:' in line:
			error(line)
			raise MkvMergeException(line)
		elif 'This corresponds to a delay' in line:
			warning(line)
		elif 'audio/video synchronization may have been lost' in line:
			warning(line)
		elif not line.startswith('Progress:') and not line.endswith('%'): # progress bar
			debug(prefix+' '+line)
	for b in err.splitlines():
		_parse(b, prefix='STDERR')
	for b in out.splitlines():
		_parse(b)
	return returncode or 0
def mkvmerge(input_filename, output_file_pattern='', **kwargs):
	dirname, basename = os.path.split(input_filename)
	filepart, ext = os.path.splitext(basename)
	if not os.path.isfile(input_filename):
		error("Failed to open '{}'".format(input_filename))
		return -1
	debug("Running probe...")
	if not MkvMerge_probe(input_filename):
		error("Failed to open '{}'".format(input_filename))
		return -1
	command = MkvMerge_command(input_filename, **kwargs)
	debug("Running "+' '.join(command))
	proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	out, err = proc.communicate()
	return parse_output(out, err, proc.returncode)