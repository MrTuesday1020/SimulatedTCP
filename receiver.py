#!/usr/bin/python3
# Test by python3

from random import *
import json
import socket
import sys

# the IP address of receiver
IP = "127.0.0.1"
# the port number of receiver
PORT = sys.argv[1]
FileName = sys.argv[2]
seq = -1
ack = -1
# buffer to store data
dataBuffer = []
bufferSize = 1024
dataReceived = 0
noOfSegments = 0
noOfDupilcate = 0

receiverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
receiverSocket.bind((IP, int(PORT)))


# get the right ack number from data buffer
def getAck():
	global dataBuffer, ack
	dataBuffer = sorted(dataBuffer)
	if len(dataBuffer) == 1 :
		ack = dataBuffer[0][0] + dataBuffer[0][1]
	else:
		for i in range(len(dataBuffer)-1):
			if dataBuffer[i][0] + dataBuffer[i][1] != dataBuffer[i+1][0]:
				ack = dataBuffer[i][0] + dataBuffer[i][1]
				break
			else:
				ack = dataBuffer[i+1][0] + dataBuffer[i+1][1]
	return ack


while True:
	rsegment, address = receiverSocket.recvfrom(bufferSize)
	rsegment = json.loads(rsegment.decode('utf-8'))
	
	##############################################################
	# first time to receive request of establishment
	if rsegment['S'] == 1 and rsegment['A'] == 0 :
		ack = rsegment['seq'] + 1
		ssegment = {'seq':seq, 'ack':ack, 'len': None, 'S':1, 'A':1, 'F': 0, 'D':0, 'data': None}
		ssegment = json.dumps(ssegment)
		receiverSocket.sendto(ssegment.encode('utf-8'), address)
		
	# second time to receive request of establishment
	if rsegment['S'] == 1 and rsegment['A'] == 1 :
		seq = rsegment['ack']
		continue
		
	##############################################################
	# receive data
	if rsegment['D'] == 1 :
		print(rsegment['seq'])
		data = [rsegment['seq'],rsegment['len'],rsegment['data']]
		if data not in dataBuffer:
			dataBuffer.append(data)
			dataReceived += rsegment['len']
			noOfSegments += 1
		else:
			noOfDupilcate += 1
		ack = getAck()
		ssegment = {'seq':seq, 'ack':ack, 'len': None, 'S':0, 'A':1, 'F': 0, 'D':0, 'data': None}
		ssegment = json.dumps(ssegment)
		receiverSocket.sendto(ssegment.encode('utf-8'), address)
		
	##############################################################
	# first time to receive request of teardown
	if rsegment['F'] == 1 and rsegment['A'] == 0 :
		ack = rsegment['seq'] + 1
		ssegment = {'seq':seq, 'ack':ack, 'len': None, 'S':0, 'A':1, 'F': 1, 'D':0, 'data': None}
		ssegment = json.dumps(ssegment)
		receiverSocket.sendto(ssegment.encode('utf-8'), address)
			
	# second time to receive request of establishment
	if rsegment['F'] == 1 and rsegment['A'] == 1 :
		seq = rsegment['ack']
		break

logfile = []
logfile.append(("Amount of data received: ", dataReceived))
logfile.append(("Number of data segments received: ", noOfSegments))
logfile.append(("Amount of data duplicate segments: ", noOfDupilcate))
	
with open("Receiver_log.txt", "w") as output:
	for log in logfile:
		output.write(str(log)+'\n')	

with open(FileName, "w") as output:
	for data in dataBuffer:
		output.write(data[2])