#!/bin/python

#debendency  pywapi psi pysensors 

import pywapi
import sys
import datetime
import random
import os, platform, subprocess, re
import urllib2
import multiprocessing
import psi
import numpy

if (len(sys.argv) != 1):
	print 'Usage : python.py computer.py'
	sys.exit(-1)

verbose = True
energy = []

def get_processor_name():
    command = "cat /proc/cpuinfo"
    all_info = subprocess.check_output(command, shell=True).strip()
    for line in all_info.split("\n"):
        if "model name" in line:
            return re.sub( ".*model name.*:", "", line,1)
    return ""


#Laptop or desktop? If laptop, there's a lid...
mobile =  os.path.exists("/proc/acpi/button/lid/")
if (mobile):
	if verbose:
		print "You appear to be on a laptop"

#Processor
model = get_processor_name()
processor_energy = -1
while (processor_energy == -1): #Intel sometimes return a 500 error. We just have to retry 5 to 10 times...
	if (re.search( "intel", model,re.I)):
		model = re.sub( "\(r\)|\(tm\)|intel|[@][ ]?[0-9]+.[0-9]+[kmghz]+|cpu|celeron|\t", " ", model,0,re.I).strip()
		if verbose:
			print "Intel processor detected : " + model
		url = "http://ark.intel.com/search?q="+re.sub("[ ]+","+",model)
		try:
			content = urllib2.urlopen(url).read()

			tdp = re.search("([0-9]+) W",content,re.I | re.M)
			if tdp:
				processor_energy = float(tdp.group(1))
				if verbose:
					print "Processor MAX TDP found on intel.com : %f" % processor_energy
			else:
				regex = "href=\"/products/([0-9]+)/" + re.sub("[ ]+",".*?",model)
				m2 = re.search(regex,content,re.I | re.M | re.S)
				if m2:
					pid =  m2.group(1)
					content3 = urllib2.urlopen("http://ark.intel.com/products/"+pid+"/").read()
					m3 = re.search("([0-9]+) W",content3,re.I | re.M)
					if m3:
						processor_energy = float(m3.group(1))
						if verbose:
							print "Processor MAX TDP found on intel.com : %f" % processor_energy
				else:
					if verbose:
						print "Processor model could not be find on intel.com, assuming MAX TDP 65Watt"
					processor_energy = 65
		except:
			pass
	
	else:
		if verbose:
			print "Processour manufcaturer unknow, assuming MAX TDP 65Watt"
		processor_energy = 65

#Hard drives
all_info = subprocess.check_output("ls /dev/sd[a-z]", shell=True).strip()
for drive in all_info.split("\n"):
	dev_info = subprocess.check_output("hdparm -I " + drive, shell=True).strip()
	ssd = False
	for hi in dev_info.split("\n"):
		if "Solid State Device" in hi:
			ssd = True
	if ssd:
		if verbose:
			print "SSD Detected. Assuming 0.8Watt"
		energy.append(0.8)
	else:
		if mobile:	
			if verbose:		
				print "HDD Detected. Assuming 7Watt"
			energy.append(7)
		else:
			if verbose:
				print "HDD Detected. Assuming 2Watt"
			energy.append(2)

#---Processor load
load = (os.getloadavg()[2])/multiprocessing.cpu_count()
if verbose:
	print "Your system load is %.2f" % load
energy.append(processor_energy * (load/2 + 0.5))

#Motherboard
if (mobile):
	energy.append(10)
else:
	energy.append(25)

#Fans
nfan = 0
command = "cat /sys/class/thermal/cooling_device*/cur_state"
all_info = subprocess.check_output(command, shell=True).strip()
for line in all_info.split("\n"):
    if (float(line) >= 1):
	 nfan += 1;

if (mobile and nfan==0):
	nfan = 1

#---The power fan of desktop is nearly never monitored
if (not mobile):
	nfan += 1
if verbose:
	print "You appear to have %d fan." % nfan


#Calculating sum
somme = numpy.array(energy).sum()

#Average power conversion efficiency: 80%, and 1 watt base
somme = somme / 0.8 + 1

print somme
