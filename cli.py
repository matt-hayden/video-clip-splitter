#!/usr/bin/env python3
import os, os.path

from . import *
from .converters import *
from .m3u import *
from .splits_tsv import *

###
def get_converter(*args, **kwargs):
	if not args:
		raise ValueError("Argument required")
	video_file = cuts = cut_units = '' # wouldn't do that with a class
	for arg in args:
		_, ext = os.path.splitext(arg)
		ext = ext.upper()
		if '.M3U' == ext:
			cuts, cut_units = [ (cut.start, cut.end) for cut in extended_m3u_file(arg) ], 'seconds'
		elif '.SPLITS' == ext:
			cuts, cut_units = old_splits_file(arg).cuts, 'frames'
		elif ext in ('.AVI', '.DIVX'):
			video_file, converter = arg, avidemux
		elif ext in ('.MKV', '.WEBM', '.FLV'):
			video_file, converter = arg, mkvmerge
		elif ext in ('.MPG', '.MP4', '.MOV'):
			video_file, converter = arg, MP4Box
		elif ext in ('.ASF', '.WMV'):
			video_file, converter = arg, asfbin
		else:
			raise SplitterException(ext+' not understood')
	nargs = {}
	# can be overwritten:
	nargs['video_file'] = video_file
	# this section defines 'seconds' as the default 'splits'
	if 'seconds' == cut_units: 
		nargs['splits'] = cuts
	else:
		nargs[cut_units] = cuts
	#
	nargs.update(kwargs)
	# cannot be overwritten:
	nargs['profile'] = converter.__name__
	#
	return converter, nargs

def run(*args):
	def die(*args):
		error(*args)
		return -1
	#
	converter, kwargs = get_converter(*args)
	video_file = kwargs.pop('video_file')
	debug("Parameters:")
	for k, v in kwargs.items():
		debug("\t{}={}".format(k, v))
	try:
		return converter(video_file, **kwargs)
	except OSError as e:
		die("{} not found: {}".format(kwargs['profile'], e))
	except Exception as e:
		warning("{} failed: {}".format(kwargs.pop('profile'), e))
		debug("Trying fallback {}...".format(default_converter.__name__ or 'converter'))
		return default_converter(video_file, **kwargs)
#