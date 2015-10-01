#!/usr/bin/env python3
import os.path
import shlex
import string
import subprocess
import sys

import tqdm

from . import *
from .chapters import make_chapters_file
from .FFprobe import get_frame_rate

if sys.platform.startswith('win'):
	mp4box_executable = 'MP4BOX.EXE'
else:
	mp4box_executable = 'MP4Box'
debug("MP4Box is {}".format(mp4box_executable))

common_chapter_spec_element = '''CHAPTER${n}=$timestamp
CHAPTER${n}NAME=$name
'''

class MP4BoxException(SplitterException):
	pass

def MP4Box_command(input_filename,
				   output_filename='{filepart}_Cut.MP4',
				   chapters_filename='{basename}.chapters',
				   **kwargs):
	if '+' in input_filename: raise MP4BoxException("MP4Box is intolerant of filenames with special characters: '{}'".format(input_filename))
	dirname, basename = os.path.split(input_filename)
	filepart, ext = os.path.splitext(basename)
	commands = kwargs.pop('commands', [])
	if 'cut' in kwargs:
		cut = kwargs.pop('cut')
		if not isinstance(cut, (list, tuple)):
			raise MP4BoxException("{} not valid splits".format(cut))
		try:
			b, e = cut
			if not b:
				b = ''
			if not e:
				e = ''
			commands += [ '-split-chunk', '{}:{}'.format(b, e) ]
		except Exception as e:
			raise MP4BoxException("{} not valid splits: {}".format(cut, e))
	if 'chapters' in kwargs: # these are pairs
		try:
			chapters_filename = chapters_filename.format(**locals())
		except:
			warning("chapters_filename={}, which is probably not what you intended".format(chapters_filename))
		if make_chapters_file(kwargs.pop('chapters'), chapters_filename):
			commands += [ '-chap', chapters_filename ]
			commands += [ '-add-item', chapters_filename ]
	try:
		output_filename = output_filename.format(**locals())
	except:
		warning("output_filename={}, which is probably not what you intended".format(output_filename))
	commands += [ '-new', output_filename ]
	for k, v in kwargs.items():
		debug("Extra parameter unused: {}={}".format(k, v))
	return [ mp4box_executable, '-cat', input_filename ]+commands
def MP4Box_probe(filename):
	if '+' in filename:
		raise MP4BoxException("MP4Box is intolerant of filenames with special characters: '{}'".format(filename))
	command = [ mp4box_executable, '-info', filename, '-std' ]
	proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	out, err = proc.communicate()
	return not parse_output(out, err, proc.returncode)
def parse_output(out, err='', returncode=None):
	def _parse(b, prefix='STDOUT', encoding=stream_encoding):
		line = b.decode(encoding).rstrip()
		if any(s in line for s in ['Bad Parameter', 'No suitable media tracks to cat']):
			raise MP4BoxException(line)
		elif line.upper().startswith('WARNING:'): # wrap warnings
			warning(line[9:])
		elif any(line.startswith(p) for p in [ 'Appending:', 'ISO File Writing:', 'Splitting:' ]) and line.endswith('100)'): # progress
			return line
		else:
			debug(prefix+' '+line)
	for b in err.splitlines():
		_parse(b, 'STDERR')
	'''MP4Box sends most output to stderr'''
	#for b in out.splitlines():
	#	_parse(b)
	return returncode or 0
def MP4Box(input_filename,
		   output_file_pattern='{filepart}-{n:03d}.MP4',
		   dry_run=False,
		   **kwargs):
	if not dry_run:
		def _dispatch(command):
			debug("Running "+' '.join(command))
			proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			out, err = proc.communicate()
			return parse_output(out, err, proc.returncode)
	else:
		def _dispatch(command):
			print(' '.join(shlex.quote(s) for s in command))

	fps = get_frame_rate(input_filename)
	dirname, basename = os.path.split(input_filename)
	filepart, ext = os.path.splitext(basename)
	if not os.path.isfile(input_filename):
		raise MP4BoxException("'{}' not found".format(input_filename))
	debug("Running probe...")
	if not MP4Box_probe(input_filename):
		raise MP4BoxException("Failed to open '{}'".format(input_filename))
	if 'frames' in kwargs:
		debug("Converting frames before split")
		kwargs['splits'] = [ (int(b)/fps if b else '', int(e)/fps if e else '') for (b, e) in kwargs.pop('frames') ]
	if 'splits' in kwargs:
		splits = kwargs.pop('splits')
		return_codes = []
		a = return_codes.append
		for n, (b, e) in enumerate(tqdm.tqdm(splits, desc=input_filename), start=1):
			command = MP4Box_command(input_filename,
									 output_filename=output_file_pattern.format(**locals()),
									 cut=(b,e),
									 **kwargs)
			r = not _dispatch(command)
			if r:
				debug("part {} succeeded".format(n))
			else:
				error("part {} failed".format(n))
			a(r)
		return all(return_codes)
	else:
		command = MP4Box_command(input_filename, **kwargs)
		return not _dispatch(command)
