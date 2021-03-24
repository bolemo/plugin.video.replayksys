#!/usr/bin/python
# -*- coding: utf-8 -*-

import requests
import simplejson as json
import base64
import os.path
import xbmcgui
import xbmc
import time
import uuid

class KsysUser:
	def __init__(self):
		self.KTV_URL   		= "http://api-tv.k-sys.ch/"
		self.KAUTH_URL      = "https://accounts.caps.services/"
	
		self.loadJwt()

	def loadJwt(self):
		path_jwt = xbmc.translatePath("special://userdata/addon_data/plugin.video.replayksys/.jwt")
		if os.path.isfile(path_jwt):
			file = open(xbmc.translatePath("special://userdata/addon_data/plugin.video.replayksys/.jwt"), "r")
			jwt_tmp = file.read();
			file.close()
			jwt = json.loads(jwt_tmp)
			self.accessToken 	= jwt['accessToken']
			self.refreshToken 	= jwt['refreshToken']
			self.expireToken 	= jwt['expireAccessTokenDate']
			self.pin 			= jwt['pin']
			self.playerId 		= jwt['playerId']
		else:
			self.accessToken 	= ""
			self.refreshToken 	= ""
			self.expireToken 	= 0
			self.pin 			= ""
			self.playerId 	    = ""

	def saveJwt(self):
		file = open(xbmc.translatePath("special://userdata/addon_data/plugin.video.replayksys/.jwt"), "w")
		file.write(json.dumps({
			"accessToken":    			self.accessToken,
			"expireAccessTokenDate": 	self.expireToken,
			"refreshToken":      		self.refreshToken,
			"pin":      				self.pin,
			"playerId":      			self.playerId
		}))
		file.close()

	def getPinCode(self):
		self.playerId = "kodi_plugin_replayksys_" + str(uuid.uuid4())
		req = requests.get("%sv1/player/%s/setup" % (self.KAUTH_URL, self.playerId))
		return json.loads(req.text)['pin']

	def getTokenByCode(self):
		dialog = xbmcgui.Dialog()
		ok = xbmcgui.Dialog().yesno( "K-Sys Replay", "Vous devez connecter votre compte K-Sys pour continuer.", "", "Voulez-vous le faire maintenant ?", "Non","Oui")
		self.pin = ""
		while ok:
			if self.pin == "":
				self.pin = self.getPinCode()
			dialog.ok("K-Sys Replay", "Rendez-vous sur https://reg.ktv.zone pour enregister ce lecteur %s avec votre compte. ENSUITE cliquez sur OK !" % (self.pin))
			req = requests.get(self.KAUTH_URL+"v1/player/%s/access_token" % (self.pin))
			if req.status_code == 200:
				jwt = json.loads(req.text)
				self.accessToken 	= jwt['access_token']
				self.refreshToken 	= jwt['refresh_token']
				self.expireToken 	= time.time() + jwt['expires_in']
				self.saveJwt()
				break;
			elif req.status_code == 419 :
				ok = dialog.yesno("K-Sys Replay", "Erreur le compte n'a pas été validé sur le site reg.ktv.zone" "", "Voulez-vous re-essayer ?", "Non","Oui")
		return self.accessToken

	def getJWTByPassword(self):
		dialog = xbmcgui.Dialog()
		username = ""
		password = ""
		while True:
			username = dialog.input("Identifiant K-Sys", username, type=xbmcgui.INPUT_ALPHANUM)
			password = dialog.input("Mot de passe K-Sys", "", type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.ALPHANUM_HIDE_INPUT)
			req = requests.post(
				self.KAUTH_URL+"v1/access_token",
				data="grant_type=password&client_id=ktv&username=" + username + "&password=" + password,
				headers={"Content-type": "application/x-www-form-urlencoded"}
			)
			if req.status_code == 200:
				jwt = json.loads(req.text)
				self.accessToken 	= jwt['access_token']
				self.refreshToken 	= jwt['refresh_token']
				self.expireToken 	= time.time() + jwt['expires_in']
				self.saveJwt()
				break
			elif (req.status_code == 400 and req.text == "nom d'utilisateur ou mot de passe incorrect"):
				ok = xbmcgui.Dialog().yesno( "K-Sys Replay", "Mot de passe incorrect !", "", "Voulez-vous réessayer ?", "Non","Oui")
				if not ok:
					break
			else:
				print(('Error : authentification return HTTP ' + req.status_code))
				json_req = json.loads(req.text)
				ok = xbmcgui.Dialog().ok("K-Sys Replay", "Erreur innatendue !", "", json_req["message"], "Non","Oui")
				break
		return self.accessToken

	def getJWTByRefreshToken(self):
		dialog = xbmcgui.Dialog()
		data = {'grant_type': 'refresh_token', 'client_id': 'ktv', 'refresh_token': self.refreshToken}
		req = requests.post(
			self.KAUTH_URL+"v1/access_token",
			data=data,
			headers={"Content-type": "application/x-www-form-urlencoded"}
		)
		if req.status_code == 200:
			jwt = json.loads(req.text)
			self.accessToken 	= jwt['access_token']
			self.refreshToken 	= jwt['refresh_token']
			self.expireToken 	= time.time() + jwt['expires_in']
			self.saveJwt()
		else:
			return self.getTokenByCode()

		return self.accessToken

	def getAccessToken(self):
		if self.accessToken != "" and self.expireToken > time.time():
			return self.accessToken
		elif self.refreshToken != "":
			return self.getJWTByRefreshToken()
		else:
			return self.getTokenByCode()

	def getCredentials(self):
		return json.dumps({
			"login":    self.user,
			"password": self.password,
			"mac":      self.mac
		})

	def getEPGbyCat(self, cat, subcat, offset, limit):
		req = requests.get("%stv/guide/thematic/%s/%s/%d-%d/" % (self.KTV_URL, cat, subcat, offset, limit))
		return json.loads(req.text)['content']

	def getEPG(self, channels, timestamp, duration):
		req = requests.get("%stv/guide/%s/%s/%s/" % (self.KTV_URL,  channels, timestamp, duration))
		return json.loads(req.text)['content']

	def getCategory(self):
		req = requests.get("%stv/guide/thematic/cats/" % (self.KTV_URL))
		return json.loads(req.text)['content']

	def getChannelsReplay(self):
		req = requests.get("%stv/catchup/channels/" % (self.KTV_URL))
		return json.loads(req.text)['content']

	def getURLCatchup(self, channel, timestamp, duration):
		return "%stv/catchup/%s/%s/%s/" % (self.KTV_URL, channel, timestamp, duration)

	"""
	Télécharge et sauvegarde le M3U8 du catchup, puis retourne le chemin du M3U téléchargé

	:param url: url du catchup
	:type url: str
	"""
	def getTempM3UCatchup(self, url):
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
		req = requests.get("%s/tv/guide/thematic/program/%s/%d-%d/" % (self.KTV_URL, base64.b64encode(title), offset, limit))
		return json.loads(req.text)['content']
