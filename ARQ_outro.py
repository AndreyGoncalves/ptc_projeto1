# -*- coding: utf-8 -*-
#Interpreta o arquivo como utf-8 (aceita acentos)
from enum import Enum
import crcmod.predefined
from binascii import unhexlify
import enlayce
import enquadramento
import select

class ARQ:

	def __init__(self, enq, timeout):
		self.Estados = Enum('Estados', 'ocioso espera') 
		self.estado = self.Estados.ocioso
		self.TipoEvento = Enum('TipoEvento','payload quadro timeout')
		self.evento = None
		self.buf = bytearray()
		self.dado = bytearray()
		self.enq = enq
		self.n = 0 #controle envio
		self.m = 1 #controle recepção
		self.payload_recebido = bytearray()		

	def envia(self, dado):

		if (dado == bytearray()):
			return
		print('Tratando o seguinte payload: {}'.format(dado))
		self.evento = self.TipoEvento.payload
		self.dado = dado

		while(True):
			
			if (self._handle(self.evento) == self.Estados.ocioso):
				print('Payload tratado e enviado.')
				return
			else:
				#self.evento = self.TipoEvento.quadro
				print('Aguardando ACK.')
	def recebe(self):
		while(True):					
			
			tam, self.buf = self.enq.recebe()
			
			if (self.buf == bytearray()):
				continue #enquanto não receber um frame válido, tenta de novo

			print('Recebeu o seguinte frame: {}'.format(self.buf))

			self.evento = self.TipoEvento.quadro

			if (self._handle(self.evento) == self.Estados.ocioso):
				return len(self.buf), self.buf


	def _set_timeout(self, tout):
		pass


	def _handle(self, evento):
		print('Tratando estado {}'.format(self.estado))
		if (self.estado == self.Estados.ocioso):
			self.estado = self._func_ocioso(evento)
			print(self.estado)
			return self.estado
		else: #Estado de espera
			self.estado = self._func_espera(evento)
			return self.estado

	def _func_ocioso(self, evento):
		if (self.evento == self.TipoEvento.payload or self.evento == self.TipoEvento.timeout):
			
			if (self.n == 1):
				self.n = 0
			else:
				self.n = 1
			self._func_payload() #chama payload
			return self.Estados.espera
		elif (self.evento == self.TipoEvento.quadro):
			self._func_quadro()
			return self.estado


	def _func_espera(self, evento):
		if (evento == self.TipoEvento.payload): #se o evento é payload
			# aqui que deve dar timeout se não receber ack			
			tam, dado_recebido = self.recebe()			
			if (tam == 0):
				return self.Estados.espera
			self._remove_frame()
			if (self.buf ==  bytearray()):
				return self.Estados.ocioso
			return self.Estados.espera
		elif(evento == self.TipoEvento.quadro):
			if (self.buf ==  bytearray()):
				return self.Estados.ocioso
			return self._remove_frame()
		elif(evento == self.TipoEvento.timeout):
			return self.Estados.espera


	def _func_payload(self):

		dado = bytearray()
		controle = 0b00000000
		#if (self.n == self.m and self.n == 1):
		if (self.n == 1):
			controle = controle | 0b00001000

		proto = b'\x00'

		dado = dado + bytes([controle]) + proto + self.dado
		print('_func_payload enviando: {}'.format(dado))
		self.enq.envia(dado)

		return

	def _func_quadro(self):
		controle = self.buf[0]
		if (((controle & 0b10000000) >> 7) == 1): #quadro de ack
			if (((controle & 0b00001000) >> 3) == self.n):
				#cancela o timeout
				return self.Estados.ocioso
			else:
				self._func_payload()
				return self.Estados.espera
		else: #quadro de dados
			#if (((controle & 0b00001000) >> 3) == self.m):
			return self._remove_frame()
			#else:
				#remanda ACK
			#	self._ack()

			

	def _remove_frame(self):
		#print('Remove frame')
		#print(self.buf)
		controle = self.buf[0]
		if (((controle & 0b10000000) >> 7) == 0): #se for data (0 & 1 = 0)
			if (((controle & 0b00001000) >> 3) == self.m): #M
			 	#envia o ackM e manda payload para a app
				self.payload_recebido = self.buf[2:]
				self._ack(self.m)
				return self.estado 
			else: #!M (m barrado)
				#envia o ack!M
				self._ack(not self.m)
				return self.estado
		else: #se for ack
			if (((controle & 0b00001000) >> 3) == self.n): #se é o ack certo
				self.buf = bytearray()
				return self.Estados.ocioso #libera a app
			return self.Estados.espera
	
	def _ack(self, mEnvia):
		ack = bytearray()
		controle = 0b10000000
		if (mEnvia == 1):
			controle = controle | 0b00001000

		proto = b'\x00'

		ack = ack + bytes([controle]) + proto

		self.enq.envia(ack)
