
Install
-------

Create your virtual env and install the dependencies:

    pip install -e requirements.txt

We're using a published but unreleased-as-a-package version of wasabi2d, revision 38175c94531efc229c562e0721b9b50e80297401.


Gameplay
--------

Movement features of your character:

* Double jump!

* Wall slide and wall jump!  Jumping from a wall slide restores your jump.

* "Coyote time"!  If you jump immediately after falling off a ledge, or pushing
  away from a wall, you'll be rewarded with getting your double jump back.

* "Coyote time warp speed"!  If you're holding left or right when you execute
  a jump during "coyote time", you'll immediately warp to full speed in that
  direction!


Controls
--------

**A** or **Left arrow** to run left.

**D** or **Right arrow** to run right.

**Space** to jump.

**Enter** to shoot.


Development
-----------

We're using Tiled 1.9.1.
