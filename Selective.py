# SimPy models for rdt_Sender and rdt_Receiver
# implementing the Go-Back-N Protocol

# Author: Dr. Neha Karanjkar, IIT Goa

import simpy
import random
import sys
from Packet import Packet



	


class rdt_Sender(object):
	
	def __init__(self,env):
		
		# Initialize variables and parameters
		self.env=env 
		self.channel=None
		
		# some default parameter values
		self.data_packet_length=10 # bits
		self.timeout_value=10 # default timeout value for the sender
		self.N=5 # Sender's Window size
		self.K=32

		# some state variables and parameters for the Go-Back-N Protocol
		self.base=0 # base of the current window 
		self.nextseqnum=0 # next sequence number
		self.sndpkt= {} # a buffer for storing the packets to be sent (implemented as a Python dictionary)

		# Setting up a timer list for all the packets
		self.rdt_sender = None
		self.timeout_value =15
		self.timer_is_running=False
		
		self.timer_dict = {} #This dictionary stores whether timer is running or not
		self.timer_processes = {}
		self.ack_dict = {}
		self.i=0

		# Packet Number for which timeout has occured
		self.l=0
		
		for self.i in range(0, self.K):
			self.timer_dict[self.i] = self.timer_is_running

		# some other variables to maintain sender-sidtimer.interrupt()e statistics
		self.total_packets_sent=0
		self.num_retransmissions=0



	

	# Finally, these functions are used for modeling a Timer's behavior.
	def timer_behavior(self, l):
		try:
			# Wait for timeout 
			self.timer_dict[l]=True
			
			yield self.env.timeout(self.timeout_value, l)
			
			self.timer_dict[l]=False
			# take some actions 
			self.timeout_action(l)
		except simpy.Interrupt:
			# stop the timer
			self.timer_dict[l]=False

	# This function can be called to start the timer
	def start_timer(self, l):
		assert(self.timer_dict[l]==False)
		self.timer_processes[l]=self.env.process(self.timer_behavior(l))
		print("TIME:",self.env.now,"TIMER STARTED for", l, "for a timeout of ",self.timeout_value)
		
	# This function can be called to stop the timer
	def stop_timer(self, l):
		assert(self.timer_dict[l]==True)
		self.timer_processes[l].interrupt()
		print("TIME:",self.env.now,"TIMER STOPPED.")
		
	def restart_timer(self, l):
		# stop and start the timer
		assert(self.timer_dict[l]==True)
		self.timer_processes[l].interrupt()
		assert(self.timer_dict[l]==False)
		self.timer_processes[l]=self.env.process(self.timer_behavior(l))
		print("TIME:",self.env.now,"TIMER RESTARTED for a timeout of ",self.timeout_value)



		
	# Actions to be performed upon timeout
	def timeout_action(self, l):
		# Here l is the packet number for which timeout has occurred
		packet_to_be_resent = self.sndpkt[l]
		print("TIME:",self.env.now,"RDT_SENDER: TIMEOUT OCCURED FOR", l, ". Re-transmitting packet ", packet_to_be_resent)
		self.channel.udt_send(self.sndpkt[l])
		self.num_retransmissions+=1
		self.total_packets_sent+=1
		# Re-start the timer
		self.start_timer(l)

			
	
	def rdt_send(self,msg):
		# This function is called by the 
		# sending application.
		# check if the nextseqnum lies within the 
		# range of sequence numbers in the current window.
		# If it does, make a packet and send it,
		# else, refuse this data.
		print(self.timer_dict)
		print("\nSndPkt Dict: ", self.sndpkt)
		if(self.nextseqnum in [(self.base+i)%self.K for i in range(0,self.N)]):
			print("TIME:",self.env.now,"RDT_SENDER: rdt_send() called for nextseqnum=",self.nextseqnum," within current window. Sending new packet.")
			# create a new packet and store a copy of it in the buffer
			self.sndpkt[self.nextseqnum]= Packet(seq_num=self.nextseqnum, payload=msg, packet_length=self.data_packet_length)
			self.ack_dict[self.nextseqnum] = True
			# send the packet
			self.channel.udt_send(self.sndpkt[self.nextseqnum])
			self.total_packets_sent+=1
			
			
			self.start_timer(self.nextseqnum)
			
			
			# update the nextseqnum
			self.nextseqnum = (self.nextseqnum+1)%self.K
			return True
		else:
			print("TIME:",self.env.now,"RDT_SENDER: rdt_send() called for nextseqnum=",self.nextseqnum," outside the current window. Refusing data.")
			return False

	
	def rdt_rcv(self,packt):
		# This function is called by the lower-layer 
		# when an ACK packet arrives
		print("$$", self.timer_dict[self.nextseqnum])
		
		if (packt.corrupted==False):
			
			print("Hey! Received Something!")
			print("Here is the packet number: ", packt.payload, packt.seq_num)
			# check if we got an ACK for a packet within the current window.
			if(packt.seq_num in self.sndpkt.keys()):
				
				if (self.base==packt.seq_num):
					del self.sndpkt[packt.seq_num]		# Marking as received
					del self.ack_dict[packt.seq_num]
					
					if(not bool(self.sndpkt)):
						self.base = self.nextseqnum % self.K
					
					else:
						print(min(self.sndpkt.keys()), "kkkkkkkkkkkkkkkkkkkkk")
						self.base = min(self.sndpkt.keys()) % self.K
						

					self.stop_timer(packt.seq_num%self.K)

					

				elif (self.base<packt.seq_num):
					del self.sndpkt[packt.seq_num%self.K]		# Marking as received
					
					
					
					self.stop_timer(packt.seq_num%self.K)
				
				# exit the while loop
				print("TIME:",self.env.now,"RDT_SENDER: Got an ACK",packt.seq_num,". Updated window:", [(self.base+i)%self.K for i in range(0,self.N)],"base =",self.base,"nextseqnum =",self.nextseqnum)
			else:
				print("TIME:",self.env.now,"RDT_SENDER: Got an ACK",packt.seq_num," for a packet in the old window. Ignoring it.")
		
		else:
			print("!!!!Received corrupted ACK", packt.seq_num, "!!!!")
		


	# A function to print the current window position for the sender.
	def print_status(self):
		print("TIME:",self.env.now,"Current window:", [(self.base+i)%self.K for i in range(0,self.N)],"base =",self.base,"nextseqnum =",self.nextseqnum)
		print("---------------------")

