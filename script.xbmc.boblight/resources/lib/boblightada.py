# -*- coding: utf-8 -*- 
'''
    Boblight - Adalight - Python library

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
	
	https://pypi.python.org/pypi/pyserial
'''

import xbmc
import sys
import os
import subprocess
import time
import re
import json
import math
from threading import Thread

__cwd__        = sys.modules[ "__main__" ].__cwd__
__pyserial__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'pyserial-2.7' ) )
__conf__   = xbmc.translatePath( os.path.join( __cwd__, 'hyperion.config.json' ) )
sys.path.insert (0, __pyserial__)

import serial

class BoblightAda():
	def __init__( self, *args, **kwargs ):
		self.started = False
		self.refresh_thread = None
		self.flush_thread = None
		self.loadconf();
		self.create_buffer();
		self.set_permission = False
		self.scan_width = 0
		self.scan_height = 0
		self.scan_image = None
		self.adalight = None
		#self.count = 3
	
	def removeComments(self, txt):
		txt = re.sub(re.compile("/\*.*?\*/",re.DOTALL ) ,"" ,txt) # remove all occurance streamed comments (/*COMMENT */) from txt
		txt = re.sub(re.compile("//.*?\n" ) ,"" ,txt) # remove all occurance singleline comments (//COMMENT\n ) from txt
		return txt
	
	def loadconf(self):
		txt = None
		with open(__conf__) as f:
			txt = f.read()
		config  = json.loads(self.removeComments(txt))
		self.device = config["device"]["output"]
		self.rate = config["device"]["rate"]
		self.interval = config["color"]["smoothing"]["updateFrequency"] / 1000
		self.smoothing = 0 #0.15
		self.saturation_gain = config["color"]["transform"][0]["hsv"]["saturationGain"]
		self.value_gain = config["color"]["transform"][0]["hsv"]["valueGain"]
		self.colors = {
				"red"  : config["color"]["transform"][0]["red"],
				"green": config["color"]["transform"][0]["green"],
				"blue" : config["color"]["transform"][0]["blue"]
			}
		
		self.leds = []
		leds = config["leds"]
		last = -1
		for i in range(len(leds)):
			led = leds[i]
			current = led["index"]
			if (current > last):
				#xbmc.log(str(led))
				self.leds.append(led)
				last = current
			else:
				i = 0
				while (self.leds[i]["index"] < current):
					i += 1
				self.leds.insert(i, led)
	
	def connect(self):
		result = True
		try:
			self.adalight = serial.Serial(self.device, self.rate, timeout=1)
			retry = 0
			while (retry < 10 and (not self.adalight.isOpen())):
				retry += 1
				time.sleep(0.1)
			if (retry == 10):
				result = False
		except:
			if (not self.set_permission):
				p = subprocess.Popen("su", stdin=subprocess.PIPE)
				p.communicate("chmod 777 %s \nexit" % self.device)
				self.set_permission = True
				result = self.connect()
			else:
				result = False
		if (result):
			xbmc.log('connection succeeded')
		else:
			xbmc.log('connection failed')
		return result
	
	def keepalive(self):
		if ((self.adalight is None) or (not self.adalight.isOpen())):
			self.connect()
		else:
			self.write_buffer()
	
	def close(self):
		if ((self.adalight is not None) and (self.adalight.isOpen())):
			self.stop()
			self.adalight.close()
	
	def create_buffer(self):
		int1 = (len(self.leds)-1) >> 8
		int2 = (len(self.leds)-1) & 0xff
		buffer = ['\x41', '\x64', '\x61', chr(int1), chr(int2)] #Ada + led count + checksum
		buffer.append(chr(int1 ^ int2 ^ 0x55))
		for i in range(len(self.leds) * 3):
			buffer.append(chr(0))
		
		self.buffer_prefix_length = 6
		self.buffer = buffer
	
	def update_buffer(self, led_colors, is_static):
		#xbmc.log("colors %s" % str(len(led_colors)))
		for i in range(len(led_colors)):
			color = None
			if ((self.saturation_gain == 1) and (self.value_gain == 1)):
				color = led_colors[i]
			else:
				color = self.fix_hsv(led_colors[i])
			
			j = i * 3
			if ((self.smoothing != 0) and (not is_static)):
				self.buffer[self.buffer_prefix_length + j] = chr(self.fix_color(int(color[0] * (1 - self.smoothing) + ord(self.buffer[self.buffer_prefix_length + j]) * self.smoothing), self.colors["red"]))
				self.buffer[self.buffer_prefix_length + j + 1] = chr(self.fix_color(int(color[1] * (1 - self.smoothing) + ord(self.buffer[self.buffer_prefix_length + j + 1]) * self.smoothing), self.colors["green"]))
				self.buffer[self.buffer_prefix_length + j + 2] = chr(self.fix_color(int(color[2] * (1 - self.smoothing) + ord(self.buffer[self.buffer_prefix_length + j + 2]) * self.smoothing), self.colors["blue"]))
			else:
				self.buffer[self.buffer_prefix_length + j] = chr(self.fix_color(color[0], self.colors["red"]))
				self.buffer[self.buffer_prefix_length + j + 1] = chr(self.fix_color(color[1], self.colors["green"]))
				self.buffer[self.buffer_prefix_length + j + 2] = chr(self.fix_color(color[2], self.colors["blue"]))
		#xbmc.log(str(self.buffer))
	
	def fix_color(self, color_level, color_settings):
		if (color_settings["threshold"] > 0 and color_level <= color_settings["threshold"] * 255):
			return int(color_settings["blacklevel"] * 255)
		else:
			result = None
			if (color_settings["blacklevel"] > 0 or color_settings["whitelevel"] < 1):
				result = int(color_settings["blacklevel"] * 255 + color_level * (color_settings["whitelevel"] - color_settings["blacklevel"]))
			else:
				result = color_level
			
			if (color_settings["gamma"] != 1):
				result = int(255 * math.pow((float(result) / 255), (1 / color_settings["gamma"])))
			
			if (color_settings["threshold"] > 0 and result <= color_settings["threshold"] * 255):
				result = int(color_settings["blacklevel"] * 255)
			
			return result
	
	def fix_hsv(self, rgb):
		hsv = self.convert_to_hsv(rgb)
		if (self.saturation_gain != 1):
			hsv[1] = math.pow(hsv[1], (1 / self.saturation_gain))
		
		if (self.value_gain != 1):
			hsv[2] = math.pow(hsv[2], (1 / self.value_gain))
		
		return self.convert_to_rgb(hsv)
	
	def convert_to_hsv(self, rgb):
		r = float(rgb[0]) / 255
		g = float(rgb[1]) / 255
		b = float(rgb[2]) / 255
		
		v_min = min(r, g, b)
		v_max = max(r, g, b)
		delta = v_max - v_min
		
		v = v_max
		s = 0
		h = 0
		
		if (delta > 0):
			s = delta / v_max
			delta_r = (((v_max - r) / 6) + (delta / 2)) / delta
			delta_g = (((v_max - g) / 6) + (delta / 2)) / delta
			delta_b = (((v_max - b) / 6) + (delta / 2)) / delta
			
			if (r == v_max):
				h = delta_b - delta_g
			elif (g == v_max):
				h = 0.333 + delta_r - delta_b
			else: # (b == v_max)
				h = 0.666 + delta_g - delta_r
			
			if (h < 0):
				h += 1
			elif (h > 1):
				h -= 1
		
		return [h, s, v]
	
	def convert_to_rgb(self, hsv):
		h = hsv[0] * 6
		s = hsv[1]
		v = hsv[2]
		
		i = math.floor(h)
		f = h - i
		m = v * (1 - s)
		n = v * (1 - s * f)
		k = v * (1 - s * (1 - f))
		
		r = 0
		g = 0
		b = 0
		
		if (i == 0):
			r = v
			g = k
			b = m
		elif (i == 1):
			r = n
			g = v
			b = m
		elif (i == 2):
			r = m
			g = v
			b = k
		elif (i == 3):
			r = m
			g = n
			b = v
		elif (i == 4):
			r = k
			g = m
			b = v
		else: # (i == 5) or (i == 6)
			r = v
			g = m
			b = n
		
		return [int(r * 255), int(g * 255), int(b * 255)]
	
	def write_buffer(self):
		self.adalight.write(''.join(self.buffer))
	
	def static_color(self, color):
		led_colors = []
		for i in range(len(self.leds)):
			led_colors.append(color)
		self.update_buffer(led_colors, True)
		self.start()
	
	def get_color(self, r, g, b):
		color = [r, g, b]
		return color
	
	def blank_color(self):
		return self.get_color(0, 0, 0)
	
	def set_scan_range(self, width, height):
		if (self.scan_width != width or self.scan_height != height):
			self.scan_width = width
			self.scan_height = height
			self.scan_image = []
			for y in range(height):
				row = []
				for x in range(width):
					#row.append(self.blank_color())
					row.append(None)
				self.scan_image.append(row)
	
	def get_led_colors_for_image(self, image, width, height):
		led_colors = []
		for i in range(len(self.leds)):
			led = self.leds[i]
			color = None
			total_r = 0
			total_g = 0
			total_b = 0
			hscan_min = int(math.floor(led["hscan"]["minimum"] * width))
			hscan_max = int(math.ceil(led["hscan"]["maximum"] * width))
			vscan_min = int(math.floor(led["vscan"]["minimum"] * height))
			vscan_max = int(math.ceil(led["vscan"]["maximum"] * height))
			area = (hscan_max - hscan_min) * (vscan_max - vscan_min)
			if (area > 0):
				for x in range(hscan_max-hscan_min):
					for y in range(vscan_max-vscan_min):
						total_r += image[vscan_min + y][hscan_min + x][0]
						total_g += image[vscan_min + y][hscan_min + x][1]
						total_b += image[vscan_min + y][hscan_min + x][2]
				color = self.get_color(int(total_r/area), int(total_g/area), int(total_b/area))
			else:
				color = self.blank_color()
			led_colors.append(color)
		return led_colors
	
	def set_image(self, image, image_width, image_height):
		self.scan_image = image
		self.scan_width = image_width
		self.scan_height = image_height
	
	def flush_image(self):
		led_colors = self.get_led_colors_for_image(self.scan_image, self.scan_width, self.scan_height)
		#self.scan_image = None
		self.update_buffer(led_colors, False)
		self.write_buffer()
		#self.start()
		
		if (self.flush_thread is not None):
			self.flush_thread = None
	
	def flush_image_async(self):
		self.flush_thread = Thread(target=self.flush_image)
		self.flush_thread.start()
	
	def update_image(self, x, y, color):
		if (self.scan_image is not None):
			self.scan_image[y][x] = color
	
	def refresh(self):
		while (self.started):
			time.sleep(self.interval)
			self.write_buffer()
	
	def start(self):
		self.write_buffer()
		if (not self.started):
			self.started = True
			if (self.refresh_thread is None):
				self.refresh_thread = Thread(target=self.refresh)
				self.refresh_thread.start()
	
	def stop(self):
		self.started = False
		if (self.flush_thread is not None):
			self.flush_thread.join()
			self.flush_thread = None
		if (self.refresh_thread is not None):
			self.refresh_thread.join()
			self.refresh_thread = None
		xbmc.log("stopped")
	