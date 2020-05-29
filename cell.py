# -*- coding: utf-8 -*-

"""
cellanneal.cell
~~~~~~~~~~~~~~~

This module contains the Cell class which stores the properties of cells and
related functions.
"""

from math import atan2, ceil, cos, floor, sin, sqrt
import time
import numpy as np
from skimage.draw import polygon
# from skimage.draw import circle, polygon
from scipy.ndimage import gaussian_filter

from drawing import draw_arc, draw_line, circle
from mathhelper import Rectangle, Vector


class Cell(object):
    """The Cell class stores information about a particular cell."""

    _REQUIRED_CONFIG = []

    def __init__(self, name):
        self._name = name

    @classmethod
    def checkconfig(cls, config):
        for required in cls._REQUIRED_CONFIG:
            if required not in config:
                raise ValueError(f'Invalid config: missing "{required}"')

    @property
    def name(self):
        return self._name


class Bacilli(Cell):
    """The Bacilli class represents a bacilli bacterium."""

    _REQUIRED_CONFIG = [
        'bacilli.maxSpeed',
        'bacilli.maxSpin',
        'bacilli.minGrowth',
        'bacilli.maxGrowth',
        'bacilli.minWidth',
        'bacilli.maxWidth',
        'bacilli.minLength',
        'bacilli.maxLength'
    ]

    def __init__(self, name, x, y, width, length, rotation):
        #upper left corner is the origin
        #x,y are index of the array
        #x:column index y:row index
        super().__init__(name)
        self._position = Vector([x, y, 0])
        self._width = width
        self._length = length
        self._rotation = rotation
        self._needs_refresh = True

    def _refresh(self):
        # get the positions of the centers of the head and tail circles
        direction = Vector([cos(self._rotation), sin(self._rotation), 0])
        distance = (self._length - self._width)/2
        displacement = distance*direction

        self._head_center = self._position + displacement
        self._tail_center = self._position - displacement

        # get the positions of the corners of the bacilli box
        side = Vector([-sin(self._rotation), cos(self._rotation), 0])
        radius = self._width/2

        self._head_right = self._head_center + radius*side
        self._head_left = self._head_center - radius*side
        self._tail_right = self._tail_center + radius*side
        self._tail_left = self._tail_center - radius*side

        # compute the region of interest
        self._region = Rectangle(
            floor(min(self._head_center.x, self._tail_center.x) - radius), #left
            floor(min(self._head_center.y, self._tail_center.y) - radius), #top
            ceil(max(self._head_center.x, self._tail_center.x) + radius) + 1, #right
            ceil(max(self._head_center.y, self._tail_center.y) + radius) + 1) #bottom

        self._needs_refresh = False

    def draw(self, image, is_cell, simulation_config):
        """Draws the cell by adding the given value to the image."""
        if self._needs_refresh:
            self._refresh()
        
        #Diffraction pattern currently only applies to graySynthetic image
        image_type = simulation_config["image.type"]
        background_color = simulation_config["background.color"]
        cell_color = simulation_config["cell.color"]
        
        top = self._region.top 
        bottom = self._region.bottom 
        left = self._region.left 
        right = self._region.right 
        width = right - left
        height = bottom - top
        mask = np.zeros((height, width), dtype=np.bool)
        
        body_mask = polygon(
            r=(self._head_left.y - top,
               self._head_right.y - top,
               self._tail_right.y - top,
               self._tail_left.y - top),
            c=(self._head_left.x - left,
               self._head_right.x - left,
               self._tail_right.x - left,
               self._tail_left.x - left),
            shape=mask.shape)
        
        body_mask_up = polygon(
            r=(self._head_left.y - self._region.top,
               ceil((self._head_right.y + self._head_left.y) / 2) - self._region.top,
               ceil((self._tail_right.y + self._tail_left.y) / 2) - self._region.top,
               self._tail_left.y - self._region.top),
            c=(self._head_left.x - self._region.left,
               ceil((self._head_right.x + self._head_left.x) / 2) - self._region.left,
               ceil((self._tail_right.x + self._tail_left.x) / 2) - self._region.left,
               self._tail_left.x - self._region.left),
            shape=mask.shape)
        
        body_mask_middle = polygon(
            r=(ceil((self._head_right.y + self._head_left.y * 2) / 3) - self._region.top,
               ceil((self._head_right.y * 2 + self._head_left.y) / 3) - self._region.top,
               ceil((self._tail_right.y * 2 + self._tail_left.y) / 3) - self._region.top,
               ceil((self._tail_right.y + self._tail_left.y * 2) / 3) - self._region.top),
            c=(ceil((self._head_right.x + self._head_left.x * 2) / 3) - self._region.left,
               ceil((self._head_right.x * 2 + self._head_left.x) / 3) - self._region.left,
               ceil((self._tail_right.x * 2 + self._tail_left.x) / 3) - self._region.left,
               ceil((self._tail_right.x + self._tail_left.x * 2) / 3) - self._region.left),
            shape=mask.shape)
        
        head_mask = circle(
            x=self._head_center.x - left,
            y=self._head_center.y - top,
            radius=self._width / 2,
            shape=mask.shape)

        tail_mask = circle(
            x=self._tail_center.x - left,
            y=self._tail_center.y - top,
            radius=self._width / 2,
            shape=mask.shape)
        #phaseContrast unchanged
        if image_type == "phaseContrast":
            if not is_cell:
                mask[body_mask] = True
                mask[head_mask] = True
                mask[tail_mask] = True

                image[self._region.top:self._region.bottom,
                self._region.left:self._region.right][mask] = 0.39  # 0.39*255=100

            else:
                mask = np.zeros((height, width), dtype=np.bool)
                mask[body_mask] = True
                image[self._region.top:self._region.bottom,
                self._region.left:self._region.right][mask] = 0.25  # 0.25*255=65

                mask = np.zeros((height, width), dtype=np.bool)
                mask[head_mask] = True
                image[self._region.top:self._region.bottom,
                self._region.left:self._region.right][mask] = 0.25

                mask = np.zeros((height, width), dtype=np.bool)
                mask[tail_mask] = True
                image[self._region.top:self._region.bottom,
                self._region.left:self._region.right][mask] = 0.25

                mask = np.zeros((height, width), dtype=np.bool)
                mask[body_mask_up] = True
                image[self._region.top:self._region.bottom,
                self._region.left:self._region.right][mask] = 0.63  # 0.63*255=160

                mask = np.zeros((height, width), dtype=np.bool)
                mask[body_mask_middle] = True
                image[self._region.top:self._region.bottom,
                self._region.left:self._region.right][mask] = 0.39  # 0.39*255=100

        elif image_type == "graySynthetic":
            mask[body_mask] = True
            mask[head_mask] = True
            mask[tail_mask] = True
            
            gaussian_filter_truncate = 4
            gaussian_filter_sigma = simulation_config["light.diffraction.sigma"]
            diffraction_strength = simulation_config["light.diffraction.strength"]
            #in order to use optimze funtion
            extension = max(floor(gaussian_filter_truncate * gaussian_filter_sigma - 0.5),0)
            
            diffraction_mask = mask.astype(float)
            diffraction_mask[mask] = diffraction_strength
            diffraction_mask = np.pad(diffraction_mask, extension, mode="constant")
            diffraction_mask = gaussian_filter(diffraction_mask, gaussian_filter_sigma, truncate = gaussian_filter_truncate)
            
            diff_top = top - extension
            diff_left = left - extension
            diff_bottom = bottom + extension
            diff_right = right + extension
            
            if is_cell:  
                image[diff_top:diff_bottom, diff_left:diff_right] += diffraction_mask
                image[top:bottom, left:right][mask] = cell_color 
            else:
                image[diff_top:diff_bottom, diff_left:diff_right] -= diffraction_mask
                image[top:bottom, left:right][mask] = background_color
                
        elif image_type == "binary":
            mask[body_mask] = True
            mask[head_mask] = True
            mask[tail_mask] = True
            if is_cell:
                image[self._region.top:self._region.bottom,
                      self._region.left:self._region.right][mask] += 1.0
            else:
                image[self._region.top:self._region.bottom,
                      self._region.left:self._region.right][mask] += -1.0





    def drawoutline(self, image, color):
        """Draws the outline of the cell over a color image."""
        if self._needs_refresh:
            self._refresh()

        draw_line(image, int(self._tail_left.x), int(self._tail_left.y),
                         int(self._head_left.x), int(self._head_left.y), color)
        draw_line(image, int(self._tail_right.x), int(self._tail_right.y),
                         int(self._head_right.x), int(self._head_right.y), color)

        r0 = self._head_right - self._head_center
        r1 = self._head_left - self._head_center
        t1 = atan2(r0.y, r0.x)
        t0 = atan2(r1.y, r1.x)
        draw_arc(image, self._head_center.x, self._head_center.y,
                        self._width/2, t0, t1, color)

        r0 = self._tail_right - self._tail_center
        r1 = self._tail_left - self._tail_center
        t0 = atan2(r0.y, r0.x)
        t1 = atan2(r1.y, r1.x)
        draw_arc(image, self._tail_center.x, self._tail_center.y,
                        self._width/2, t0, t1, color)

    def split(self, alpha):
        """Splits a cell into two cells with a ratio determined by alpha."""
        if self._needs_refresh:
            self._refresh()

        direction = Vector([cos(self._rotation), sin(self._rotation), 0])
        unit = self._length*direction

        front = self._position + unit/2
        back = self._position - unit/2
        center = self._position + (0.5 - alpha)*unit

        position1 = (front + center)/2
        position2 = (center + back)/2

        cell1 = Bacilli(
            self._name + '0',
            position1.x, position1.y,
            self._width, self._length*alpha,
            self._rotation)

        cell2 = Bacilli(
            self._name + '1',
            position2.x, position2.y,
            self._width, self._length*(1 - alpha),
            self._rotation)

        return cell1, cell2

    def combine(self, cell):
        """Combines this cell with another cell."""
        if self._needs_refresh:
            self._refresh()

        if cell._needs_refresh:
            cell._refresh()

        separation = self._position - cell._position
        direction = separation/sqrt(separation@separation)

        # get combined front
        direction1 = Vector([cos(self._rotation), sin(self._rotation), 0])
        distance1 = self._length - self._width
        if direction1@direction >= 0:
            head1 = self._position + distance1*direction1/2
        else:
            head1 = self._position - distance1*direction1/2
        extent1 = head1 + self._width*direction/2
        front = self._position + ((extent1 - self._position)@direction)*direction

        # get combined back
        direction2 = Vector([cos(cell._rotation), sin(cell._rotation), 0])
        distance2 = cell._length - cell._width
        if direction2@direction >= 0:
            tail2 = cell._position - distance2*direction2/2
        else:
            tail2 = cell._position + distance2*direction2/2
        extent2 = tail2 - cell._width*direction/2
        back = cell._position + ((extent2 - cell._position)@direction)*direction

        # create new cell
        position = (front + back)/2
        rotation = atan2(direction.y, direction.x)
        width = (self._width + cell._width)/2
        length = sqrt((front - back)@(front - back))

        return Bacilli(
            self._name[:-1],
            position.x, position.y,
            width, length,
            rotation)

    def __repr__(self):
        return (f'Bacilli('
                f'name="{self._name}", '
                f'x={self._position.x}, y={self._position.y}, '
                f'width={self._width}, length={self._length}, '
                f'rotation={self._rotation})')

    @property
    def region(self):
        if self._needs_refresh:
            self._refresh()
        return self._region

    @property
    def position(self):
        return self._position.copy()

    @property
    def x(self):
        return self._position.x

    @x.setter
    def x(self, value):
        if value != self._position.x:
            self._position.x = value
            self._needs_refresh = True

    @property
    def y(self):
        return self._position.y

    @y.setter
    def y(self, value):
        if value != self._position.y:
            self._position.y = value
            self._needs_refresh = True

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, value):
        if value != self._width:
            self._width = value
            self._needs_refresh = True

    @property
    def length(self):
        return self._length

    @length.setter
    def length(self, value):
        if value != self._length:
            self._length = value
            self._needs_refresh = True

    @property
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self, value):
        if value != self._rotation:
            self._rotation = value
            self._needs_refresh = True