#==========================================================================================

class rdt_Receiver(object):
	
	def __init__(self,env):
		
		# Initialize variables
		self.env=env
		self.receiving_app=None
		self.channel=None

		# Some default parameter values
		self.ack_packet_length=10 # bits
		self.K=16 # range of sequence numbers expected

		# Initialize state variables
		self.expectedseqnum=0
		self.sndpkt= Packet(seq_num=0, payload="ACK",packet_length=self.ack_packet_length)
		self.total_packets_sent=0
		self.num_retransmissions=0

		# Some state variables and parameters for the Go-Back-N Protocol
		self.base=0 # base of the current window 
		self.nextseqnum=0 # next sequence number
		self.delivery_pkts= {} # a buffer for storing the packets to be delivered (implemented as a Python dictionary)
		

		# Some default parameter values
		self.data_packet_length=10 # bits
		self.timeout_value=10 # default timeout value for the sender
		self.N=5 # Sender's Window size
		self.K=32 # Packet Sequence numbers can range from 0 to K-1


	def rdt_rcv(self,packt):
		# This function is called by the lower-layer 
		# when a packet arrives at the receiver
		print("RDT_RECEIVER: Just got packet:", packt)
		print("\nBase of rdt_receiver at: ", self.base, "\n")
		print("\n\nTHIS IS MY BUFFER\n\n", self.delivery_pkts)
		if(packt.seq_num in [(self.base+i)%self.K for i in range(0,self.N)]):
			
			
			if(packt.corrupted==False and packt.seq_num==self.base):
				# extract and deliver data
				print("RDT_RECEIVER: Here packt.seq_num==base. self.base=", self.base, "Checking if it's in the buffer. If not then Delievering this to Receiving Application..")
				
				if(packt.seq_num in self.delivery_pkts.keys()):
					print('++++++++The Packet I got is already in the Buffer++++++++')
					self.delivery_pkts[packt.seq_num].append(packt.payload)
				else:	
					print("''''''''''''Delivering from base directly''''''''''''")
					self.receiving_app.deliver_data(packt.payload)

				print("TIME:",self.env.now,"RDT_RECEIVER: got expected packet",packt.seq_num)
				
				if(bool(self.delivery_pkts.keys())):
					if(self.base==min(self.delivery_pkts.keys())):
						while(self.base in self.delivery_pkts.keys()):
							if(len(self.delivery_pkts[self.base])!=0):
								packet_to_be_delivered = self.delivery_pkts[self.base][0]
								print("\nAYo!! Delivering ", packt)
								print("\n")
								self.receiving_app.deliver_data(packet_to_be_delivered)
								self.delivery_pkts[self.base].pop()

								if(len(self.delivery_pkts[self.base])==0):
									del self.delivery_pkts[self.base]

						self.base = (self.base+1)%self.K

				# send an ACK for the newly received packet
				self.sndpkt=Packet(seq_num=packt.seq_num, payload="ACK",packet_length=self.ack_packet_length) 
				self.channel.udt_send(self.sndpkt)
				self.total_packets_sent+=1

				# increment the expectedseqnum modulo K
				self.expectedseqnum = (self.expectedseqnum + 1)%self.K

				self.base = (self.base+1)%self.K
				self.nextseqnum = (self.nextseqnum+1)%self.K
				print("\nTIME:",self.env.now,"RDT_RECEIVER: Got a Packet",packt.seq_num,". Current window:", [(self.base+i)%self.K for i in range(0,self.N)],"base =",self.base,"nextseqnum =",self.nextseqnum)


			elif(packt.corrupted==False and ((self.base + 1)%self.K <= packt.seq_num <= (self.base + self.N - 1) % self.K)):
				
				# extract data along with the packet.seq_num
				if(packt.seq_num not in self.delivery_pkts.keys()):
					self.delivery_pkts[packt.seq_num] = []

				self.delivery_pkts[packt.seq_num].append(packt.payload)
				print("TIME:",self.env.now,"RDT_RECEIVER: got expected packet. But packet number is not same as base. Buffering it!",packt.seq_num,". Sent ACK",packt.seq_num)

				# send an ACK for the newly received packet
				self.sndpkt=Packet(seq_num=packt.seq_num, payload="ACK", packet_length=self.ack_packet_length) 
				self.channel.udt_send(self.sndpkt)
				self.total_packets_sent+=1
				print("Packets to be delivered:: ", self.delivery_pkts)

				

			else:
				# got a corrupted or unexpected packet.
				# send the ACK for the oldest packet received successfully
				if(packt.corrupted):
					print("TIME:",self.env.now,"RDT_RECEIVER: got corrupted packet", packt.seq_num,"/////////////////////////////////",". Sent ACK",self.sndpkt.seq_num)
				

			print("\n")
			
			""" if(bool(self.delivery_pkts.keys())): """
			""" if(self.base==min(self.delivery_pkts.keys())): """
			""" if(bool(self.delivery_pkts.keys())):
				if(self.base==min(self.delivery_pkts.keys())):
					while(self.base in self.delivery_pkts.keys()):
						if(len(self.delivery_pkts[self.base])!=0):
							packet_to_be_delivered = self.delivery_pkts[self.base][0]
							print("\nAYo!! Delivering ", packt)
							print("\n")
							self.receiving_app.deliver_data(packet_to_be_delivered)
							self.delivery_pkts[self.base].pop()

							if(len(self.delivery_pkts[self.base])==0):
								del self.delivery_pkts[self.base]

						self.base = (self.base+1)%self.K """

			print("$delivery pkts$", self.delivery_pkts)

		elif((packt.corrupted==False) and packt.seq_num not in [(self.base+i)%self.K for i in range(0,self.N)]):
			
			print("TIME:",self.env.now,"RDT_RECEIVER: got unexpected packet with sequence number",packt.seq_num,". Sent ACK",self.sndpkt.seq_num)
			self.sndpkt=Packet(seq_num=packt.seq_num, payload="ACK",packet_length=self.ack_packet_length) 
			self.channel.udt_send(self.sndpkt)
			self.total_packets_sent+=1
			self.num_retransmissions+=1
			print("Sending ACK ", packt.seq_num, "Again!")

