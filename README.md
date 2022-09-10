

It's time to play GAME NAME HERE!

Install
-------

You need to run the game from your favorite command shell, using a Python "virtual env" or "venv".  First, create a venv in the game directory:

    % python3 -m venv .venv

Now activate it.  On Windows and most UNIX shells, the command to activate a venv is:

    % ./.venv/bin/activate

If that doesn't work, try this command:

    % source .venv/bin/activate

Next you'll need to pull in the source for `wasabi2d`.
We're using a published but unreleased-as-a-package version of wasabi2d, revision 6e855f65f9b4326e8ec6647caf7d4990c43a618e.

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


Goal
----

Get through every level.  Every goal has some objectives:

* You must collect all the floating gems.  Just touch the floating gem to collect it!  Some levels may not have any floating gems.

* You must kill all the monsters.  You must shoot a monster to kill it.  Be careful, monsters will kill you!  Some levels may not have any monsters.

Once you've collected all the floating gems and killed all the monsters, you're ready for
departure--but you have to get to the departure point.  This is a flat object that pops up
a little bit when it's ready to send you to the next level.

Platform mechanics
------------------

Movement features of your character:

* Double jump!

* Wall slide and wall jump!  Jumping from a wall slide restores your jump.

* "Coyote time"!  If you jump immediately after falling off a ledge, or pushing
  away from a wall, you'll be rewarded with getting your double jump back.

* "Coyote time warp speed"!  If you're holding left or right when you execute
  a jump during "coyote time", you'll immediately warp to full speed in that
  direction!

Color
-----

Color plays a big role in GAME NAME HERE.  There are six colors:

* red
* orange
* yellow
* green
* blue
* purple

Each of them can be toggled on and off in various ways.
And when a color is turned off, all the platforms and walls
of that color disappear!  They only come back when you turn
that color back on.

(Gray platforms are super safe--they never disappear on you.)

Terrain
-------

You'll see the following things in levels:

* Color switches!  These turn a color on or off.  You can toggle
  a color's state by touching--or shooting--one of its switches.

* Colored platforms!  These are platforms that disappear when
  you turn a color off--and reappear when you turn the color back
  on again.

* Color actuators!  These are colored tubes that give you the ability
  to toggle a color whenever you want!  Only lasts through the end
  of the level.

* Checkpoints!  These little mushroom guys save your current state:
  your current location and the current on/off state of all the colors.
  The popped-up one is your current checkpoint.

* Jump restorers!  Touch one of these green diamonds while in the air,
  and you'll get *both* your jumps back!  Did someone say octuple-jump?
  I swear I heard someone say octuple-jump.

* Pass-through platforms!  These platforms are thinner

But it's not all good news.  You'll also see:

* Monsters!  You have to kill all of them, by shooting them.
  But be careful, if you touch one it'll kill you!

* Spikes!  If you fall on them you die!  Well, there's one exception:
  if you jump up through spikes from below, you'll pass through them safely!


Controls
--------

**A** or **Left arrow** to run left.

**D** or **Right arrow** to run right.

**Space** to jump.

**Enter** to shoot.

Number keys toggle a color, if you've picked up the correct color actuator:

**1** to toggle red.

**2** to toggle orange.

**3** to toggle yellow.

**4** to toggle gree.

**5** to toggle blue.

**6** to toggle purple.


Development
-----------

We're using Tiled 1.9.1.
