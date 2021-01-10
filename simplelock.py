# Copyright 2016 Steve Borho <steve@borho.org>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.
#
"""simple file locking for unmergable files

This locking feature requires a special purpose lock repository.  Each lock and
unlock operation involves making a change to the local clone of a central lock
repository, commit, then push.

Use of the locking API is completely voluntary. Users users must exercise
discipline to remember to lock files before editing them and unlock them
again after comiting and pushing their changes.

An .hglocks file in the work repository may list file patterns of files that
are frequently locked. These files will be shown by 'hg locks -u' even when
unlocked.

The master lock repository must be publishing, meaning commits pushed to it
must become public phase."""

import os

from mercurial.i18n import _
from mercurial.node import bin, hex, short, nullid, nullrev
from mercurial import hg, error, registrar, commands, scmutil, util
from mercurial import match as matchmod

cmdtable = {}
command = registrar.command(cmdtable)


def getlockrepo(ui):
    lockroot = ui.config('simplelock', 'repo')
    if not lockroot:
        raise error.Abort(_('No lock repository configured'))
    return hg.repository(ui, lockroot)


def commitpush(repo, **opts):
    commands.commit(repo.ui, repo, **opts)
    try:
        commands.push(repo.ui, repo)
    except error.Abort:
        repo.ui.warn(_('Lock push failed, please retry\n'))


def readlockables(repo):
    'return files matched by .hglocks pattern, if present'
    path = repo.wjoin('.hglocks')
    if os.path.exists(path):
        pats = matchmod.readpatternfile(path, repo.ui.warn)
        m = matchmod.match(repo.root, '', [], pats, ctx=repo[None])
        return sum(repo.status(match=m, clean=True), [])
    else:
        return []


def parseLocks(repo):
    lockrepo = getlockrepo(repo.ui)
    dfile = lockrepo.wjoin('locked')
    if not os.path.exists(dfile):
        repo.ui.warn(_('Locked file not present, abort'))
        return {}

    locks = {}
    repoid = hex(repo[0].node())
    curbranch = repo.dirstate.branch()
    with open(dfile, 'r') as f:
        for line in f:
            fields = line.strip().split('\t')
            if len(fields) != 5:
                continue
            rid, branch, wfile, user, purpose = fields
            if rid == repoid and branch == curbranch:
                locks[wfile] = [user, purpose]
    return locks


def lsync(repo):
    'remove all local changes and synchronize with public lock repo'
    lockrepo = getlockrepo(repo.ui)

    # clean uncommitted changes
    if lockrepo[None].dirty():
        commands.update(lockrepo.ui, lockrepo, clean=True)

    # strip outgoing
    s = lockrepo.revs('outgoing()')
    if s:
        from hgext import strip as stripmod
        repo.ui.status(_('Stripping local commits not in public lock repo'))
        stripmod.stripcmd(lockrepo.ui, lockrepo, force=True, rev=list(s))

    # pull and update
    lockrepo.ui.pushbuffer()
    commands.pull(lockrepo.ui, lockrepo, update=True)
    lockrepo.ui.popbuffer()


@command("locks",
         [('u', 'unlocked', None, _('also show unlocked files'))],
         _('hg locks'))
def lockscmd(ui, repo, *pats, **opts):
    """displays the locked files in this repository"""
    lsync(repo)
    locks = parseLocks(repo)
    lockables = readlockables(repo)

    # use a predictable sort order regardless of --unlocked
    sum = sorted (set(lockables) | set(locks))
    for wfile in sum:
        if wfile in locks:
            user, purpose = locks[wfile]
            ui.status(_('%s is locked by %s for %s\n') % (wfile, user, purpose))
        elif opts.get('unlocked'):
            ui.status(_('%s is unlocked\n') % wfile)

@command("unlock",
         [('f', 'force', None, _('force unlock'))],
          _('hg unlock [-f] FILES...'))
def unlockcmd(ui, repo, file1, *pats, **opts):
    '''unlock one or more locked files

    The line(s) in the lock file are removed, the lock repo is then
    committed and pushed. Only locks made by the user are allowed
    to be deleted, unless --force is specified.
    '''
    repoid = hex(repo[0].node())
    curbranch = repo.dirstate.branch()
    curuser = ui.username()
    m = scmutil.match(repo[None], (file1,) + pats, opts)
    ulock = m.files()

    lsync(repo)

    lockrepo = getlockrepo(repo.ui)
    dfile = lockrepo.wjoin('locked')

    cleared = set()
    outlines = []
    with open(dfile, 'r') as f:
        for line in f:
            fields = line.strip().split('\t')
            if len(fields) == 5:
                rid, branch, wfile, user, purpose = fields
                if rid == repoid and branch == curbranch and wfile in ulock:
                    if user == curuser or opts.get('force', False):
                        cleared.add(wfile)
                        continue
                outlines.append(line)

    if len(cleared) != len(ulock):
        if len(m.files()) == 1:
            ui.warn(_('No locks found for specified file\n'))
        else:
            ui.warn(_('Only %d of %d files were locked\n') % (len(cleared),
                                                              len(ulock)))
        return 1

    with open(dfile, 'w') as f:
        f.write(''.join(outlines))

    commitpush(lockrepo, message='remove lock')


@command("lock",
         [('p', 'purpose', '', _('lock (edit) purpose'), _('TEXT'))],
          _('hg lock [-p MESSAGE] FILES...'))
def lockcmd(ui, repo, file1, *pats, **opts):
    """marks one or more files as locked

    If locks are created, the lock repo is committed and pushed.
    """
    lsync(repo)
    locks = parseLocks(repo)
    m = scmutil.match(repo[None], (file1,) + pats, opts)

    for wfile in m.files():
        if locks.get(wfile) is not None:
            raise error.Abort(_('%s is already locked\n') % wfile)

    lockrepo = getlockrepo(repo.ui)
    repoid = hex(repo[0].node())
    curbranch = repo.dirstate.branch()
    user = ui.username()
    purpose = opts.get('purpose') or 'editing'

    dfile = lockrepo.wjoin('locked')
    with open(dfile, 'a') as f:
        for wfile in m.files():
            f.write('\t'.join([repoid, curbranch, wfile, user, purpose]) + '\n')

    commitpush(lockrepo, message='add lock')
