#!/usr/bin/python
# -*- coding: utf-8 -*-

import requests
import simplejson as json
import base64
import os.path
import xbmcgui
import xbmc
import time

class KsysUser:
	def __init__(self, user, password):
		self.user     = user
		self.password = password
		self.ktvurl   = "https://testing-wstv.k-sys.ch/"

		self.accessToken 	= ""
		self.refreshTOken 	= ""
		self.expireToken 	= 0

		self.loadJwt()

	def loadJwt(self):
		path_jwt = xbmc.translatePath("special://userdata/addon_data/pvr.ksys/.jwt")
		if os.path.isfile(path_jwt):
			file = open(xbmc.translatePath("special://userdata/addon_data/pvr.ksys/.jwt"), "r")
			jwt_tmp = file.read();
			file.close()
			jwt = json.loads(jwt_tmp)
			self.accessToken 	= jwt['accessToken']
			self.refreshToken 	= jwt['refreshToken']
			self.expireToken 	= jwt['expireAccessTokenDate']

	def saveJwt(self):
		file = open(xbmc.translatePath("special://userdata/addon_data/pvr.ksys/.jwt"), "w")
		file.write(json.dumps({
			"accessToken":    			self.accessToken,
			"expireAccessTokenDate": 	self.expireToken,
			"refreshToken":      		self.refreshToken
		}))
		file.close()

	def getAccessToken(self):
		if self.accessToken != "" and self.expireToken > time.time():
			return self.accessToken
		else:
			#ON doit le générer
			return ""

	def getCredentials(self):
		return json.dumps({
			"login":    self.user,
			"password": self.password,
			"mac":      self.mac
		})

	def getEPGbyCat(self, cat, subcat, offset, limit):
		req = requests.get("%stv/guide/thematic/%s/%s/%d-%d/" % (self.ktvurl, cat, subcat, offset, limit))
		return json.loads(req.text)['content']

	def getEPG(self, channels, timestamp, duration):
		req = requests.get("%stv/guide/%s/%s/%s/" % (self.ktvurl,  channels, timestamp, duration))
		return json.loads(req.text)['content']

	def getCategory(self):
		req = requests.get("%stv/guide/thematic/cats/" % (self.ktvurl))
		return json.loads(req.text)['content']

	def getChannelsReplay(self):
		req = requests.get("%stv/catchup/channels/" % (self.ktvurl))
		return json.loads(req.text)['content']

	def getURLCatchup(self, channel, timestamp, duration):
		return "%stv/catchup/%s/%s/%s/" % (self.ktvurl, channel, timestamp, duration)

	"""
	Télécharge et sauvegarde le M3U8 du catchup, puis retourne le chemin du M3U téléchargé

	:param url: url du catchup
	:type url: str
	"""
	def getTempM3UCatchup(self, url):
		xbmc.log("AZERTY : " + url, xbmc.LOGDEBUG)
		req = requests.get(
			"%s" % (url),
			headers={"Authorization": "Bearer " + self.getAccessToken()}
		)
		path = xbmc.translatePath("special://temp/tmp_replay_ksys.m3u8")
		file = open(path, "w")
		file.write(req.text)
		file.close
		return path

	def getVideoByTitle(self, title, offset, limit):
		req = requests.get("%s/tv/guide/thematic/program/%s/%d-%d/" % (self.ktvurl, base64.b64encode(title), offset, limit))
		return json.loads(req.text)['content']
