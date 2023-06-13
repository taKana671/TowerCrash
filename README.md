# TowerCrash
Tower Crash Game made with Python and Panda3D

The blocks of a tower fall by gravity in Bullet World of Panda3d at the timing when a ball hit the tower. The trajectory of the ball is calculated by using Bézier curve.
All of the blocks are procedurally created, not by using 3D models. Press D key to toggle debug ON and OFF.

![demo_towercrash](https://user-images.githubusercontent.com/48859041/190886190-9438a433-bb0d-4cf7-b912-b4172f7305f3.png)

# Requirements
* Python 3.11
* Panda3D 1.10.13

# Environment
* Windows11

# Usage
* Execute a command below on the command line.
```
>>>python towercrash.py
```

### How to play:
* Dragging the mouse left and right on the game screen enables the camera to rotate.
* Click on a block having the same color with a ball to delete the block.
* A multi colored ball can delete all of the blocks having the same color with the clicked block.
* A black and white ball can delete all of the blocks having the different color with the clicked block.
* If successfully break the tower, you can try the next one.
* Let's enjoy 7 towers!

![seven_towers](https://user-images.githubusercontent.com/48859041/190887173-18fb07cc-245c-494e-81bd-4e095eb45ad7.png)
