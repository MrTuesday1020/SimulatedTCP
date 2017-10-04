#!/usr/bin/python
# Test by python3

import random
import threading
from threading import Timer
from time import time
import socket
import json
import sys
import os

############################################################
# some constants
# the IP address of receiver
IP = sys.argv[1]
# the port number of receiver
PORT = sys.argv[2]
# the file the sender needs to send to receiver
FileName = sys.argv[3]
# maximun window size
MWS = int(sys.argv[4])
# maximum segment size
MSS = int(sys.argv[5])
# the value of timeout in milliseconds
Timeout = int(sys.argv[6])
Timeout = Timeout/1000
# the probablity of the segment to be dropped
Pdrop = float(sys.argv[7])
# the seed for random number generate
Seed = int(sys.argv[8])
random.seed(Seed)
# some golbal arguments
# connection status
Connection = False
SYN = 0
ACK = 0
FIN = 0
seq = -1
ack = -1
# LastByteSent - LastByteAcked <= MWS
LastByteSent = 0
LastByteAcked = -1
DuplicatedAck = 1
# SendBase is the sequence number of the oldest unacked byte
# SendBase = LastByteAcked + 1
# SendBase = 0
# log file
start = time()
logfile = []
# statistics
amountOfData = 0		# amount of data trasnfered
noOfSege = 0			# number of segments sent
noOfdroped = 0			# numebr of packets droped
noOfRetr = 0			# number of retransmit segments
noOfDupl = 0			# number of duplicated acks
# timer status
TimerIsAlive = False
# read file content
with open (FileName, "r") as myfile:
	FileContent = myfile.read()
lock = threading.Lock()
senderSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


############################################################
# timeout thread
class MyTime(object):
	def __init__(self, timeout, f, *args, **kwargs):
		self.timeout = timeout
		self.f = f
		self.args = args
		self.kwargs = kwargs
		self.timer = None

	def callback(self):
		self.f(*self.args, **self.kwargs)
		self.start()

	def start(self):
		self.timer = Timer(self.timeout, self.callback)
		self.timer.start()
	
	def cancel(self):
			self.timer.cancel()
			
def Retransmit():
	print("Retransmit: ",LastByteAcked + 1)
	retrSeq = LastByteAcked + 1
	message = FileContent[retrSeq:retrSeq+MSS]
	length = len(message)
	segment = {'seq':retrSeq, 'ack':None, 'len': length, 'S':0, 'A':0, 'F': 0, 'D':1, 'data': message} 
	segment = json.dumps(segment)
	senderSocket.sendto(segment.encode('utf-8'), (IP, int(PORT)))
	# write logfile
	runtime = round((time() - start) * 1000, 3)
	loglist = ['snd', runtime, 'D' , retrSeq, length, ack]
	logfile.append(loglist)
timer = MyTime(Timeout, Retransmit)



############################################################
# sending data thread
class MySend (threading.Thread):
	def __init__(self, name):
		threading.Thread.__init__(self)
		self.name = name
	
	def run(self):
		global Connection, SYN, ACK, FIN, seq, ack, FileContent, TimerIsAlive, LastByteSent, LastByteAcked, logfile, start, time, amountOfData, noOfSege, noOfdroped
		
		# establish connection
		while Connection == False :
			# first time to send request of establishment
			if SYN == 0 and ACK == 0 :
				lock.acquire()
				segment = {'seq':seq, 'ack':None, 'len': None, 'S':1, 'A':0, 'F': 0, 'D':0, 'data': None}
				segment = json.dumps(segment)
				senderSocket.sendto(segment.encode('utf-8'), (IP, int(PORT)))
				# write logfile
				runtime = round((time() - start) * 1000, 3)
				loglist = ['snd', runtime, 'S' , seq, 0, None]
				logfile.append(loglist)
				SYN = 1
				lock.release()
			# second time to send request of establishment
			if SYN == 1 and ACK == 1 :
				lock.acquire()
				segment = {'seq':None, 'ack':ack, 'len': None,'S':1, 'A':1, 'F': 0, 'D':0, 'data': None}
				segment = json.dumps(segment)
				senderSocket.sendto(segment.encode('utf-8'), (IP, int(PORT)))
				# write logfile
				runtime = round((time() - start) * 1000, 3)
				loglist = ['snd', runtime, 'A' , seq, 0, ack]
				logfile.append(loglist)
				ACK = 0
				SYN = 0
				Connection = True
				lock.release()
				print("connected!!!")
				
		#send data segment
		while (seq < len(FileContent)):
			if (LastByteSent - LastByteAcked <= MWS):
				lock.acquire()
				drop = PLD()
				if drop == True :
					noOfdroped += 1
					message = FileContent[seq:seq+MSS]
					length = len(message)
					# write logfile
					print("drop!!!",seq)
					runtime = round((time() - start) * 1000, 3)
					loglist = ['drop', runtime, 'D' , seq, length, ack]
					logfile.append(loglist)
				else:
					message = FileContent[seq:seq+MSS]
					length = len(message)
					segment = {'seq':seq, 'ack':None, 'len': length, 'S':0, 'A':0, 'F': 0, 'D':1, 'data': str(message)} 
					segment = json.dumps(segment)
					senderSocket.sendto(segment.encode('utf-8'), (IP, int(PORT)))
					# write logfile
					runtime = round((time() - start) * 1000, 3)
					loglist = ['snd', runtime, 'D' , seq, length, ack]
					logfile.append(loglist)
				amountOfData += length
				noOfSege += 1
				seq = seq + length
				LastByteSent = seq -1
				if TimerIsAlive == False :
					TimerIsAlive = True
					timer.start()
				lock.release()
				
			
		# teardown connection
		while Connection == True :
			if LastByteAcked == len(FileContent) - 1 :
				# first time to send request of teardown
				if FIN == 0 and ACK == 0 :
					lock.acquire()
					segment = {'seq':seq, 'ack':None, 'len': None, 'S':0, 'A':0, 'F': 1, 'D':0, 'data': None}
					segment = json.dumps(segment)
					senderSocket.sendto(segment.encode('utf-8'), (IP, int(PORT)))
					# write logfile
					runtime = round((time() - start) * 1000, 3)
					loglist = ['snd', runtime, 'F' , seq, 0, ack]
					logfile.append(loglist)
					FIN = 1
					lock.release()
				# second time to send request of teardown
				if FIN == 1 and ACK == 1 :
					lock.acquire()
					segment = {'seq':None, 'ack':ack, 'len': None,'S':0, 'A':1, 'F': 1, 'D':0, 'data': None}
					segment = json.dumps(segment)
					senderSocket.sendto(segment.encode('utf-8'), (IP, int(PORT)))
					# write logfile
					runtime = round((time() - start) * 1000, 3)
					loglist = ['snd', runtime, 'A' , seq, 0, ack]
					logfile.append(loglist)
					ACK = 0
					FIN = 0
					Connection = False
					lock.release()
					
					print("teardown!!!")
					
