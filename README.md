Dr. Farb's Huepocalypse
=======================

![# Screenshot](/images/screenshot.png)

Overview
--------

Dr. Hugh Farb, you've *really* done it this time!

Your wavelength dimensional convolver has overloaded...
breaking *color itself!*  All the color is starting to
drain out of the world, starting with the lower frequencies.
I never thought I'd have a use for this word, but it's...
a ***huepocalypse!***

If you don't fix it soon, the entire planet will turn red!
We think all color might drain out of the entire solar
system--not that we'd notice, as we'll all be dead by then.

You're going to have to put on that silly silver color
stabilization suit and run out and fix everything!  Good thing
you're such a gym rat--all that cardio and parkour is
going to come in handy!


*Dr. Farb's Huepocalypse* was written by Larry Hastings
and Dan Pope in September 2022 for the
[PyWeek 34](https://pyweek.org/34/) game programming contest.


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

Next, if you cloned our GitHub repo, you'll need to pull in the source for `wasabi2d`.
We're using a published but unreleased-as-a-package version of wasabi2d, revision
18bba079e38d0c39ca55e1f9126840a8ad933328.  If you got the game as the PyWeek `.zip`
file, you can skip this step.

    % git submodule init vendor/wasabi2d
    % git submodule update

Now you can install the game's dependencies:

    % pip3 install -r requirements.txt

This will install the vendored copy of wasabi2d too.  Now the game should be ready to run:

    % python3 main.py

Phew!

If you exit this venv, or attempt to run the game from a different shell,
you'll need to "activate" the venv again in that instance of the shell.
If you forget to activate, the game will complain with a

    ModuleNotFoundError: No module named 'wasabigeom'

error.

Goal
----

Huepocalypse is a platformer game.  You control a scientist named Dr. Hugh Farb.

Your goal is to finish every level.  Every goal has some objectives:

* You must collect all the floating gems.  Just touch the floating gem to collect it!  Some levels may not have any floating gems.

* You must kill all the monsters.  You must shoot a monster to kill it.  Be careful, monsters will kill you!  Some levels may not have any monsters.

Once you've collected all the floating gems and killed all the monsters, you're ready for
departure--but you have to get to the departure point.  This is a little door that
opens when it's ready to send you to the next level.

You have infinite lives.  So, you've got that going for you.

Platform mechanics
------------------

Movement features of your character:

* Run!  In two deluxe directions--left *and* right!

* Not merely a single jump, not for you!  You get a *double* jump!

* *Wall slide* and *wall jump!*  Jumping from a wall slide restores your
  second jump.

* *Coyote time!*  If you jump immediately after falling
  off a ledge, or pushing away from a wall, you'll be rewarded with
  getting your double jump back.  But be quick--it's a very short winow!

* And new for 2022: *coyote time warp speed!*  If you're holding
  left or right when you execute a jump during "coyote time", you'll
  immediately warp to full speed in that direction!

Color
-----

Color plays a big role in the Huepocalypse.  There are six colors:

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

But it gets more complicated!  When you turn on or off one
of the three *secondary* colors, it also affects the two
related *primary* colors:

* orange also affects red and yellow
* green also affects yellow and blue
* purple also affects blue and red

When you turn off orange, you turn off red, orange, and yellow!
And when you turn orange back on, you turn red, orange, and yellow
all back on at once!

(Though it doesn't go the other way--toggling red doesn't affect
orange or purple.)

Oh, I almost forgot!  There's one more wrinkle.  The blue and
purple colors are even more unstable than the rest.  I'm afraid
that you can only turn them off for short bursts.  Then they
pop back on all by themselves!


Terrain
-------

You'll see the following sorts of objects and terrain in levels:

* *Platforms!*  They're all over the place.  Not sure how they stay
  up like that.

* *Pass-through platforms!*  These platforms are thinner than normal
  and a little see-through.
  You can jump up through them from below!  Maybe it's old fashioned--
  I think this was first popularized nearly forty years ago--but
  sometimes the old ways are the best ways.

* *Color switches!*  These are little colored pedestals that can
  turn a color on or off.  You activate a color switch by
  touching it--or shooting it!

* *Colored platforms!*  These are platforms that disappear when
  you turn a color off--and reappear when you turn the color back
  on again.  But you better be careful--if you're inside a colored
  platform when it reappears, you'll die!

* *Checkpoints!*  These little mushroom guys save your current
  your current location.  If you die--egad!--you'll reappear at
  a checkpoint.  Checkpoints look like mushrooms--I'm not sure
  why, that's how they came from the cfactory.  The shiny red
  pressed-in red one is your current checkpoint, and all the
  other ones are more brown and tall and skinny.  Checkpoints
  also remember the current state of all the color switches,
  so be sure to touch one pretty often!

* *Jump restorers!*  Touch one of these green diamonds while in the air,
  and you'll get *both* your jumps back!  Did someone say octuple-jump?
  I swear I heard someone say octuple-jump.

* *Springboards!*  Just touch one of these little plungers, and you'll
  go shooting up into the air like a firework!  Luckily for you,
  you don't also do the explody bit at the end.  Or, at least,
  I don't think so.

* *Signposts!*  Just walk by one of these signs to read it.
  It won't even slow you down!  But maybe you should read it
  anyway.  It just might have something interesting to say!

And there are even sometims things for you to pick up, like:

* *Gems!*  These floaty blue things have something to do with fixing
  the color problem.  I'm really not sure--all I know is, you have
  to pick up all of them before you can leave the level.  Just
  run up and touch one to collect it!  You might need to jump a little.

* *Color actuators!*  These look like colored tubes.  They give you
  the ability to toggle a color whenever you want!  Only lasts
  through the end of the level.

* A shiny new *Whitegun!*  This is a gun that shoots the color white.
  Use it to whitewash Monsters out of existence.  You can also shoot
  color switches!  Pity you can't take it with you when you exit a
  level.


But it's not all good news.  You'll also see:

* *Monsters!*  Little brown frowning circles--with red eyes!
  You have to kill all of them before you can leave--and
  the only way is by shooting them. But be careful, if you touch one
  it'll kill you!

* *Spikes!*  If you fall on them you die!  Well, there's one exception:
  if you jump up through spikes from below, you'll pass through them safely!

Oh, I almost forgot!  And we've saved the best for last.  One last bit
of terrain:

* Every level has one gen-u-ine patented *departure point!*
  Once you've killed all the monsters and picked up all the gems,
  the departure point will become active!  Just enter the little
  door to be whisked away, off to your next adventure.



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

**Ctrl-Q** to quit at any time.

Secret Command-Line Flags
-------------------------

If you want to skip the tutorial and just play the challenge levels,
run the game with the `-c` or `--challenge` flags:

    % python3 main.py -c

And if you want to jump to a particular level, just specify the
unique part of the level's filename.  All the level files are

    data/level_*.tmx

So, to jump straight to "Go Hunting", you'd run

    % python3 main.py go_hunting


Development
-----------

In case you want to make your own levels, we're using Tiled 1.9.1.
There are three tilesets.  We created "terrain maps" for the seven
colors of platforms but they don't work super-well--Tiled wants
way more tiles than just nine slice scaling.
