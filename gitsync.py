#!/usr/bin/python

# -*- coding: utf-8 -*-

"""
# gitsync - a git-based synchronisation deamon.
#
# Copyright (C) 2011 Pierre-Yves Chibon
# Author: Pierre-Yves Chibon <pingou@pingoured.fr>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or (at
# your option) any later version.
# See http://www.gnu.org/copyleft/gpl.html  for the full text of the
# license.
"""


from pygit2 import Repository, Signature
from pygit2 import (GIT_STATUS_WT_NEW, GIT_STATUS_WT_DELETED,
    GIT_STATUS_WT_MODIFIED)
from time import gmtime, strftime, time
import ConfigParser
import logging
import os
import subprocess
import sys


# Initial simple logging stuff
logging.basicConfig()
LOG = logging.getLogger('gitsync')
if '--debug' in sys.argv or '-d' in sys.argv:
    LOG.setLevel(logging.DEBUG)
elif '--verbose' in sys.argv or '-v' in sys.argv:
    LOG.setLevel(logging.INFO)

SETTINGS_FILE = os.path.join(os.environ['HOME'], '.config',
                    'gitsync')
OFFLINE_FILE = os.path.join(os.environ['HOME'], '.config',
                    'gitsync.offline')

def run_cmd(cmd):
    """ Run a given command using the popen module.
    """
    LOG.debug('run cmd: `%s`' % ' '.join(cmd))
    process = subprocess.Popen(cmd,
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
    run_cmd(['git', 'stash', 'apply'])
    run_cmd(['git', 'stash', 'clear'])
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


class GitSync(object):
    """ Main class of the project, handles the command line arguments,
    set the deamon, manage the Git repo.
    """

    def __init__(self):
        self.log = LOG
        self.settings = Settings()
        if not self.settings.work_dir:
            raise GitSyncError(
                'No git repository set in %s' % SETTINGS_FILE)
        for repo in self.settings.work_dir.split(','):
            if repo.strip():
                self.update_repo(os.path.expanduser(repo.strip()))

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
                'The indicated working directory is not a valid git '\
                'repository: %s' %
                reponame)

        run_pull_rebase(repo.workdir)

        index = repo.index
        docommit = False
        origin = None

        index = repo.index
        ## Add or remove to staging the files according to their status
        if repo.status:
            status = repo.status()
            for filepath, flag in status.items():
                if flag == GIT_STATUS_WT_DELETED:
                    self.log.info('Removing files %s' % filepath)
                    del index[filepath]
                    docommit = True
                elif flag == GIT_STATUS_WT_NEW:
                    self.log.info('Adding files %s' % filepath)
                    index.add(filepath)
                    docommit = True
                elif flag == GIT_STATUS_WT_MODIFIED:
                    self.log.info('Modifying files %s' % filepath)
                    index.add(filepath)
                    docommit = True
        index.write()
        tree = index.write_tree()

        if docommit:
            head = repo.lookup_reference('HEAD')
            head = head.resolve()
            commit = repo[head.oid]
            msg = strftime('Commit: %a, %d %b %Y %H:%M:%S +0000',
                gmtime())
            committer = Signature('gitsync', 'root@localhost', time(), 0)
            self.log.info('Doing commit: %s' % msg)
            sha = repo.create_commit('refs/heads/master', committer,
                committer, msg, tree, [head.hex])
            commit = repo[sha]
            ## if there is a remote, push to it
            if not os.path.exists(OFFLINE_FILE):
                run_pull_rebase(repo.workdir)
                run_push(repo.workdir)
        else:
            self.log.info('No changes found')


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

    def __init__(self):
        """Constructor of the Settings object.
        This instanciate the Settings object and load into the _dict
        attributes the default configuration which each available option.
        """
        self._dict = {'work_dir': self.work_dir,
                     }
        self.load_config(SETTINGS_FILE, 'gitsync')

    def load_config(self, configfile, sec):
        """Load the configuration in memory.

        :arg configfile, name of the configuration file loaded.
        :arg sec, section of the configuration retrieved.
        """
        parser = ConfigParser.ConfigParser()
        configfile = os.path.join(os.environ['HOME'], configfile)
        isNew = self.create_conf(configfile)
        parser.read(configfile)
        if not parser.has_section(sec):
            parser.add_section(sec)
        self.populate(parser, sec)
        if isNew:
            self.save_config(configfile, parser)

    def create_conf(self, configfile):
        """Check if the provided configuration file exists, generate the
        folder if it does not and return True or False according to the
        initial check.

        :arg configfile, name of the configuration file looked for.
        """
        if not os.path.exists(configfile):
            dn = os.path.dirname(configfile)
            if not os.path.exists(dn):
                os.makedirs(dn)
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
        hash = self._get_hash(key)
        if not hash:
            raise KeyError(key)
        return self._dict.get(hash)

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


if __name__ == '__main__':
    #LOG.setLevel(logging.DEBUG)
    try:
        GitSync()
    except GitSyncError, msg:
        print msg
