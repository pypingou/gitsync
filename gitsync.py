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


from git import Repo, InvalidGitRepositoryError, GitCommandError
from time import gmtime, strftime
import ConfigParser
import logging
import os
import sys


# Initial simple logging stuff
logging.basicConfig()
LOG = logging.getLogger('gitsync')
if '--debug' in sys.argv:
    LOG.setLevel(logging.DEBUG)
elif '--verbose' in sys.argv:
    LOG.setLevel(logging.INFO)

SETTINGS_FILE = os.path.join(os.environ['HOME'], '.config',
                    'gitsync')


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
            repo = Repo(reponame)
        except InvalidGitRepositoryError:
            raise GitSyncError(
                'The indicated working directory is not a valid git '\
                'repository: %s' %
                reponame)

        index = repo.index
        docommit = False
        origin = None

        if repo.remotes and repo.remotes.origin:
            origin = repo.remotes.origin
            ## fetch and pull/rebase from the remote
            try:
                origin.fetch()
                if not repo.is_dirty():
                    origin.pull(rebase=True)
            except AssertionError:
                print 'Could not fetch from the remote repository'

        ## Add all untracked files
        if repo.untracked_files:
            self.log.info('Adding files %s' % repo.untracked_files)
            index.add(repo.untracked_files)
            docommit = True
        ## Add all files changed
        if repo.is_dirty():
            self.log.info('Repo is dirty, processing files')
            docommit = True
            for (path, stage), entry in index.entries.iteritems():
                path = repo.working_dir + '/' + path
                if os.path.exists(path):
                    index.add([path])
                else:
                    index.remove([path])

        if docommit:
            msg = strftime('Commit: %a, %d %b %Y %H:%M:%S +0000',
                gmtime())
            self.log.info('Doing commit: %s' % msg)
            index.commit(msg)
            ## if there is a remote, push to it
            if origin:
                try:
                    origin.pull(rebase=True)
                    origin.push()
                except GitCommandError:
                    raise GitSyncError(
                    'Could not push into the remote repository')
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
    try:
        GitSync()
    except GitSyncError, msg:
        print msg
