import binascii
import struct
import pandas as pd
import sys

def read_shellcode(file_path):
    """Read shellcode from a binary file."""
    with open(file_path, 'rb') as f:
        return f.read()

def find_bad_chars_indices(shellcode, bad_chars):
    """Find indices of bad characters in the shellcode."""
    bad_chars_indices = []
    for index, byte in enumerate(shellcode):
        if byte in bad_chars:
            bad_chars_indices.append((index, byte))
    return bad_chars_indices

def generate_replacement_map(bad_chars, replacements):
    """Generate a map of bad characters to replacements."""
    if len(bad_chars) != len(replacements):
        raise ValueError("Number of bad characters must match number of replacements.")
    return {bad: rep for bad, rep in zip(bad_chars, replacements)}

def replace_bad_chars(shellcode, bad_chars, replacement_map):
    """Replace bad characters in the shellcode using a replacement map."""
    new_shellcode = bytearray(shellcode)
    bad_chars_indices = find_bad_chars_indices(shellcode, bad_chars)
    
    replacement_records = []
    for index, bad_char in bad_chars_indices:
        new_shellcode[index] = replacement_map[bad_char]
        replacement_records.append((index, bad_char, replacement_map[bad_char]))
    
    return new_shellcode, replacement_records

def format_shellcode(shellcode):
    """Format the shellcode in \\x format."""
    return ''.join(f'\\x{byte:02x}' for byte in shellcode)

def shift_payload(shellcode, shift):
    """Shift entire payload by a specified number of bytes."""
    shifted_shellcode = bytearray(shellcode)
    for i in range(len(shellcode)):
        shifted_shellcode[i] = (shifted_shellcode[i] + shift) % 256
    return shifted_shellcode

def ror(byte, count):
    """Rotate right (ROR) operation on a byte."""
    return ((byte >> count) | (byte << (8 - count))) & 0xFF

def shl(byte, count):
    """Shift left (SHL) operation on a byte."""
    return (byte << count) & 0xFF

def xor(byte, value):
    """XOR operation on a byte."""
    return byte ^ value

def and_op(byte, value):
    """AND operation on a byte."""
    return byte & value

def or_op(byte, value):
    """OR operation on a byte."""
    return byte | value

def not_op(byte):
    """NOT operation on a byte."""
    return ~byte & 0xFF

def apply_bitwise_operations(shellcode):
    """Apply bitwise operations to the shellcode."""
    ror_shellcode = bytearray(shellcode)
    shl_shellcode = bytearray(shellcode)
    xor_shellcode = bytearray(shellcode)
    and_shellcode = bytearray(shellcode)
    or_shellcode = bytearray(shellcode)
    not_shellcode = bytearray(shellcode)
    
    for i in range(len(shellcode)):
        ror_shellcode[i] = ror(ror_shellcode[i], 1)
        shl_shellcode[i] = shl(shl_shellcode[i], 1)
        xor_shellcode[i] = xor(xor_shellcode[i], 0xFF) #  XOR with 0xFF
        and_shellcode[i] = and_op(and_shellcode[i], 0x7F) # AND with 0x7F
        or_shellcode[i] = or_op(or_shellcode[i], 0x80) #  OR with 0x80
        not_shellcode[i] = not_op(not_shellcode[i])
    
    return {
        "ROR": ror_shellcode,
        "SHL": shl_shellcode,
        "XOR": xor_shellcode,
        "AND": and_shellcode,
        "OR": or_shellcode,
        "NOT": not_shellcode
    }

def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <shellcode.bin>")
        return

    shellcode_file = sys.argv[1]
    shellcode = read_shellcode(shellcode_file)

    # Example bad characters and replacements
    bad_chars = [0x00, 0x0a, 0x11, 0x20, 0x21, 0x22, 0x28, 0x80, 0x81]
    replacements = [0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98]

    replacement_map = generate_replacement_map(bad_chars, replacements)
    new_shellcode, replacement_records = replace_bad_chars(shellcode, bad_chars, replacement_map)

   
    shifted_shellcode = shift_payload(shellcode, 1)

    
    bitwise_shellcodes = apply_bitwise_operations(shellcode)

    # Print the replacement map and new shellcode
    print("Bad Characters Replacement Map:")
    for bad_char, replacement in replacement_map.items():
        print(f'\\x{bad_char:02x} -> \\x{replacement:02x}')

    print("\nOriginal Shellcode:")
    print(format_shellcode(shellcode))

    print("\nNew Shellcode (Replaced Bad Characters):")
    print(format_shellcode(new_shellcode))

    print("\nShifted Shellcode (+1):")
    print(format_shellcode(shifted_shellcode))

   
    for op_name, op_shellcode in bitwise_shellcodes.items():
        print(f"\n{op_name} Shellcode:")
        print(format_shellcode(op_shellcode))

    
    df = pd.DataFrame(replacement_records, columns=['Index', 'Original Bad Char', 'Replaced Char'])
    df['Original Bad Char'] = df['Original Bad Char'].apply(lambda x: f'\\x{x:02x}')
    df['Replaced Char'] = df['Replaced Char'].apply(lambda x: f'\\x{x:02x}')
    
    print("\nBad Characters Indices and Replacements:")
    print(df.to_string(index=False))

if __name__ == "__main__":
    main()
