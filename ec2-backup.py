#!/usr/bin/env python
import sys 
import os
import subprocess
import math
import time

verbose = '0'
SSH_FLAG = ''
AWS_FLAG = ''

if "EC2_BACKUP_FLAGS_SSH" in os.environ:
	SSH_FLAG = os.environ['EC2_BACKUP_FLAGS_SSH'][3:]
	#key_name = SSH_FLAG.split("/")[2]
	#print key_name

if "EC2_BACKUP_FLAGS_AWS" in os.environ:
	AWS_FLAG = os.environ['EC2_BACKUP_FLAGS_AWS'].split(' ')

if "EC2_BACKUP_VERBOSE" in os.environ:
	verbose =  os.environ['EC2_BACKUP_VERBOSE']


def Check_syntax(arg):
	path = ""
	volId = ""

	if len(arg) == 1 or len(arg) > 4:
		print "Invalid syntax, Use -h for help"
		sys.exit()
	elif len(arg) == 2 and arg[1] == "-h":
		print("ec2-backup help--\n\n"
      			"ec2-backup -- backup a directory into Elastic Block Storage (EBS)\n\n"
      			"Syntax: ec2-backup [-h] [-v volume-id] dir\n"
      			"	-h: Help \n"
      			"	-v volume-id: allows user to provide volume to backup the dir to.\n"
      			"	dir: allows user to provide directory without any flags.\n\n"
      			"Supported environment variable\n"
      			'	export Variable_Name="variable-Value"\n'
      			'	EC2_BACKUP_VERBOSE=1 if set to 1 then program print additional info as it goes through different stages.\n'
      			'	EC2_BACKUP_FLAGS_SSH="-i ~/.ssh/abc": if set, allows user to use specific ssh key.\n'
      			'	EC2_BACKUP_FLAGS_AWS= : if set, allows user to specify below aws flag when creating instance, else default values will be used.\n'
      			'		"--instance-type xyz" \n'
      			'		"--security-groups xyz" \n\n'
      			"Examples: \n"
      			"	ec2-backup -h \n"
      			"	ec2-backup /home  -  will create a volume in user's default aws region and backup /home data to that volume.\n"
      			"	ec2-backup -v vol-abc /home -  will backup /home data to specified volume. \n"
      			"	EC2_BACKUP_VERBOSE:1 ./ec2-backup -v vol-abc / - passing environment variable.\n\n"
				"Result: \n"
				"	If successful, program will print Volume-Id to which dir data was backed up.\n"
				"	If unsuccessful, program will print >0 with some error info.\n")


		sys.exit()
        elif len(arg) > 2 and arg[1] != "-v":
                print "Invalid syntax, Use -h for help."
		sys.exit()	
	elif len(arg) == 2 and arg[1] == "-v":
		print "Invalid syntax: expected a volume-id and directory after -v flag"
		print "Use -h for help"
		sys.exit()
	elif len(arg) == 2:
		if os.path.isdir(arg[1]) == True:
			path = str(arg[1])
			return (path, volId)
		else:	
			print "Invalid syntax, Use -h for help."
			sys.exit()
	elif len(arg) == 4 and str(sys.argv[1]) == "-v":
                if os.path.isdir(arg[3]) == True:
                        path = str(arg[3])
			volId = str(arg[2])
			return (path, volId)
		else:
			print "Provided directory is invalid, Please provide a valid directory"
			sys.exit()
        elif len(arg) == 3 and str(sys.argv[1]) == "-v":
		print "Invalid syntax: expected directory after volume-id"
		print "Use -h for help"
		sys.exit()
        elif len(arg) == 4 and str(sys.argv[1]) != "-v":
		print "Invalid syntax, Use -h for help"
		sys.exit()

def Check_dir_size(dir_path):
        process = subprocess.Popen(['du','-sh',dir_path], stderr = subprocess.PIPE, stdout = subprocess.PIPE)#.split()[0] #.decode('utf-8')
     	stdout, stderr = process.communicate()
	#dir_size = stdout.split()[0]
	return (stdout.split()[0], stderr)

