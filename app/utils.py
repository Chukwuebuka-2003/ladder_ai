import random
import string

def generate_otp(length=6):
    """
    Return a numeric one-time password (OTP) string.
    
    Parameters:
        length (int): Number of digits to generate (default 6). Must be a non-negative integer.
    
    Returns:
        str: A string of exactly `length` random digits (0–9).
    """
    return ''.join(random.choices(string.digits, k=length))
