# Python script to generate bond_strength_map.csv and color_map.json
# This will be run locally and its output will be copied to the respective files.

import csv
import json

# --- Helper Functions for LHA Metrics (Simplified for mapping 1-1000) ---
def get_prime_factors(n):
    factors = {}
    d = 2
    tempN = n
    while d * d <= tempN:
        while tempN % d == 0:
            # Corrected syntax: use 'or' and proper dictionary assignment
            factors[d] = (factors.get(d, 0) + 1)
            tempN /= d
        d += 1
    if tempN > 1:
        # Corrected syntax: use 'or' and proper dictionary assignment
        factors[tempN] = (factors.get(tempN, 0) + 1)
    return factors

def calculate_bond_strength(n):
    if n <= 1: return 0
    factors_dict = get_prime_factors(n)
    unique_prime_factors = list(factors_dict.keys())
    
    bond_score = sum(unique_prime_factors) # Sum of unique prime factors
    bond_score += sum(factors_dict.values()) # Sum of exponents

    # Simple bonus for composite numbers (more "bonds")
    if len(unique_prime_factors) > 1 or (len(unique_prime_factors) == 1 and factors_dict[unique_prime_factors[0]] > 1):
        bond_score *= 1.1 # Small bonus for being composite

    # Add a bonus for numbers with many divisors (high "connectivity")
    num_divisors = 1
    for p in factors_dict:
        num_divisors *= (factors_dict[p] + 1)
    bond_score += (num_divisors * 0.5) # Bonus based on number of divisors

    # Normalize roughly for 1-1000 range to get a reasonable scale
    return bond_score * 0.5 + 5 # Adjust scale to make values more distinct

def hsl_to_rgb(h, s, l):
    # Converts HSL color to RGB (0-255)
    # h: hue [0, 360), s: saturation [0, 1], l: lightness [0, 1]
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    
    r, g, b = 0, 0, 0
    if 0 <= h < 60:
        r, g, b = c, x, 0
    elif 60 <= h < 120:
        r, g, b = x, c, 0
    elif 120 <= h < 180:
        r, g, b = 0, c, x
    elif 180 <= h < 240:
        r, g, b = 0, x, c
    elif 240 <= h < 300:
        r, g, b = x, 0, c
    elif 300 <= h < 360:
        r, g, b = c, 0, x
        
    r = round((r + m) * 255)
    g = round((g + m) * 255)
    b = round((b + m) * 255)
    
    return (r, g, b)

# --- Generate bond_strength_map.csv ---
csv_data = []
header = ["number", "bond_strength", "r", "g", "b"]
csv_data.append(header)

# Determine the min/max bond strengths for normalization
min_bs = float('inf')
max_bs = float('-inf')
all_bs = []
for n in range(1, 1001):
    bs = calculate_bond_strength(n)
    all_bs.append(bs)
    if bs < min_bs: min_bs = bs
    if bs > max_bs: max_bs = bs

# Generate data for CSV
for n in range(1, 1001):
    bs = calculate_bond_strength(n)
    
    # Normalize Bond Strength to a 0-1 range for color mapping
    normalized_bs = (bs - min_bs) / (max_bs - min_bs) if (max_bs - min_bs) > 0 else 0
    
    # Map normalized_bs to a hue (e.g., blue to red spectrum)
    # Hue: 240 (blue) to 0 (red) for increasing BS
    hue = (1 - normalized_bs) * 240 
    
    # Saturation and Lightness for a vibrant spectrum
    saturation = 0.9 # High saturation
    lightness = 0.5 # Medium lightness

    r, g, b = hsl_to_rgb(hue, saturation, lightness)
    
    csv_data.append([n, round(bs, 2), r, g, b])

# --- Generate color_map.json ---
color_map_data = {
    "description": "Harmonic Spectrum Pulse: Bond Strength mapped to a continuous HSL spectrum (blue to red) with implicit pulse modulation.",
    "color_logic_type": "Harmonic Spectrum Pulse",
    "spectrum_mapping": {
        "bond_strength_range": [round(min_bs, 2), round(max_bs, 2)],
        "hue_range": [240, 0], # Blue (240) to Red (0)
        "saturation": 0.9,
        "lightness": 0.5
    },
    "pulse_modulation_notes": "The 'pulse' aspect is implemented in the firmware (cube_controller.ino) by dynamically adjusting intensity or saturation based on secondary numerical properties (e.g., number of unique prime factors, digit sum parity) and a time-based oscillation, creating a living, breathing light effect."
}

# --- Output to files (for manual copy-paste) ---
# For bond_strength_map.csv
csv_output = ""
for row in csv_data:
    csv_output += ",".join(map(str, row)) + "\n"

print("--- bond_strength_map.csv CONTENT ---")
print(csv_output)
print("--- END bond_strength_map.csv CONTENT ---")

# For color_map.json
json_output = json.dumps(color_map_data, indent=2)
print("\n--- color_map.json CONTENT ---")
print(json_output)
print("--- END color_map.json CONTENT ---")