def Check_volume(vId):
	try:
		volume = ''
		cmd = 'Regions[*].RegionName'
		regions = subprocess.check_output(['aws','ec2', 'describe-regions','--query',cmd,'--output','text'],).split()
		for region in regions:
			try:
				cmd2= 'Volumes[*].[[Attachments[0].InstanceId],[State],[AvailabilityZone],[Size]]'
				volume = subprocess.check_output(['aws','ec2', 'describe-volumes', '--region', region, '--volume-ids', vId,'--query',cmd2,'--output','text'],stderr = subprocess.STDOUT).split()
				return volume

			except subprocess.CalledProcessError as e:
				pass			
	except subprocess.CalledProcessError as e:
		print "Backup Failed: Error checking volume"
		print ">0"
		sys.exit()



def Compare_vol_dir_size (d_size, v_size):

	number = float(d_size[:-1])

	if 'K' in d_size:
		number = number * 1000
	if 'M' in d_size:
		number = number * 1000000
	if 'G' in d_size:
		number = number * 1000000000

	v_size = float(v_size) * 1000000000

	if v_size > number:
		return True
	else:
		return False

def Volume_size(directory_size):
	number =float(directory_size[:-1])
	if "K" or "M" in directory_size:
		if number <= 500:
			vol_size = 1
		else:
			vol_size = (int(math.ceil((number * 2) / 1000)))
	if "G" in directory_size:
		vol_size = (int(math.ceil((number * 2))))
	return vol_size
	
def Create_volume(v_size):	
	vol_avzone = ""
	cmd = "AvailabilityZones[*].[[State],[ZoneName]]"
	try:
		vol_avzone = subprocess.check_output(['aws','ec2', 'describe-availability-zones', '--query',cmd,'--output','text'],)
		vol_avzone = vol_avzone.split()[1]
	except subprocess.CalledProcessError as e:
		print "Backup Failed: Error creating volume"
		sys.exit()	
	try:
		vol_id = subprocess.check_output(['aws','ec2', 'create-volume', '--size', str(v_size), '--availability-zone', vol_avzone, '--query','VolumeId','--output','text'],).split()
		return (vol_id[0], vol_avzone)
	except subprocess.CalledProcessError as e:
		print "Backup Failed: Error creating volume"
		print ">0"
		sys.exit()	

def InstanceAmi (vol_reg):
	available_region_ami ={'eu-central-1' : 'ami-0233214e13e500f77','eu-west-1' : 'ami-047bb4163c506cd98','eu-west-2' : 'ami-f976839e','eu-west-3' : 'ami-0ebc281c20e89ba4b','us-east-1' : 'ami-0ff8a91507f77f867','us-east-2' : 'ami-0b59bfac6be064b78','us-west-1' : 'ami-0bdb828fd58c52235','us-west-2' : 'ami-a0cfeed8','sa-east-1' : 'ami-07b14488da8ea02a0','ap-northeast-1' : 'ami-06cd52961ce9f0d85','ap-northeast-2' : 'ami-0a10b2721688ce9d2','ap-south-1' : 'ami-0912f71e06545ad88','ap-southeast-1' : 'ami-08569b978cc4dfa10','ap-southeast-2' : 'ami-09b42976632b27e9b','ca-central-1' : 'ami-0b18956f'}
	if vol_reg not in available_region_ami:
		print 'Backup Failed: No AMI for Region: '+ vol_reg 
		print "Supported Regions: eu-central-1, eu-west-1, eu-west-2, eu-west-3, us-east-1, us-east-2, us-west-1, us-west-2, sa-east-1, ap-northeast-1, ap-northeast-2, ap-south-1, ap-southeast-1, ap-southeast-2, ca-central-1"
		return None
	else:
		instance_ami = available_region_ami[vol_reg]
		return instance_ami

