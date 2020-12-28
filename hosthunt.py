import requests 
import re
import time
import subprocess
import platform
import traceback

CHUNK_SIZE = 1024*128

output = open("hosthunt.csv", "w")

def download(url):
	run_time = 20
	with requests.get(url, stream=True) as response:
		response.raise_for_status()
		start = time.time()
		speed_points = [0] * (run_time)
		downloaded = 0
		previous_speed = 0
		delta_sequence = 0
		for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
			downloaded += len(chunk)
			speed = round((downloaded / (time.time() - start)) / 1_000_000, 4)
			delta = abs(previous_speed - speed)
			
			# Breaking condition, we stop measuring speed once the speed is settled 
			# if delta <= 0.01:
			# 	delta_sequence += 1
			# else:
			# 	delta_sequence = 0

			# if delta_sequence >= 10 and time.time() - start > 10:
			# 	return speed

			speed_points[min(int(time.time() - start), run_time-1)] = speed

			if time.time() - start > run_time:
				return speed_points

			print(url, speed, "MB/s           ", end="\r")

			previous_speed = speed

def ping(host):
	return int(re.findall( r"(\d+)\s?ms", subprocess.Popen([
		"ping",
		"-n" if platform.system().lower()=="windows" else "-c",
		"1",
		host
	], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8").stdout.read())[0])

def findgroup(regex, data):
	match = list(re.finditer(regex, data))
	if not match:
		return {}
	return match[0].groupdict()

if __name__ == "__main__":

	response = requests.get("https://looking.house/")

	for country in re.findall(r"\?country=(\d+)", response.text):
		response = requests.get("https://looking.house/points.php?country={0}".format(country))

		for host_text in re.findall(r"(?sm)\<tr\>(.*?)\<\/tr\>", response.text):
			info = {
				**findgroup(r"href=\"(?P<file>.*?)\".*?\>1000\sMB\<", host_text),
				**findgroup(r"\/company\.php\?id\=(?P<company_id>\d+).*?\>(?P<company_name>.*?)\<\/a\>", host_text),
				**findgroup(r"ModalMap\(.*?\'(?P<location>.*?)(?:<br.*?)?\'\);", host_text),
				**findgroup(r"\"\>(?P<ipv4>.*?)\<hr.*?margin\:9px\s0px\;\"\>\s*(?P<ipv6>.*?)\s*\<", host_text),
				**findgroup(r"line\-height\:59px\;\"\>(?P<ipv4>.*?)\<\/", host_text),
				"ping": -1
			}
			if not info.get("file"): continue

			try:
				info["ping"] = ping(info["ipv4"])
			except:
				traceback.print_exc()
			
			try:
				info["speed"] = download(info["file"])
			except:
				traceback.print_exc()
			
			print(info)

			if info.get("speed"):
				for second, point in enumerate(info["speed"]):
					output.write(",".join([
						info["company_id"],
						info["company_name"],
						"\"" + info["location"] + "\"",
						str(info["ping"]),
						str(second),
						str(point)
					]) + "\n")
					output.flush()