import requests, json
from .secret import USERNAME, PASSWORD


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
	return int(mmol*18)

def main():
	if True:
		login = get_login()
		if login.status_code == 200:
			entries = get_entries(login)
	else:
		entries = json.loads(open("entries.json","r").read())
	print(len(entries["logEntryList"]), "entries")


if __name__ == '__main__':
	main()

