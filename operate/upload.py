from os.path import basename
import subprocess
from subprocess import PIPE

def upload(source):
	print("uploading to chee.party/music")
	subprocess.run([
		"rsync",
		"-zL",
		"--progress",
		source,
		f"yay@chee.party:music/{basename(source)}"
	], stdout=PIPE)
