import requests, json, arrow
from secret import USERNAME, PASSWORD, NS_URL
NS_AUTHOR = "Diabetes-M (dm2nsc)"


def get_login():
	return requests.post('https://analytics.diabetes-m.com/api/v1/user/authentication/login', json={
		'username': USERNAME,
		'password': PASSWORD,
		'device': ''
	}, headers={
		'origin': 'https://analytics.diabetes-m.com'
	})


def get_entries(login):
	auth_code = login.json()['token']
	print("Loading entries...")
	entries = requests.post('https://analytics.diabetes-m.com/api/v1/diary/entries/list', 
		cookies=login.cookies, 
		headers={
			'origin': 'https://analytics.diabetes-m.com',
			'authorization': 'Bearer '+auth_code
		}, json={
			'fromDate': -1,
			'toDate': -1,
			'page_count': 1000,
			'page_start_entry_time': 0
		})
	return entries.json()


def to_mgdl(mmol):
	return round(mmol*18)

def convert_nightscout(entries):
	out = []
	for entry in entries:
		bolus = entry["carb_bolus"] + entry["correction_bolus"]
		time = arrow.get(int(entry["entry_time"])/1000).to(entry["timezone"]).format()
		dat = {
			"eventType": "Meal Bolus",
			"created_at": time,
			"carbs": entry["carbs"],
			"insulin": bolus,
			"notes": entry["notes"],
			"enteredBy": NS_AUTHOR
		}
		if entry["glucose"]:
			dat.update({
				"eventType": "BG Check",
				"glucose": entry["glucose"] if entry["us_units"] else to_mgdl(entry["glucose"]),
				"glucoseType": "Finger",
				"units": "mg/dL"
			})

		out.append(dat)

	return out

def main():
	if True:
		login = get_login()
		if login.status_code == 200:
			entries = get_entries(login)
	else:
		entries = json.loads(open("entries.json","r").read())
	print(len(entries["logEntryList"]), "entries")


	"""open("simple_dm.json", "w").write(json.dumps([{
		"entry_time": i["entry_time"],
		"carb_bolus": i["carb_bolus"],
		"correction_bolus": i["correction_bolus"],
		"carbs": i["carbs"],
		"notes": i["notes"],
		"glucose": i["glucose"],
		"us_units": i["us_units"]
		} for i in entries["logEntryList"]]))
	"""


	ns_format = convert_nightscout(entries["logEntryList"])

	open("nsout.json", "w").write(json.dumps(ns_format))
	print(ns_format)


if __name__ == '__main__':
	main()