def Create_instance(avzone, region, image, SSH_F, AWS_F):
	sec_group = 'default'
	inst_type = 't2.micro'
	key = 'ec2-backup'
	placement = "AvailabilityZone="+avzone

	if SSH_F != '':
		key = SSH_F.split("/")[2]	


	if AWS_FLAG != '':
		if  AWS_FLAG[0] == '--instance-type':
			inst_type = AWS_FLAG[1]
		elif  AWS_FLAG[0] == '--security-groups':
			sec_group = AWS_FLAG[1]
			print sec_group
		else:
			print "AWS environment variables not supported. Creating instance using default values"

	query = 'Instances[*].InstanceId'
	try:
		instance_id = subprocess.check_output(['aws','ec2', 'run-instances', '--image-id', str(image), '--instance-type',inst_type, '--key-name', key, '--security-groups', sec_group, '--region', region, '--placement', placement, '--query', query,'--output','text'],).split()
		time.sleep(70)
		return instance_id[0]
		#return (vol_id[0], vol_avzone)
	except subprocess.CalledProcessError as e:
		if AWS_FLAG != '':
			print "Backup Failed: Error creating instance"
			print "Please review AWS environment variable, to run the program with default values unset AWS environment variable"
		else:
			print "Backup Failed: Error creating instance"
		return None

def Volume_attach(v_id, i_id, region):
	device = '/dev/sdh'
	try:
		time.sleep(4)
		subprocess.check_output(['aws','ec2', 'attach-volume', '--region', region, '--volume-id', v_id,'--instance-id', i_id, '--device', device],)
		query= 'Volumes[*].[[Attachments[0].InstanceId]]'
		time.sleep(6)
		volume = subprocess.check_output(['aws','ec2', 'describe-volumes', '--region', region, '--volume-ids', v_id,'--query',query,'--output','text'],).split()
		return volume
	except subprocess.CalledProcessError as e:
		return None
	

def Dns_name (region, i_id):
	try:
		query = 'Reservations[*].Instances[*].PublicDnsName'
		dns = subprocess.check_output(['aws','ec2', 'describe-instances', '--region', region, '--instance-id', i_id,'--query',query,'--output','text'],).split()[0]		
		return dns
	except subprocess.CalledProcessError as e:
		print "Backup Failed: Error retrieving FQDN of instance"
		print ">0"
		sys.exit()


def Backup_data(path, name, identity):
	block = 'sudo dd of=/dev/xvdh 2>/dev/null'
	log = 'LogLevel=ERROR'
	hostkey = "StrictHostKeyChecking=no"
	hostname = 'ec2-user@'+name
	process = subprocess.Popen(['tar', 'cf', '-', path], stdout = subprocess.PIPE, stderr = subprocess.PIPE )
	try:
		if identity == '':
			data = subprocess.check_output(['ssh','-o', hostkey, '-o' ,log, hostname, block ], stdin = process.stdout)
			return True
		else:
			data = subprocess.check_output(['ssh','-i',identity,'-o',hostkey,'-o', log, hostname, block ], stdin = process.stdout)
			return True
	except subprocess.CalledProcessError as e:
		return None

def Terminate_instance(region, i_id):
	try:
		terminate = subprocess.check_output(['aws','ec2', 'terminate-instances', '--region', region, '--instance-id', i_id, '--output','text'],stderr = subprocess.STDOUT)	
		time.sleep(30)
	except subprocess.CalledProcessError as e:
		print "Error terminating instance"
		sys.exit()

def Delete_volume(region, v_id):
	try:
		delete_v = subprocess.check_output(['aws','ec2', 'delete-volume', '--region', region, '--volume-id', v_id, '--output','text'], stderr = subprocess.STDOUT )	
	except subprocess.CalledProcessError as e:
		print "Error deleting volume"
		sys.exit()

Result  = Check_syntax(sys.argv)

