# SimpleLock #

A Mercurial extension offering simple file locking for unmergable files

> Cloned for backup purposes from <https://foss.heptapod.net/mercurial/tortoisehg/thg-build-deps/simplelock> (thanks to [Heptapod](https://heptapod.net) for providing Mercurial support).

## Purpose ##

Mercurial is not well suited for development that involves (binary)
files that cannot be merged. One example is specification development
using tools such as Framemaker or Word. Parallel versions of files occur
naturally in Mercurial, so in trying to prevent this, we are "going
against the grain". At the same time, introducing a different tool like
Subversion is obviously not very attractive.

## Configuration ##

This locking feature requires a special purpose lock repository. The
repository holding this extension is an appropriate lock repository,
because it has an empty **locked** file. The team's lock repository must
be globally accessible with the same write permissions as the work
repositories.

Semantically one can think of the lock repository like a white-board.
You write your name and file on it prior to editing any file, and then
remove your name once your done. So long as all of your coworkers do the
same, no merges will be required.

A single lock repository can manage locks for multiple work
repositories. The suggested usage is to have a single lock repository
per organization.

This extension must be enabled. On Windows it will be packaged with
TortoiseHg > 3.7 and simply needs to be enabled in the Settings tool. On
Linux the extension must be configured in ~/.hgrc by adding these lines:

```
#!python

[extensions]
simplelock = location of simplelock.py
```

To test that this was done correctly, try 'hg help simplelock'. You
should see the extension help text. Each user must clone the team's
lock repository and configure the location of this clone:

```
#!python

[simplelock]
repo = ~/work/locks
```

Now 'hg locks' should list the locked files in your work repository.

An **.hglocks** file can be added to each work repository, describing
the patterns of files which are considered _lockable_. The format is the
same as .hgignore. These files will be shown by 'hg locks -u' and they
will be displayed by the TortoiseHg lock dialog even when unlocked. It
makes it easier to find the files which are frequently locked.  You may
lock files even if they are not in this list.

## Workflow ##

Use of the locking API is completely voluntary. The users must use
discipline to remember to lock files before editing them, and then
unlock them again after committing and pushing their changes.

The crucial thing is that users stay up to date with changes from others
by pulling from the central team repository often and pushing as soon as
modifications are done. If you are not editing the most recent version
of the file, then locking will not prevent a merge. The workflow looks
like this:

* hg lock FILE
* hg pull --update
* edit FILE
* hg commit FILE
* hg push
* hg unlock FILE

Note that the only operation that enforces the lock is the lock command
itself. The lock will fail if the file is already locked.  If users do not
consistently acquire the lock prior to editing the file, then merges can
still be required.

## Commands ##

The simplelock extension adds three new commands to Mercurial.

1. hg locks - lists locked files in the current work repository.
2. hg lock FILE - marks a file as locked. This adds a line to the **locked** file in the user's local lock repository containing the repository identifier, the current branch of the work repository, the user's name (as it is known to Mercurial), and the editing purpose - which defaults to 'editing'. The lock repository is then committed and pushed.
3. hg unlock FILE - removes a locked file's lock information from the local user's lock repository. The lock repository is then committed and pushed.

lock, and unlock operations might all fail in the push phase if some
other user has pushed changes to the lock repository since the last time
you synchronized. If they fail you should retry the failed locking
operation.

## Details ##

The file locks are named-branch aware. A lock only pertains to the named
branch on which it was made. In this regard the lock tool assumes that
named-branches are long lived and seldom (or never) merged.

Only the user who locked a files is allowed to unlock it using the 'hg
unlock' command, unless --force is specified (in an emergency).

The master lock repository must be publishing, meaning commits pushed to
it must become public phase.

It is highly recommended to use the mercurial keyring extension or other
mechanism to avoid having to enter passwords for each operation.

## See Also ##

Note there are two other locking extensions, each with different pros and cons:

1. https://www.mercurial-scm.org/wiki/LockExtension
2. https://bitbucket.org/sorenmat/hglock/

The notable benefits of this extension are that it does not require any
additional infrastructure, just a public lock repository, plus it has
TortoiseHg integration.

Full disclosure: I borrowed some of the excellent prose of the
LockExtension for this README

## TODO ##

* read-only marking of unlocked lockable files (.hglocks)
* post-push hook to auto-unlock locked files
