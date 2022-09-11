Developer Guide
===============

How To Install And Run
----------------------

Huepocalypse is written in Python 3.  We used Python 3.10 during development,
though it's possible other versions may work fine.

You need to run the game from your favorite command shell, using a Python "virtual env" or "venv".  First, create a venv in the game directory:

    % python3 -m venv .venv

Now activate it.  On Windows and most UNIX shells, the command to activate a venv is:

    % ./.venv/bin/activate

If that doesn't work, try this command:

    % source .venv/bin/activate

Next you'll need to pull in the source for `wasabi2d`.
We're using a published but unreleased-as-a-package version of wasabi2d, revision
18bba079e38d0c39ca55e1f9126840a8ad933328.

    % git submodule init vendor/wasabi2d
    % git submodule update

Now you can install the game's dependencies:

    % pip3 install -e requirements.txt

This will install the vendored copy of wasabi2d too.  Now the game should be ready to run:

    % python3 main.py

Phew!

If you exit this venv, or attempt to run the game from a different shell,
you'll need to "activate" the venv again in that instance of the shell.
If you forget to activate, the game will complain with a

    ModuleNotFoundError: No module named 'wasabigeom'

error.



In case you want to make your own levels, we're using Tiled 1.9.1.
There are three tilesets.  We created "terrain maps" for the seven
colors of platforms but they don't work super-well--Tiled wants
way more tiles than just nine slice scaling.
