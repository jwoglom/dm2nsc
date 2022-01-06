from secret import USERNAME, PASSWORD, NS_URL, NS_SECRET
import requests, json, arrow, hashlib, urllib, datetime
import cloudscraper


DBM_HOST = 'https://analytics.diabetes-m.com'

# this is the enteredBy field saved to Nightscout
NS_AUTHOR = "Diabetes-M (dm2nsc)"


def get_login():
	sess = cloudscraper.create_scraper(
		browser={
			'browser': 'chrome',
			'platform': 'windows',
			'desktop': True
		}
	)
	index = sess.get(DBM_HOST + '/login')

	return sess.post(DBM_HOST + '/api/v1/user/authentication/login', json={
		'username': USERNAME,
		'password': PASSWORD,
		'device': ''
	}, headers={
		'origin': DBM_HOST,
		'referer': DBM_HOST + '/login'
	}, cookies=index.cookies), sess


def get_entries(login, sess):
	auth_code = login.json()['token']
	print("Loading entries...")
	entries = sess.post(DBM_HOST + '/api/v1/diary/entries/list', 
		cookies=login.cookies, 
		headers={
			'origin': DBM_HOST,
			'authorization': 'Bearer '+auth_code
		}, json={
			'fromDate': -1,
			'toDate': -1,
			'page_count': 90000,
			'page_start_entry_time': 0
		})
	return entries.json()


def to_mgdl(mmol):
	return round(mmol*18)

def convert_nightscout(entries, start_time=None):
	out = []

	for entry in entries:
		bolus = entry["carb_bolus"] + entry["correction_bolus"]
		time = arrow.get(int(entry["entry_time"])/1000).to(entry["timezone"])

		#Fill notes varable
		notes = entry["notes"]

		#save notes data to a variable used to skip uploads from nightscoute
		noteskip = entry["notes"]

		# Check if there is any data for basal, proteins or fats and if notes are empty
		if (entry["basal"]+ entry["proteins"]+ entry["fats"]) != 0 and len(notes)!=0:

			#Build the string of additional data to be pushed into notes field on nightscout if notes there are notes
			notes = "%s Basal: %s Proteins: %s Fats: %s" % (entry["notes"], entry["basal"], entry["proteins"], entry["fats"])

		# Check if there is any data for basal, proteins or fats and if notes are not empty
		if (entry["basal"]+ entry["proteins"]+ entry["fats"]) != 0 and len(notes) == 0:

			#Build the string of additional data to be pushed into notes field on nightscout of there  are no notes
			notes = "Basal: %s Proteins: %s Fats: %s" % (entry["basal"], entry["proteins"], entry["fats"])

		if start_time and start_time >= time:

			continue

		author = NS_AUTHOR

		# if from nightscout, skip
		if noteskip == "[Nightscout]":
			continue

		# You can do some custom processing here, if necessary

		dat = {
			"eventType": "Meal Bolus",
			"created_at": time.format(),
			"carbs": entry["carbs"],			
			"fats": entry["fats"],
			"proteins": entry["proteins"],
			"basal": entry["basal"],
			"insulin": bolus,
			"notes": notes,
			"enteredBy": author
		}


		if entry["glucose"]:
			bgEvent = {
				"eventType": "BG Check",
				"glucoseType": "Finger",
			}
			# entry["glucose"] is always in mmol/L, but entry["glucoseInCurrentUnit"] is either mmol/L or mg/dL depending on account settings
			# entry["us_units"] appears to always be false, even if your account is set to mg/dL, so it is ignored for now
			unit_mmol = (entry["glucoseInCurrentUnit"] == entry["glucose"])

			# for mmol/L units, if no carbs or bolus is present then we upload with mmol/L units
			# to nightscout, otherwise we use the converted mg/dL as normal.
			# this is due to a UI display issue with Nightscout (it will show mg/dL units always for
			# bg-only readings, but convert to the NS default unit otherwise)
			if unit_mmol and not (entry["carbs"] or bolus):
				bgEvent["units"] = "mg/dL"
				# convert mmol/L -> mg/dL
				bgEvent["glucose"] = to_mgdl(entry["glucose"])
			else:
				bgEvent["units"] = "mmol"
				# save the mmol/L value from DB-M
				bgEvent["glucose"] = entry["glucose"]

			dat.update(bgEvent)

		out.append(dat)

	return out

def upload_nightscout(ns_format):
	upload = requests.post(NS_URL + 'api/v1/treatments?api_secret=' + NS_SECRET, json=ns_format, headers={
		'Accept': 'application/json',
		'Content-Type': 'application/json',
		'api-secret': hashlib.sha1(NS_SECRET.encode()).hexdigest()
	})
	print("Nightscout upload status:", upload.status_code, upload.text)

def get_last_nightscout():
	last = requests.get(NS_URL + 'api/v1/treatments?count=1&find[enteredBy]='+urllib.parse.quote(NS_AUTHOR))
	if last.status_code == 200:
		js = last.json()
		if len(js) > 0:
			return arrow.get(js[0]['created_at']).datetime

def main():
	print("Logging in to Diabetes-M...", datetime.datetime.now())
	login, sess = get_login()
	if login.status_code == 200:
		entries = get_entries(login, sess)
	else:
		print("Error logging in to Diabetes-M: ",login.status_code, login.text)
		exit(0)

	print("Loaded", len(entries["logEntryList"]), "entries")

	# skip uploading entries past the last entry
	# uploaded to Nightscout by `NS_AUTHOR`
	ns_last = get_last_nightscout()

	ns_format = convert_nightscout(entries["logEntryList"], ns_last)

	print("Converted", len(ns_format), "entries to Nightscout format")
	print(ns_format)

	print("Uploading", len(ns_format), "entries to Nightscout...")
	upload_nightscout(ns_format)
