import os
import subprocess
from datetime import datetime
import re

def error ( string ):
    print ( string )
    exit ( 1 )

def utc_timestamp ():
    return datetime.utcnow ().timestamp ()

class cd:
    """Context manager for changing the current working directory"""
    def __init__ ( self, newPath ):
        self.newPath = newPath

    def __enter__ ( self ):
        self.savedPath = os.getcwd ()
        os.chdir ( self.newPath )

    def __exit__ ( self, etype, value, traceback ):
        os.chdir ( self.savedPath )

from settings import *

# Run system commands

def run_command ( command, ret = 'exit_code' ):
    r = None
    if args.verbosity >= 1:
        print ( "Running command: " + str ( command ) )
    if ret == 'exit_code':
        r = subprocess.call ( command, stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL )
    if ret == 'output':
        r = subprocess.check_output ( command, stderr = subprocess.DEVNULL )
        r = r.rstrip ( b'\n' )
    if args.verbosity >= 2:
        print ( "Returning: " + str ( r ) )
    return r

def popen ( command, *args_forward, **keyargs ):
    if args.verbosity >= 1:
        print ( "Running command: " + str ( command ) )
    return subprocess.Popen ( command, *args_forward, **keyargs )

# Git interaction

def build_ref_dict ():
    ref_dict = {}
    output = popen ( [ 'git', 'show-ref' ], stdout = subprocess.PIPE ).stdout
    regex = re.compile ( br"([A-Za-z0-9]{40}) refs/(?:heads/|remotes/)(\S*)" )
    for line in output:
        match = regex.match ( line )
        if not match:
            error ( 'failed to match regex on `git show-ref` output line' )
        ref_dict [ match.group ( 2 ) ] = match.group ( 1 )
    if args.verbosity >= 2:
        print ( "Parsed references: " + str ( ref_dict ) )
    return ref_dict

def get_log ( revision_range ):
    log = []
    output = popen ( [ 'git', 'rev-list', '--pretty=oneline', revision_range ], stdout = subprocess.PIPE ).stdout
    regex = re.compile ( br"([A-Za-z0-9]{40}) (.*)" )
    for line in output:
        match = regex.match ( line )
        if not match:
            error ( 'failed to match regex on `git rev-list --pretty=oneline` output line' )
        log.append ( ( match.group ( 1 ), match.group ( 2 ) ) )
    if args.verbosity >= 2:
        print ( "Parsed log: " + str ( log ) )
    return log

def get_diff ( tree_ish, second = None ):
    command = [ 'git', 'diff-tree', '-p', '--no-commit-id', tree_ish ]
    if second:
        command.append ( second )
    return run_command ( command, ret = 'output' )

def get_best_ancestor ( ref_list, commit ):
    current = None
    for ref in ref_list:
        res = run_command ( [ 'git', 'merge-base', ref, commit ], ret = 'output' )
        if not current or run_command ( [ 'git', 'merge-base', '--is-ancestor', res, current ] ):
            current = res
    return current

class Signal:
    def __init__ ( self ):
        self.subscribers = []

    def subscribe ( self, subscriber ):
        self.subscribers.append ( subscriber )

    def unsubscribe ( self, subscriber ):
        self.subscribers.remove ( subscriber )

    def __call__ ( self, *args, **kwargs ):
        for subscriber in self.subscribers:
            subscriber ( *args, **kwargs )