# -*- coding: utf-8 -*- 
'''
    Boblight for XBMC
    Copyright (C) 2012 Team XBMC

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

"""

cheat sheet

c_void_p(self.libboblight.boblight_init())
self.libboblight.boblight_destroy(boblight)
c_int(self.libboblight.boblight_connect(boblight, const char* address, int port, int usectimeout))
c_int(self.libboblight.boblight_setpriority(boblight, int priority))
c_char_p(self.libboblight.boblight_geterror(boblight))
c_int(self.libboblight.boblight_getnrlights(boblight))
c_char_p(self.libboblight.boblight_getlightname(boblight, int lightnr))
c_int(self.libboblight.boblight_getnroptions(boblight))
c_char_p(self.libboblight.boblight_getoptiondescriptboblight, int option))
c_int(self.libboblight.boblight_setoption(boblight, int lightnr, const char* option))
c_int(self.libboblight.boblight_getoption(boblight, int lightnr, const char* option, const char** output))
self.libboblight.boblight_setscanrange(boblight, int width, int height)
c_int(self.libboblight.boblight_addpixel(boblight, int lightnr, int* rgb))
self.libboblight.boblight_addpixelxy(boblight, int x, int y, int* rgb)
c_int(self.libboblight.boblight_sendrgb(boblight, int sync, int* outputused))
c_int(self.libboblight.boblight_ping(boblight, int* outputused))

"""
import sys
import os
import time
import xbmc
from boblightada import BoblightAda

try:
  from ctypes import *
  HAVE_CTYPES = True
except:
  HAVE_CTYPES = False

class Boblight():
  def __init__( self, *args, **kwargs ):
    self.current_priority = -1
    self.boblightada      = None
    self.connected        = False
    self.boblightLoaded   = False

  def bob_loadLibBoblight(self,libname,platform):
    ret = 0
    try:
      self.boblightada = BoblightAda()
      self.boblightLoaded = True
    except:
      ret = 1
    return ret
  
  def bob_set_priority(self,priority):   
    ret = True
    if self.boblightLoaded and self.connected:
      if priority != self.current_priority:
        if (priority == 255):
          self.boblightada.static_color(self.boblightada.blank_color())
          self.boblightada.stop()
        self.current_priority = priority
    return ret
    
  def bob_setscanrange(self, width, height):
    ret = False
    if self.boblightLoaded and self.connected:
      self.boblightada.set_scan_range(width, height)
      ret = True
    return ret
    
  def bob_setimage(self, image, width, height):
    ret = False
    if self.boblightLoaded and self.connected:
      self.boblightada.set_image(image, width, height)
      self.boblightada.flush_image()
      ret = True
    return ret
  
  def bob_addpixelxy(self,x,y,rgb):
    if self.boblightLoaded and self.connected:
      self.boblightada.update_image(x, y, rgb)
  
  def bob_addpixel(self,rgb):
    return self.static_color(rgb)
  
  def bob_sendrgb(self):
    ret = False
    if self.boblightLoaded and self.connected:
      #self.boblightada.flush_image()
      self.boblightada.flush_image_async()
      ret = True
    return ret
    
  def bob_setoption(self,option):
    ret = False
    if self.boblightLoaded and self.connected:
      ret = True
    return ret
    
  def bob_getnrlights(self):
    ret = 0
    if self.boblightLoaded and self.connected:
      ret = len(self.boblightada.leds)
    return ret
  
  def bob_getlightname(self,nr):
    ret = "Adalight"
    return ret
  
  def bob_connect(self,hostip, hostport):    
    if self.boblightLoaded:
      try:
	    self.boblightada.connect()
	    self.connected = True
      except:
        self.connected = False
    return self.connected
    
  def bob_set_static_color(self,rgb):
    res = False
    if self.boblightLoaded and self.connected:
      self.boblightada.static_color(rgb)
      res = True
    return res  
  
  def bob_destroy(self):
    if self.boblightLoaded:
      self.boblightada.close()
      self.boblightLoaded = False
  
  def bob_geterror(self):
    ret = ""
    return ret
  
  def bob_ping(self):
    ret = False
    if self.boblightLoaded and self.connected:
      self.boblightada.keepalive()
      ret = True
    return ret
