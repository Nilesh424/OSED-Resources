def calculate_xor_value(target, given_value):
    x = target ^ given_value
    return x


def calculate_or_value(target, given_value):
    
    x = target | given_value
    return x
# Example usage
target = 0x0 
given_value = 0x562AF351
#or eax, 0x631052B4 
result = calculate_xor_value(target, given_value)
result2 = calculate_or_value(target,given_value)
print(f"The value to XOR with {hex(given_value)} to get {target} is: {hex(result)}")
print(f"The value to OR with {hex(given_value)} to get {target} is: {hex(result2)}")

