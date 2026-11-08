# Downloads the dlib face recognition models used by howdy at build time.
# Called from meson when the fetch_dlib_data option is enabled, with the
# output directory as the only argument. Honors the http_proxy/https_proxy
# environment variables and falls back to github mirror prefixes.

import bz2
import hashlib
import os
import sys
import urllib.request
from urllib.parse import urlparse

BASE_URL = "https://github.com/davisking/dlib-models/raw/master/"

# Mirror prefixes that are tried in order when the original URL fails
MIRRORS = [
	"",
	"https://ghfast.top/",
	"https://gh-proxy.com/",
]

# Archive name and the sha256 checksum of the compressed archive
MODELS = [
	("dlib_face_recognition_resnet_model_v1.dat.bz2",
	 "abb1f61041e434465855ce81c2bd546e830d28bcbed8d27ffbe5bb408b11553a"),
	("mmod_human_face_detector.dat.bz2",
	 "db9e9e40f092c118d5eb3e643935b216838170793559515541c56a2b50d9fc84"),
	("shape_predictor_5_face_landmarks.dat.bz2",
	 "6e787bbebf5c9efdb793f6cd1f023230c4413306605f24f299f12869f95aa472"),
]

opener = None


def build_opener():
	"""Build a request opener that goes through the environment proxy"""
	proxy = os.environ.get("http_proxy") or os.environ.get("https_proxy")
	if not proxy:
		return urllib.request.build_opener()

	# Normalize the proxy to a plain http:// URL so urllib CONNECTs without
	# trying to speak TLS to the local proxy itself
	parsed = urlparse(proxy)
	proxy_url = "http://" + parsed.netloc
	return urllib.request.build_opener(
		urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
	)


def fetch(url):
	"""Download a url, trying every mirror before giving up"""
	last_error = None
	for mirror in MIRRORS:
		try:
			with opener.open(mirror + url, timeout=120) as response:
				return response.read()
		except Exception as error:
			last_error = error
			print("Download failed from " + mirror + url + ": " + str(error))
	raise SystemExit("Unable to download " + url + ": " + str(last_error))


def main():
	global opener

	if len(sys.argv) != 2:
		raise SystemExit("usage: fetch.py <output-dir>")

	outdir = sys.argv[1]
	os.makedirs(outdir, exist_ok=True)
	opener = build_opener()

	for (archive, checksum) in MODELS:
		out_path = os.path.join(outdir, archive[:-4])

		# Reuse a previously extracted model to keep repeated builds cheap
		if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
			print("Using existing " + out_path)
			continue

		print("Downloading " + archive + " ...")
		data = fetch(BASE_URL + archive)

		actual = hashlib.sha256(data).hexdigest()
		if actual != checksum:
			raise SystemExit(
				"Checksum mismatch for " + archive + ": expected " + checksum + ", got " + actual
			)

		with open(out_path, "wb") as handle:
			handle.write(bz2.decompress(data))
		print("Wrote " + out_path)


if __name__ == "__main__":
	main()