if Result[1] == "":
	dir_path = Result[0]
	directory = Check_dir_size(dir_path)
	size = directory[0]
	dir_error = directory[1]
	vol_size = Volume_size(size)
	volume = Create_volume(vol_size)
	vol_id = volume[0]
	vol_avzone = volume[1]
	vol_region = volume[1][:-1]
	if verbose == '1':
		print "Volume " + vol_id + " created in Availability Zone " + vol_avzone
	ami = InstanceAmi(vol_region)
	if ami == None:
		if verbose == '1':
			print "Deleting volume due to unsupported region"
		Delete_volume(vol_region, vol_id)
		print '>0'
		sys.exit()
	if verbose == '1':
		print "Creating a suitable instance in " + vol_avzone
	instance_id = Create_instance(vol_avzone, vol_region, ami, SSH_FLAG, AWS_FLAG)
	if instance_id == None:
		if verbose == '1':
			print "Deleting volume due to instance creation failure"
		Delete_volume(vol_region, vol_id)
		print '>0'
		sys.exit()
	if verbose == '1':
		print "Instance created: " + instance_id
	if verbose == '1':
		print "Attaching volume " + vol_id + " to instance " + instance_id	
	V_attached = Volume_attach(vol_id, instance_id, vol_region)
	if V_attached == None or V_attached[0] != instance_id:
		print "Error attaching volume to instnace, Terminating instance and volume"
		Terminate_instance(vol_region, instance_id)
		Delete_volume(vol_region, vol_id)
		print '>0'
		sys.exit()
	if verbose == '1':
		print "Volume attached"
	dns = Dns_name(vol_region, instance_id)
	if verbose == '1':
		print "Performing backup... "	
	Backup_result = Backup_data(dir_path, dns, SSH_FLAG)
	if Backup_result == None:
		print "Backup Failed due to SSH, Terminating instance and deleting volume " 
		Terminate_instance(vol_region, instance_id)
		Delete_volume(vol_region, vol_id)
		print ">0"
		sys.exit()
	if verbose == '1':
		print "Terminating instance: " + instance_id
	Terminate_instance(vol_region, instance_id)
	if verbose == '1':
		print "Backup complete: " + size + " of data written to:  "
	print vol_id
	if dir_error != '':
		print 'Due to permission issue, some of the files/directory in dir ' + dir_path + ' were not backed up.'


else:
	dir_path = Result[0]
	directory = Check_dir_size(dir_path)
	size = directory[0]
	dir_error = directory[1]
	if verbose == "1":
		print "Verifying volume"
	volume_info = Check_volume(Result[1])
	if volume_info == None:
		print "Volume " + Result[1] + " is invalid, Please provide a valid aws Volume-Id"
		sys.exit()
	elif volume_info[0] != 'None' and volume_info[1] != "available":
		print "Volume " + Result[1] + " is alredy in use, Please provide a Volume that is not in use"
		sys.exit()
	vol_size = volume_info[3]
	#compare volume size to dir size
	size_result = Compare_vol_dir_size(size, vol_size)
	if size_result == False:
		print 'Backup Error: Volume size is smaller than dirctory size. Please provide bigger size volume'
		sys.exit()
	vol_id = Result[1]
	vol_avzone = volume_info[2]
	vol_region = volume_info[2][:-1]
	if verbose == '1':
		print "Volume " + vol_id + " is in Availability Zone " + vol_avzone
	ami = InstanceAmi(vol_region)
	if verbose == '1':
		print "Creating a suitable instance in " + vol_avzone
	instance_id = Create_instance(vol_avzone, vol_region, ami, SSH_FLAG, AWS_FLAG)
	if instance_id == None:
		sys.exit()
	if verbose == '1':
		print "Instance created: " + instance_id
	if verbose == '1':
		print "Attaching volume " + vol_id + " to instance " + 	instance_id
	V_attached = Volume_attach(vol_id, instance_id, vol_region)
	if V_attached == None or V_attached[0] != instance_id:
		print "Error attaching Volume to instnace, Terminating instance"
		Terminate_instance(vol_region, instance_id)
		print ">0"
		sys.exit()
	if verbose == '1':
		print "Volume attached"
	dns = Dns_name(vol_region, instance_id)
	if verbose == '1':
		print "Performing backup... "	
	Backup_result = Backup_data(dir_path, dns, SSH_FLAG)
	if Backup_result == None:
		print "Backup Failed due to SSH, Terminating instance "
		Terminate_instance(vol_region, instance_id)
		print '>0'
		sys.exit()
	if verbose == '1':
		print "Terminating instance: " + instance_id
	Terminate_instance(vol_region, instance_id)
	if verbose == '1':
		print "Backup complete: " + size + " of data written to:  "
	print vol_id
	if dir_error != '':
		print 'Due to permission issue, some of the files/directory in dir ' + dir_path + ' were not backed up.'
