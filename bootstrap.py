#!/usr/bin/env python
from __future__ import unicode_literals, print_function

import commands
import os
import platform
import subprocess
import sys

import virtualenv
from virtualenv import create_environment, Logger


WINDOWS = platform.system() == "Windows"


def bail(msg):
    if not WINDOWS:
        # show errors with ANSI color red
        msg = "\x1b[31m" + msg + "\x1b[0m"
    print(msg)
    sys.exit(1)


# Send output to both logfile and console.
# ========================================

class Writer:
    fp = open('bootstrap.log', 'w+')
    def write(self, s):
        print(s, end='', file=sys.__stdout__)
        print(s, end='', file=self.fp)
    def flush(self):
        sys.__stdout__.flush()
        self.fp.flush()

sys.stdout = Writer()


# Check Python version.
# =====================

print("="*78)
print( "Bootstrapping Gittip using Python %s on %s."
     % (platform.python_version(), platform.platform())
      )
print("="*78)

if sys.version_info[:2] != (2, 7):
    msg = "Gittip requires Python 2.7.x. You're using %s."
    bail(msg % platform.python_version())


# Check for existing virtualenv.
# ==============================

if os.path.isdir("env"):
    bail("""\
Directory 'env' already exists. Bailing, because bootstrap.py expects to be
able to create that directory. Have you already run bootstrap.py?""")
elif os.path.exists("env"):
    bail("""\
File 'env' exists (though it's not a directory). Bailing, because bootstrap.py
expects to be able to create that directory itself. What have you done?!""")


# Check for activated virtualenv.
# ===============================
# Gittip owns its virtualenv, not the other way around. The reason is to make
# things user-friendly for developers coming from other languages and maybe
# even designers. An experience Python dev will still be able to install Gittip
# into their own virtualenv, of course, if that's what they want. This check is
# intended as an aide for those not looking to void the warranty.

if 'VIRTUAL_ENV' in os.environ:
    bail("""\
You're in a virtualenv. Please deactivate it and run again, because
bootstrap.py expects to create its own virtualenv.""")
if 'WORKING_ENV' in os.environ:
    bail("""\
You're in a workingenv (really?!). Please deactivate it and run again, because
bootstrap.py expects to create its own virtualenv.""")


# Create the virtualenv.
# ======================

virtualenv.logger = Logger([(Logger.level_for_integer(2 - 1), sys.stdout)])
create_environment( "env"
                  , site_packages=False
                  , clear=False
                  , unzip_setuptools=True
                  , use_distribute=True
                  , prompt="[gittip] "
                  , search_dirs=['vendor']
                  , never_download=True
                  , no_setuptools=False
                  , no_pip=False
                   )


# Populate the virtualenv.
# ========================
# Modify requirements.txt (placing tarballs in vendor/) to change what gets
# installed.

pip = os.path.join("env", "Scripts" if WINDOWS else "bin", "pip")
to_install = ( ["-r", "requirements.txt"]
             , ["./vendor/nose-1.1.2.tar.gz"]
             , ["-e", "./"]
              )
for thing in to_install:
    retcode = subprocess.call([pip, "install"] + thing)
    if retcode > 0:
        bail("""\
Failed to bootstrap Gittip. :(

Need help?

    1. See if anyone is around on IRC: http://chat.gittip.com/

    2. Paste your bootstrap.log at https://gist.github.com/ and link it in a
       new GitHub issue: https://github.com/gittip/www.gittip.com/issues/new.
""")


# Output a welcome message.
# =========================
# Tailor the message for Windows or Unix.

WELCOME = """\
==============================================================================

                             Welcome to Gittip!
                             ~~~~~~~~~~~~~~~~~~

              Source:      https://github.com/gittip/www.gittip.com
              Production:  https://www.gittip.com/
              Local:       Right here! :D
              Help:        https://www.gittip.com/for/contributors/

------------------------------------------------------------------------------

Greetings, program! %(green)sSuccess!%(default_color)s You now have a so-called "Python virtual
environment" (a.k.a. a "virtualenv") at ./env/, into which is installed the
gittip Python library and all its dependencies.

This virtualenv is your local development sandbox for Gittip. Next steps:

    1. %(green)s"Activate" your new virtualenv by running `%(activate)s`.%(default_color)s If
       your prompt sprouts a "[gittip] ", it worked. Activating a Python
       virtualenv configures your current shell session, and you need to do
       this every time you want to work with the virtualenv in a new shell
       session. To deactivate the virtualenv simply type "deactivate" (it can
       be tab-completed).

    2. %(green)sExplore the gittip cli.%(default_color)s Once you're in your virtualenv, you should
       have the gittip cli on your path. Try out the following commands to
       get started:

       [gittip] %(prompt)s gittip help
       [gittip] %(prompt)s gittip test
       [gittip] %(prompt)s gittip run

    3. %(green)sChange some source code!%(default_color)s

       - gittip/ contains our Python library
       - scss/ contains SCSS files
       - tests/ contains tests
       - www/ contains HTTP endpoints as so-called "simplates"

=============================================================================="""

if WINDOWS:
    listing = commands.getoutput("dir").splitlines()
    ls_output = "".join([line for line in listing if "env/" in line])
    if not ls_output:
        ls_output = "Eep!"
    welcome_config = { "green": ""
                     , "default_color": ""
                     , "activate": "env\\Scripts\\activate"
                     , "ls": "dir"
                     , "ls_output": ls_output
                     , "prompt": ">"
                      }
else:
    welcome_config = { "green": "\x1b[32m"
                     , "default_color": "\x1b[0m"
                     , "activate": "source env/bin/activate"
                     , "ls": "ls"
                     , "ls_output": commands.getoutput("ls -FGl | grep env/")
                     , "prompt": "$"
                      }
print(WELCOME % welcome_config)
