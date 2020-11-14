from os.path import basename
import subprocess
from subprocess import PIPE

def upload(source):
	print("uploading to chee.snoot.club/music")
	subprocess.run([
		"rsync",
		"-zL",
		"--progress",
		source,
		f"chee@snoot.club:music/{basename(source)}"
	], stdout=PIPE)
