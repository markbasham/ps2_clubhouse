#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import cgi
import datetime
import urllib2
import webapp2
import json
import sys
from operator import itemgetter
from datetime import datetime

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import urlfetch

urlfetch.set_default_fetch_deadline(45)

import jinja2
import os

MEMBERS_PER_REQUEST = 100

CORE_ID = '37509528949522142'
PUGZ_ID = '37511770385198092'
PUGZ_ALIAS = 'PUGZ'
OUTFIT_URL = 'http://census.soe.com/s:mb/get/ps2-beta/outfit/?alias=%s'
MEMBER_URL = 'http://census.soe.com/get/ps2-beta/outfit_member/%i?c:limit=%i&c:start=%i&c:resolve=character(name,type.faction,experience,profile.active_name.en,stats_weekly.kills.faction,stats_weekly.facility_capture_count,stats_weekly.facility_defended_count,stats_weekly.play_time.class,stats_daily.facility_capture_count,stats_daily.facility_defended_count,stats_daily.play_time.class,stats_daily.kills.faction,stats_monthly.facility_capture_count,stats_monthly.facility_defended_count,stats_monthly.play_time.class,stats_monthly.kills.faction,,stats.facility_capture_count,stats.facility_defended_count,stats.play_time.class,stats.kills.faction,times.last_login),online_status'

DEFAULT_SORT = 'joined'
SORT_TYPE = {
	'joined':[(itemgetter('member_since'),False),
		(itemgetter('online_status'),False)],
	'battle_rank':[(itemgetter('rank_int'),True),
		(itemgetter('online_status'),False)],
	'outfit_rank':[(itemgetter('rank_ordinal'),False),
		(itemgetter('online_status'),False)],
	'last_login':[(itemgetter('last_login'),True),
		(itemgetter('online_status'),False)]}

CHECK = ['experience','stats_weekly']

CLASSES = {
	'Infiltrator':'61',
	'Heavy Assault':'1',
	'Light Assault':'2',
	'Engineer':'60',
	'Combat Medic':'3',
	'MAX':'69'
	}
	
CLASSES_LOWER = {
	'infiltrator':'61',
	'heavy_assault':'1',
	'light_assault':'2',
	'engineer':'60',
	'combat_medic':'3',
	'MAX':'69'
	}
	
BR_OFFSETS = {
	'tr':1727,
	'nc':1627,
	'vs':1827
	}

ENEMY1 = {
	'tr':'nc',
	'nc':'vs',
	'vs':'tr'
	}

ENEMY2 = {
	'tr':'vs',
	'nc':'tr',
	'vs':'nc'
	}
	
STAT_TYPES = ['stats_daily','stats_weekly','stats_monthly','stats']

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

def get_playtime_class_icon_id(playtime):
	max = 0
	id = 0
	clazzes = []
	for clazz in playtime['class'].keys():
		value = int(playtime['class'][clazz]['value'])
		clazzes.append((value,CLASSES_LOWER[clazz]))
	clazzes.sort(reverse=True)
	return clazzes
	
class Greeting(db.Model):
	"""Models an individual Guestbook entry with an author, content, and date."""
	author = db.StringProperty()
	content = db.StringProperty(multiline=True)
	date = db.DateTimeProperty(auto_now_add=True)

def guestbook_key(guestbook_name=None):
	"""Constructs a Datastore key for a Guestbook entity with guestbook_name."""
	return db.Key.from_path('Guestbook', guestbook_name or 'default_guestbook')

	
