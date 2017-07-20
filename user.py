#!/usr/bin/python
# -*- coding: utf-8 -*-

import requests
import simplejson as json
import base64
import xbmcgui

class KsysUser:
	def __init__(self, user, password, mac="FF:FF:FF:00:00:03", token=""):
		self.user     = user
		self.password = password
		self.mac      = mac
		self.ktvurl   = "https://api-tv.k-sys.ch/"
		self.token    = token

	def getCredentials(self):
		return json.dumps({
			"login":    self.user,
			"password": self.password,
			"mac":      self.mac
		})

	def getToken(self):
		if self.token == "":
			req = requests.get("%sauth/%s/" % (self.ktvurl, self.mac))
			if self.checkRespToken(req) == False:
				req = requests.post(
					self.ktvurl+"auth/",
					data=self.getCredentials(),
					headers={"Content-type": "application/json"}
				)
				self.checkRespToken(req, True)

		return self.token

	def checkRespToken(self, req, showError=False):
		if req.headers['content-type'] == 'application/json':
			resp = json.loads(req.text)
			if 'content' in resp:
				if 'token' in resp['content']:
					self.token = resp['content']['token']
					return True
			elif 'message' in resp and showError == True:
				dialog = xbmcgui.Dialog()
				ok = dialog.ok('Authentification K-Sys', 'Erreur serveur d\'authentification : ' + resp['message'])
		elif showError == True:
			dialog = xbmcgui.Dialog()
			ok = dialog.ok('Authentification K-Sys', 'Erreur de communication avec le serveur d\'authentification !')

		return False

	def getChannels(self, location="CHE", group=0):
		req = requests.get(
			"%stv/map/%s/%d/" % (self.ktvurl, location, group),
			headers={"X-Authenticate": self.getToken()}
		)
		return json.loads(req.text)['content']

	def getEPGbyCat(self, cat, subcat, offset, limit, group=0):
		req = requests.get("%stv/guide/thematic/%s/%s/%d/%d-%d/" % (self.ktvurl, cat, subcat, group, offset, limit))
		return json.loads(req.text)['content']

	def getEPG(self, channels, timestamp, duration, location="CHE", group=1):
		req = requests.get("%stv/guide/%s/%d/%s/%s/%s/" % (self.ktvurl, location, group, channels, timestamp, duration))
		return json.loads(req.text)['content']

	def getCategory(self):
		req = requests.get("%stv/guide/thematic/cats/" % (self.ktvurl))
		return json.loads(req.text)['content']

	def getChannelsReplay(self):
		req = requests.get("%stv/catchup/channels/" % (self.ktvurl))
		return json.loads(req.text)['content']

	def getURLCatchup(self, channel, timestamp, duration):
		return "%stv/catchup/%s/%s/%s/%s/" % (self.ktvurl, channel, timestamp, self.getToken(), duration)

	def getVideoByTitle(self, title, offset, limit, group=0):
		req = requests.get("%s/tv/guide/thematic/program/%s/%d/%d-%d/" % (self.ktvurl, base64.b64encode(title), group, offset, limit))
		return json.loads(req.text)['content']