#					logfile.append(('Amount of data trasnfered: ',amountOfData))
#					logfile.append(('Number of segments sent: ',noOfSege))
#					logfile.append(('Numebr of packets droped: ',noOfdroped))
#					logfile.append(('Number of retransmit segments: ',noOfRetr))
#					logfile.append(('Number of duplicated acks: ',noOfDupl))
#
#					with open("Sender_log.txt", "w") as output:
#						for log in logfile:
#							output.write(str(log)+'\n')
#
#					
#					os._exit(0)
					



############################################################
# receiving acks thread
class MyAck (threading.Thread):
	def __init__(self, name):
		threading.Thread.__init__(self)
		self.name = name
	
	def run(self):
		global TimerIsAlive, SYN, ACK, FIN, seq, ack, LastByteSent, LastByteAcked, logfile, start, DuplicatedAck, time, noOfRetr, noOfDupl
		
		while True:
			segment = senderSocket.recv(1024)
			segment = json.loads(segment.decode('utf-8'))
			# ack establishing
			if segment['S'] == 1 and segment['A'] == 1 :
				lock.acquire()
				# write logfile
				runtime = round((time() - start) * 1000, 3)
				loglist = ['rcv', runtime, 'SA' , seq, 0, ack]
				logfile.append(loglist)
				ACK = 1
				seq = segment['ack']
				ack = segment['seq'] + 1
				lock.release()
			
			# ack data
			if segment['F'] == 0 and segment['S'] == 0 and segment['A'] == 1 :
				if segment['ack'] != len(FileContent):
					if segment['ack'] > LastByteAcked + 1 :
						lock.acquire()
						LastByteAcked = segment['ack'] - 1
						# write logfile
						runtime = round((time() - start) * 1000, 3)
						loglist = ['rcv', runtime, 'A' , seq, 0, segment['ack']]
						logfile.append(loglist)
						if LastByteAcked != LastByteSent :
							if TimerIsAlive == True :
								timer.cancel()
								timer.start()
							else:
								TimerIsAlive = True
								timer.start()
						lock.release()
					if segment['ack'] == LastByteAcked + 1 :
						lock.acquire()
						DuplicatedAck += 1
						lock.release()
						noOfDupl += 1
						if DuplicatedAck == 3 :
							noOfRetr += 1
							lock.acquire()
							DuplicatedAck = 1
							Retransmit()
							if TimerIsAlive == True :
								timer.cancel()
								timer.start()
							else:
								TimerIsAlive = True
								timer.start()
							lock.release()
				else:
					# close the timer
					if TimerIsAlive == True :
						timer.cancel()
					lock.acquire()
					LastByteAcked = segment['ack'] - 1
					lock.release()
					continue
					
								
			# ack teardown
			if segment['F'] == 1 and segment['A'] == 1 :
				lock.acquire()
				# write logfile
				runtime = round((time() - start) * 1000, 3)
				loglist = ['rcv', runtime, 'FA' , seq, 0, ack]
				logfile.append(loglist)
				ACK = 1
				seq = segment['ack']
				ack = segment['seq'] + 1
				lock.release()
				break



############################################################
def PLD():
	if (random.random() > Pdrop):
		return False;
	else:
		return True;



############################################################
def main():
	# create sending and acking thread
	dataThread = MySend("Sender")
	ackThread = MyAck("Receiver")
	# run these two threads
	dataThread.start()
	ackThread.start()
	dataThread.join()
	ackThread.join()

	logfile.append(('Amount of data trasnfered: ',amountOfData))
	logfile.append(('Number of segments sent: ',noOfSege))
	logfile.append(('Numebr of packets droped: ',noOfdroped))
	logfile.append(('Number of retransmit segments: ',noOfRetr))
	logfile.append(('Number of duplicated acks: ',noOfDupl))

	with open("Sender_log.txt", "w") as output:
		for log in logfile:
			output.write(str(log)+'\n')
	

if __name__ == '__main__':
	main()