class MainHandler(webapp2.RequestHandler):
    def get(self):
		outfit=self.request.get('outfit')
		if (outfit == ""):
			outfit = PUGZ_ALIAS
			
		sort=self.request.get('sort')
		if (sort == ""):
			sort = DEFAULT_SORT

		#if users.get_current_user():
		#	url = users.create_logout_url(self.request.uri)
		#	url_linktext = 'Logout'
		#else:
		#	url = users.create_login_url(self.request.uri)
		#	url_linktext = 'Login'

		# get values from URL
		try :
			url = OUTFIT_URL%(outfit)
			fetch = urlfetch.fetch(url).content
			data = json.loads(fetch)['outfit_list'][0]
			
			
		except Exception as e :
			self.response.out.write("Failed to get info from the SOE server, please try again later<br><br>")
			self.response.out.write(e)
			return		
		
		
		totalStats = {'online':0}
		for stat in STAT_TYPES:
			totalStats[stat] = {	
				'tr':{'kills':0,'caps':0},
				'vs':{'kills':0,'caps':0},
				'nc':{'kills':0,'caps':0},
				'defends':0} 
		
		members = []
		ids = []
		
		for i in range(0,int(data['member_count']),MEMBERS_PER_REQUEST):
			
			# get the next section of data
			try :
				url = MEMBER_URL%(int(data['id']),MEMBERS_PER_REQUEST,i)
				fetch = urlfetch.fetch(url).content
				member_list = json.loads(fetch)['outfit_member_list']
			except Exception as e :
				self.response.out.write("Failed to get info from the SOE server, please try again later<br><br>")
				self.response.out.write(e)
				return	
				
			
			for member in member_list:
				try :
				    if not member['character_id'] in ids :
						ids.append(member['character_id'])
					
						member['rank_int'] = int(member['character']['experience'][0]['rank'])
						member['last_login'] = int(member['character']['times']['last_login'])
						member['last_login_string'] = datetime.fromtimestamp(int(member['character']['times']['last_login'])).__str__()
						if (member['online_status'] == '0'):
							member['online_status'] = '1'
							member['online_status_colour'] = '#FF0000'
						if (member['online_status'] == '9'):
							member['online_status'] = '0'
							member['online_status_colour'] = '#00FF00'
							totalStats['online']+=1
						
						for stat in STAT_TYPES:
							totalStats[stat]['tr']['kills'] += int(member['character'][stat]['kills']['faction']['tr'])
							totalStats[stat]['vs']['kills'] += int(member['character'][stat]['kills']['faction']['vs'])
							totalStats[stat]['nc']['kills'] += int(member['character'][stat]['kills']['faction']['nc'])
							totalStats[stat]['tr']['caps'] += int(member['character'][stat]['facility_capture_count']['faction']['tr'])
							totalStats[stat]['vs']['caps'] += int(member['character'][stat]['facility_capture_count']['faction']['vs'])
							totalStats[stat]['nc']['caps'] += int(member['character'][stat]['facility_capture_count']['faction']['nc'])
							totalStats[stat]['defends'] += int(member['character'][stat]['facility_defended_count']['value'])
						
						member['daily_class'] = get_playtime_class_icon_id(member['character']['stats_daily']['play_time'])
						member['weekly_class'] = get_playtime_class_icon_id(member['character']['stats_weekly']['play_time'])
						member['monthly_class'] = get_playtime_class_icon_id(member['character']['stats_monthly']['play_time'])
						member['alltime_class'] = get_playtime_class_icon_id(member['character']['stats']['play_time'])
						
						members.append(member)
				except Exception as inst:
					#self.response.out.write(inst)
					pass
		
		faction = members[0]['character']['type']['faction']
		
		for sorter in SORT_TYPE[sort]:
			members.sort(key=sorter[0], reverse=sorter[1])
			
		template_values = {
			'total_members': int(data['member_count']),
			'name': data['name'],
			'alias': data['alias'],
			'members': members,
			'classes': CLASSES,
			'offsets': BR_OFFSETS,
			'totalStats' : totalStats,
			'faction' : faction,
			'enemy1' : ENEMY1[faction],
			'enemy2' : ENEMY2[faction],
		}

		template = jinja_environment.get_template('index.html')
		self.response.out.write(template.render(template_values))

class Test(webapp2.RequestHandler):
    def get(self):
		self.response.out.write("test")

		
class Guestbook(webapp2.RequestHandler):
    def post(self):
		# We set the same parent key on the 'Greeting' to ensure each greeting is in
		# the same entity group. Queries across the single entity group will be
		# consistent. However, the write rate to a single entity group should
		# be limited to ~1/second.
		guestbook_name = self.request.get('guestbook_name')
		greeting = Greeting(parent=guestbook_key(guestbook_name))

		if users.get_current_user():
			greeting.author = users.get_current_user().nickname()

		greeting.content = self.request.get('content')
		greeting.put()
		self.redirect('/?' + urllib.urlencode({'guestbook_name': guestbook_name}))

			
app = webapp2.WSGIApplication([('/', MainHandler),('/sign', Guestbook),('/test', Test)], debug=True)
