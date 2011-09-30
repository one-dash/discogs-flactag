#!/usr/bin/env python
# -*- coding: utf_8 -*-

class Medium:
        """
        Describes a single(or a group of unique) medium(s)
        """
        def __init__(self, name, qty = 1, diameter = '', duration = '', \
          reissue = False):
            # quantity of the mediums:
            self.qty = qty
            # name of the medium: CD, CDr, Vinyl, so on...
            self.name = name
            # diameter of the medium: 7", 3", 12", so on...
            self.diameter = diameter
            # duration of the medium: LP, EP, Single, so on...
            self.duration = duration
            # if this is a reissue
            self.reissue = reissue

