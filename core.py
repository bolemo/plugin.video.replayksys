#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
from urllib import urlencode
from urlparse import parse_qsl
import os
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import requests
import random
import simplejson as json
from datetime import datetime, date, time
import time as modTime
from unidecode import unidecode

from user import KsysUser

class KsysCore:
	def __init__(self):
		self.Addon = xbmcaddon.Addon()
		# Get the plugin url in plugin:// notation.
		self._url = sys.argv[0]
		# Get the plugin handle as an integer number.
		self._handle = int(sys.argv[1])
		self.user = KsysUser()
		self.pluginPath = xbmc.translatePath(self.Addon.getAddonInfo('path')).decode('utf-8')

	"""
	Routeur qui appelle les autres fonctions en fonction de paramstring.

	:param paramstring: URL plugin encodée paramstring
	:type paramstring: str
	"""
	def router(self, paramstring):
		# Parse a URL-encoded paramstring to the dictionary of
		# {<parameter>: <value>} elements
		params = dict(parse_qsl(paramstring))
		# Check the parameters passed to the plugin
		if params:
			if params['action'] == 'listingChannels':
				self.list_channels()
			elif params['action'] == 'listingDayChannel':
				self.list_day_channel(params['channel'], params['channelNum'])
			elif params['action'] == 'listingVideoDayChannel':
				self.list_videos_by_channel(params['channel'], params['start'], params['duration'])
			elif params['action'] == 'listingCategories':
				self.list_categories()
			elif params['action'] == 'listingSubCategory':
				self.list_sub_categories(params['category'])
			elif params['action'] == 'listingVideoCategory':
				self.list_videos_by_category(params['category'], params['subcat'])
			elif params['action'] == 'searchVideo':
				self.search_video(params['title'])
			elif params['action'] == 'play':
				# Play a video from a provided URL.
				self.play_video(params['video'])
			elif params['action'] == 'settings':
				self.list_settings()
			else:
				# If the provided paramstring does not contain a supported action
				# we raise an exception. This helps to catch coding errors,
				# e.g. typos in action names.
				raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
		else:
			self.home()

	"""
	Créé une URL pour appeler le plugin récursivement, avec les arguments donnés

	:param kwargs: "argument=value" pairs
	:type kwargs: dict
	:return: URL d'apelle du plugin
	:rtype: str
	"""
	def get_url(self, **kwargs):
		return '{0}?{1}'.format(self._url, urlencode(kwargs))

	"""
	Gère l'affichage de la page d'accueil (Affiche le menu Paramètres / Replays par chaine / Replays par genre....)
	"""
	def home(self):
		xbmcplugin.addDirectoryItem(self._handle, self.get_url(action='settings'), xbmcgui.ListItem(label=self.Addon.getLocalizedString(31002)), True)
		xbmcplugin.addDirectoryItem(self._handle, self.get_url(action='listingChannels'), xbmcgui.ListItem(label=self.Addon.getLocalizedString(31000)), True)
		xbmcplugin.addDirectoryItem(self._handle, self.get_url(action='listingCategories'), xbmcgui.ListItem(label=self.Addon.getLocalizedString(31001)), True)
		xbmcplugin.addSortMethod(self._handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
		xbmcplugin.endOfDirectory(self._handle)

	"""
	Ouvre le menu des paramètres du plugin
	"""
	def list_settings(self):
		self.Addon.openSettings()

	"""
	Affiche toutes les catégories PRINCIPALES disponible en replay (donné par le KTV)
	"""
	def list_categories(self):
		# Get video categories
		categories = self.user.getCategory()
		# Iterate through categories
		for category in categories.keys():
			if len(categories[category]) > 1:
				list_item = xbmcgui.ListItem(label=category.title())
				list_item.setInfo('video', {'title': category, 'genre': category})
				url = self.get_url(action='listingSubCategory', category=category)
				xbmcplugin.addDirectoryItem(self._handle, url, list_item, True)
			else:
				subcat = categories[category][0]
				list_item = xbmcgui.ListItem(label=subcat)
				list_item.setInfo('video', {'title': subcat, 'genre': subcat})
				url = self.get_url(action='listingVideoCategory', category=category, subcat=unidecode(subcat))
				xbmcplugin.addDirectoryItem(self._handle, url, list_item, True)
		xbmcplugin.addSortMethod(self._handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
		xbmcplugin.endOfDirectory(self._handle)
	"""
	Affiche les sous-catégories d'une catégorie principale

	:param category: nom de la catégorie
	:type category: str
	"""
	def list_sub_categories(self, category):
		# Get video categories
		categories = self.user.getCategory()

		# Iterate through categories
		for subcat in categories[category]:
			list_item = xbmcgui.ListItem(label=subcat)
			list_item.setInfo('video', {'title': subcat, 'genre': subcat})
			url = self.get_url(action='listingVideoCategory', category=category, subcat=unidecode(subcat))
			xbmcplugin.addDirectoryItem(self._handle, url, list_item, True)

		xbmcplugin.addSortMethod(self._handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
		xbmcplugin.endOfDirectory(self._handle)

	"""
	Ajoute une marge de 10% sur la durée totale de la vidéo avec un minimum de 10 minutes pour essayer de combler le problème de l'EPG

	:param duration: durée de la vidéo
	:type category: int
	"""
	def add_margin_video(self, duration):
		duration /= 10
		offset = duration*0.1
		#On fixe l'offset à + 10min min
		if offset < 60:
			offset = 60
		return int(duration)

	"""
	Liste les vidéo associées à une catégorie et sous catégorie

	:param category: nom de la catégorie
	:type category: str
	:param subcat: nom de la sous-catégorie
	:type subcat: str
	"""
	def list_videos_by_category(self, category, subcat):
		# Get the list of videos in the category.
		videos = self.user.getEPGbyCat(category, subcat, 0, 999999)
		# Iterate through videos.
		for video in videos:
			is_dir = False
			url = ""

			if video['count'] > 1:
				is_dir = True
				title = video['titre'] + " [" + str(video['count']) + " programmes]"
				list_item = xbmcgui.ListItem(label=title)
				url = self.get_url(action='searchVideo', title=unidecode(video['titre']))

			else:
				# Create a list item with a text label and a thumbnail image.
				list_item = xbmcgui.ListItem(label=video['titre'])
				timeStart = modTime.mktime(modTime.strptime(video['dateCompleteDebut'], "%Y%m%d%H%M"))
				timeEnd = modTime.mktime(modTime.strptime(video['dateCompleteFin'], "%Y%m%d%H%M"))

				# Set additional info for the list item.
				list_item.setInfo('video', {'title': video['titre'], 'genre': video['categorieDetail'], 'mediatype': 'movie', 'dbid': video['id'], 'duration': (timeEnd-timeStart), 'plot': video['description'], 'plotoutline': video['description']})
				list_item.setProperty('IsPlayable', 'true')

				duration = timeEnd - timeStart
				duration = self.add_margin_video(duration)

				urlVideo = self.user.getURLCatchup(str(video['numChaine']), int(timeStart), duration)
				url = self.get_url(action='play', video=urlVideo)

			list_item.setArt({'thumb': video['vignette'], 'icon': video['vignette'], 'fanart': video['vignette']})
			xbmcplugin.addDirectoryItem(self._handle, url, list_item, is_dir)

		# Add a sort method for the virtual folder items (alphabetically, ignore articles)
		xbmcplugin.addSortMethod(self._handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
		# Finish creating a virtual folder.
		xbmcplugin.endOfDirectory(self._handle)

	"""
	Affiche toutes les vidéos qui correspondent au titre donné.
	Exemple affiche toutes les vidéos "Les experts" (du replay)

	:param title: titre de la vidéo
	:type title: str
	"""
	def search_video(self, title):
		# Get the list of videos in the category.
		videos = self.user.getVideoByTitle(title, 0, 50000)
		# Iterate through videos.
		for video in videos:
			# Create a list item with a text label and a thumbnail image.

			timeStart = modTime.strptime(video['dateCompleteDebut'], "%Y%m%d%H%M")
			timeEnd = modTime.strptime(video['dateCompleteFin'], "%Y%m%d%H%M")

			title = video['titre'] + "  [" + modTime.strftime("%d/%m/%Y %H:%M", modTime.strptime(video['dateCompleteDebut'], "%Y%m%d%H%M")) + "]"
			list_item = xbmcgui.ListItem(label=title)

			timeStart = modTime.mktime(timeStart)
			timeEnd = modTime.mktime(timeEnd)

			# Set additional info for the list item.
			list_item.setInfo('video', {'title': title, 'genre': video['categorieDetail'], 'mediatype': 'movie', 'dbid': video['id'], 'duration': (timeEnd-timeStart), 'plot': video['description'], 'plotoutline': video['description']})
			list_item.setProperty('IsPlayable', 'true')

			duration = timeEnd - timeStart
			duration = self.add_margin_video(duration)

			urlVideo = self.user.getURLCatchup(str(video['numChaine']), str(int(timeStart)), duration)
			url = self.get_url(action='play', video=urlVideo)

			list_item.setArt({'thumb': video['vignette'], 'icon': video['vignette'], 'fanart': video['vignette']})
			xbmcplugin.addDirectoryItem(self._handle, url, list_item, False)

		# Add a sort method for the virtual folder items (alphabetically, ignore articles)
		xbmcplugin.addSortMethod(self._handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
		# Finish creating a virtual folder.
		xbmcplugin.endOfDirectory(self._handle)

	"""
	Affiche toutes les chaines disponibles en replay
	"""
	def list_channels(self):
		channels = self.user.getChannelsReplay()
		fanartPath = os.path.join(self.pluginPath, 'fanart.jpg')
		for channel in channels:
			list_item = xbmcgui.ListItem(label=str(channel['num_ch']) + ". " + channel['name'])
			list_item.setInfo('video', {'title': channel['name']})
			pathLogo = os.path.join(self.pluginPath, 'resources', 'logos', str(channel['num_fr']) + '.png')
			list_item.setArt({'thumb':  pathLogo, 'icon': pathLogo, 'fanart': fanartPath})
			url = self.get_url(action='listingDayChannel', channelNum=channel['num_ch'], channel=unidecode(channel['name']))
			xbmcplugin.addDirectoryItem(self._handle, url, list_item, True)

		xbmcplugin.addSortMethod(self._handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
		xbmcplugin.endOfDirectory(self._handle)

	"""
	Affiche les jours disponibles pour la chaine donnée (Dans notre cas J-7)

	:param channelName: nom de la chaine
	:type channelName: str
	:param channelNum: numéro de la chaine (NUMÉRO SUISSE, celui qui correspond au replay)
	:type channelNum: str
	"""
	def list_day_channel(self, channelName, channelNum):
		midnight = date.today().strftime("%s")
		secondeInDay = 86400
		for day in range(0,7):
			midnightDay = int(midnight)-(day*secondeInDay)
			strDate = channelName + " le " + datetime.fromtimestamp(midnightDay).strftime('%d/%m/%Y')
			list_item = xbmcgui.ListItem(label=strDate)
			list_item.setInfo('video', {'title': strDate})
			url = self.get_url(action='listingVideoDayChannel', channel=channelNum, start=datetime.fromtimestamp(midnightDay).strftime('%Y%m%d%H%M'), duration=secondeInDay)
			xbmcplugin.addDirectoryItem(self._handle, url, list_item, True)

		xbmcplugin.addSortMethod(self._handle, xbmcplugin.SORT_METHOD_NONE)
		xbmcplugin.endOfDirectory(self._handle)

	"""
	Liste les vidéo associées à une chaine, une plage horaire (départ + durée)

	:param channel: numéro SUISSE de la chaine
	:type channel: str
	:param start: date (au format %Y%m%d%H%M) du début de la plage horaire
	:type start: str
	:param duration: durée en seconde de la plage horaire
	:type duration: str
	"""
	def list_videos_by_channel(self, channel, start, duration):
		# Get the list of videos in the category.
		listEPG = self.user.getEPG(channel, start, duration)

		for channel in listEPG:
			for videoKey in listEPG[channel].keys():
				# Create a list item with a text label and a thumbnail image.
				video = listEPG[channel][videoKey]
				timeStart = modTime.strptime(video['dateCompleteDebut'], "%Y%m%d%H%M")
				timeEnd = modTime.strptime(video['dateCompleteFin'], "%Y%m%d%H%M")

				title = "[" + modTime.strftime("%d/%m/%Y %H:%M", modTime.strptime(video['dateCompleteDebut'], "%Y%m%d%H%M")) + "] " + video['titre']
				list_item = xbmcgui.ListItem(label=title)

				timeStart = modTime.mktime(timeStart)
				timeEnd = modTime.mktime(timeEnd)

				# Set additional info for the list item.
				list_item.setInfo('video', {'title': title, 'genre': video['categorieDetail'], 'dateadded': modTime.strftime("%Y-%m-%d %H:%M:%s", modTime.strptime(video['dateCompleteDebut'], "%Y%m%d%H%M")) ,'mediatype': 'movie', 'dbid': video['id'], 'duration': (timeEnd-timeStart), 'plot': video['description'], 'plotoutline': video['description']})
				list_item.setProperty('IsPlayable', 'true')

				duration = timeEnd - timeStart
				duration = self.add_margin_video(duration)

				urlVideo = self.user.getURLCatchup(str(video['channel_id']), str(int(timeStart)), str(duration))
				url = self.get_url(action='play', video=urlVideo)

				list_item.setArt({'thumb': video['vignette'], 'icon': video['vignette'], 'fanart': video['vignette']})
				xbmcplugin.addDirectoryItem(self._handle, url, list_item, False)

		xbmcplugin.addSortMethod(self._handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
		# Finish creating a virtual folder.
		xbmcplugin.endOfDirectory(self._handle)

	"""
	Lance la lecture de la vidéo au chemin donné

	:param path: Chemin absolu de la vidéo
	:type path: str
	"""
	def play_video(self, path):
		# Create a playable item with a path to play.
		play_item = xbmcgui.ListItem(path=self.user.getTempM3UCatchup(path))
		# Pass the item to the Kodi player.
		xbmcplugin.setResolvedUrl(self._handle, True, listitem=play_item)
