import sys
import os

def restart():
	python = sys.executable
	os.execl(python, python, *sys.argv)

def stop():
	sys.exit()