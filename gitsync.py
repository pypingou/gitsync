#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# gitsync - a git-based synchronisation deamon.
#
# Copyright (C) 2011-2014 Pierre-Yves Chibon
# Author: Pierre-Yves Chibon <pingou@pingoured.fr>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or (at
# your option) any later version.
# See http://www.gnu.org/copyleft/gpl.html  for the full text of the
# license.
"""

import argparse
import ConfigParser
import logging
import os
import subprocess
import threading
import time

import watchdog
import watchdog.events
from watchdog.observers import Observer

from pygit2 import Repository, Signature
from pygit2 import (GIT_STATUS_WT_NEW, GIT_STATUS_WT_DELETED,
                    GIT_STATUS_WT_MODIFIED)


__version__ = '1.0.0'


# Initial simple logging stuff
logging.basicConfig()
LOG = logging.getLogger('gitsync')

SETTINGS_FILE = os.path.join(
    os.path.expanduser('~'), '.config', 'gitsync')
if not os.path.exists(SETTINGS_FILE):
    SETTINGS_FILE = '/etc/gitsync.cfg'

OFFLINE_FILE = os.path.join(
    os.environ['HOME'], '.config', 'gitsync.offline')

# Five seconds of sleep before pushing.
WAIT_N = 10


def get_arguments():
    ''' Set the command line parser and retrieve the arguments provided
    by the command line.
    '''
    parser = argparse.ArgumentParser(
        description='gitsync')
    parser.add_argument(
        '--config', dest='config', default=SETTINGS_FILE,
        help='Configuration file to use instead of `%s`.' % SETTINGS_FILE)
    parser.add_argument(
        '--info', dest='info', action='store_true',
        default=False,
        help='Expand the level of information returned')
    parser.add_argument(
        '--debug', dest='debug', action='store_true',
        default=False,
        help='Expand even more the level of information returned')
    parser.add_argument(
        '--daemon', dest='daemon', action='store_true',
        default=False,
        help='Run gitsync in a daemon mode')

    return parser.parse_args()


def run_cmd(cmd):
    """ Run a given command using the popen module.
    """
    LOG.debug('run cmd: `%s`' % ' '.join(cmd))
    process = subprocess.Popen(
        cmd,
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE)
    if not process.returncode:
        LOG.info('OUTPUT: ' + process.communicate()[0].strip())
    return process.returncode


def run_pull_rebase(repo_path):
    """ Run the git pull --rebase command and react accordingly to the
    success of the task.
    """
    cwd = os.getcwd()
    os.chdir(repo_path)
    run_cmd(['git', 'stash'])
    outcode_pull = run_cmd(['git', 'pull', '--rebase'])
    run_cmd(['git', 'stash', 'pop'])
    os.chdir(cwd)
    if not outcode_pull:
        if os.path.exists(OFFLINE_FILE):
            os.remove(OFFLINE_FILE)
    else:
        if not os.path.exists(OFFLINE_FILE):
            open(OFFLINE_FILE, 'w')
            print 'Could not fetch from the remote repository'
        else:
            LOG.info('Could not fetch from the remote repository')


def run_push(repo_path):
    """ Run the git push command. """
    cwd = os.getcwd()
    os.chdir(repo_path)
    outcode = subprocess.call('git push', shell=True)
    os.chdir(cwd)
    return outcode


def docommit(repo, index, msg):
    index.write()
    tree = index.write_tree()
    head = repo.lookup_reference('HEAD').get_object()
    commit = repo[head.oid]
    committer = Signature('gitsync', 'root@localhost', time.time(), 0)
    LOG.info('Doing commit: %s' % msg)
    sha = repo.create_commit(
        'refs/heads/master', committer, committer, msg, tree, [head.hex])
    commit = repo[sha]
    return commit


class GitSyncEventHandler(watchdog.events.FileSystemEventHandler):
    """ Dedicated Event Handler for gitsync. """

    def __init__(self, repopath):
        """ Constructor for the GitSyncEventHandler class.

        Instanciate a pygit2.Repository object using the path to the repo
        provided.
        """

        self.repo = Repository(repopath)
        self.log = LOG
        self.do_push = False
        self.thread = None

    def pusher_thread(self):
        self.log.debug("pusher thread is waiting %i seconds", WAIT_N)
        self.log.debug("pusher thread waking up...")

        if self.do_push:
            self.log.debug("Pushing")
            if not os.path.exists(OFFLINE_FILE):
                run_pull_rebase(self.repo.workdir)
                run_push(self.repo.workdir)

            # Set this flag back to false when we're done
            self.do_push = False
            self.log.debug("  do push: %s", self.do_push)
        else:
            self.log.debug("  (push not actually set.. bailing out.)")

        return

    def on_any_event(self, event):
        if '.git' in event.src_path:
            return
        if not self.do_push:
            self.log.debug("Something changed, prepare to push")
            self.do_push = True
            self.thread = threading.Timer(WAIT_N, function=self.pusher_thread)
            self.thread.start()

    def on_deleted(self, event):
        """ Upon deletion, delete the file from the git repo. """
        if '.git' in event.src_path:
            return
        self.log.debug('on_deleted')
        self.log.debug(event)

        filename = event.src_path.split(self.repo.workdir)[1]
        msg = 'Remove file %s' % filename
        self.log.info(msg)
        index = self.repo.index
        index.remove(filename)
        docommit(self.repo, self.repo.index, msg)

    def on_modified(self, event):
        """ Upon modification, update the file in the git repo. """
        if '.git' in event.src_path:
            return
        self.log.debug('on_modified')
        self.log.debug(event)

        filename = event.src_path.split(self.repo.workdir)[1]
        msg = 'Update file %s' % filename
        self.log.info(msg)
        self.repo.index.add(filename)
        docommit(self.repo, self.repo.index, msg)

    def on_moved(self, event):
        """ Upon move, update the file in the git repo. """
        if '.git' in event.src_path:
            return
        self.log.debug('on_moved')
        self.log.debug(event)

        filename_from = event.src_path.split(self.repo.workdir)[1]
        filename_to = event.dest_path.split(self.repo.workdir)[1]
        msg = 'Move file from %s to %s' % (filename_from, filename_to)
        self.log.info(msg)
        self.repo.index.remove(filename_from)
        self.repo.index.add(filename_to)
        docommit(self.repo, self.repo.index, msg)


class GitSync(object):
    """ Main class of the project, handles the command line arguments,
    set the deamon, manage the Git repo.
    """

    def __init__(self, configfile=SETTINGS_FILE, daemon=False):
        self.log = LOG
        self.settings = Settings(configfile)
        if not self.settings.work_dir:
            raise GitSyncError(
                'No git repository set in %s' % configfile)

        self.observers = []
        if not daemon:
            for repo in self.settings.work_dir.split(','):
                if repo.strip():
                    self.update_repo(os.path.expanduser(repo.strip()))
        else:
            for repo in self.settings.work_dir.split(','):
                repo = repo.strip()
                if repo:
                    # First update the repo as it is now
                    self.update_repo(os.path.expanduser(repo))
                    # Then starts the daemon mode
                    observer = Observer()
                    observer.schedule(
                        GitSyncEventHandler(repo), repo, recursive=True)
                    observer.start()
                    self.observers.append(observer)

    def update_repo(self, reponame):
        """ For a given path to a repo, pull/rebase the last changes if
        it can, add/remove/commit the new changes and push them to the
        remote repo if any.

        :kwarg reponame, full path to a git repo.
        """
        self.log.info('Processing %s' % reponame)
        if not os.path.exists(reponame):
            raise GitSyncError(
                'The indicated working directory does not exists: %s' %
                reponame)
        try:
            repo = Repository(reponame)
        except Exception, err:
            print err
            raise GitSyncError(
                'The indicated working directory is not a valid git '
                'repository: %s' % reponame)

        run_pull_rebase(repo.workdir)

        index = repo.index
        dopush = False
        origin = None

        index = repo.index
        ## Add or remove to staging the files according to their status
        if repo.status:
            status = repo.status()
            for filepath, flag in status.items():
                if flag == GIT_STATUS_WT_DELETED:
                    msg = 'Remove file %s' % filepath
                    self.log.info(msg)
                    del index[filepath]
                    docommit(repo, index, msg)
                    dopush = True
                elif flag == GIT_STATUS_WT_NEW:
                    msg = 'Add file %s' % filepath
                    self.log.info(msg)
                    index.add(filepath)
                    docommit(repo, index, msg)
                    dopush = True
                elif flag == GIT_STATUS_WT_MODIFIED:
                    msg = 'Change file %s' % filepath
                    self.log.info(msg)
                    index.add(filepath)
                    docommit(repo, index, msg)
                    dopush = True

        ## if there is a remote, push to it
        if dopush and not os.path.exists(OFFLINE_FILE):
            run_pull_rebase(repo.workdir)
            run_push(repo.workdir)


class GitSyncError(Exception):
    """ General Error class for gitsync. """

    def __init__(self, value):
        """ Instanciante the error. """
        self.value = value

    def __str__(self):
        """ Represent the error. """
        return repr(self.value)


class Settings(object):
    """ gitsync Settings """
    # Work directory
    work_dir = ''

    def __init__(self, configfile=SETTINGS_FILE):
        """Constructor of the Settings object.
        This instanciate the Settings object and load into the _dict
        attributes the default configuration which each available option.
        """
        self._dict = {'work_dir': self.work_dir}
        self.load_config(configfile, 'gitsync')

    def load_config(self, configfile, sec):
        """Load the configuration in memory.

        :arg configfile, name of the configuration file loaded.
        :arg sec, section of the configuration retrieved.
        """
        parser = ConfigParser.ConfigParser()
        configfile = os.path.join(os.environ['HOME'], configfile)
        is_new = self.create_conf(configfile)
        parser.read(configfile)
        if not parser.has_section(sec):
            parser.add_section(sec)
        self.populate(parser, sec)
        if is_new:
            self.save_config(configfile, parser)

    def create_conf(self, configfile):
        """Check if the provided configuration file exists, generate the
        folder if it does not and return True or False according to the
        initial check.

        :arg configfile, name of the configuration file looked for.
        """
        if not os.path.exists(configfile):
            dirname = os.path.dirname(configfile)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            return True
        return False

    def save_config(self, configfile, parser):
        """Save the configuration into the specified file.

        :arg configfile, name of the file in which to write the configuration
        :arg parser, ConfigParser object containing the configuration to
        write down.
        """
        with open(configfile, 'w') as conf:
            parser.write(conf)

    def __getitem__(self, key):
        hashstr = self._get_hash(key)
        if not hashstr:
            raise KeyError(key)
        return self._dict.get(hashstr)

    def populate(self, parser, section):
        """Set option values from a INI file section.

        :arg parser: ConfigParser instance (or subclass)
        :arg section: INI file section to read use.
        """
        if parser.has_section(section):
            opts = set(parser.options(section))
        else:
            opts = set()

        for name in self._dict.iterkeys():
            value = None
            if name in opts:
                value = parser.get(section, name)
                setattr(self, name, value)
                parser.set(section, name, value)
            else:
                parser.set(section, name, self._dict[name])


def main():
    """ Main function of the programm.
    """
    # Retrieve arguments
    args = get_arguments()

    global LOG
    if args.debug:
        LOG.setLevel(logging.DEBUG)
    else:
        LOG.setLevel(logging.INFO)

    try:
        gitsync = GitSync(configfile=args.config, daemon=args.daemon)
    except GitSyncError, msg:
        print msg
        return 1

    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, Exception):
        LOG.info('Stopping thread')
        for observer in gitsync.observers:
            observer.stop()

    LOG.debug('Waiting for threads to stop')
    for observer in gitsync.observers:
        observer.join()

    return 0


if __name__ == '__main__':
    main()
