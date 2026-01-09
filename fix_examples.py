#!/usr/bin/env python3
"""
Script to fix power connection pin syntax in all DeMoL example files.
Changes from: board_pin -- peripheral_pin
To: peripheral_pin -- board_pin
"""

import re
import sys
from pathlib import Path

def fix_power_connections(content):
    """Fix power connection syntax by swapping pin order."""
    lines = content.split('\n')
    result = []
    in_power_block = False
    
    for line in lines:
        # Check if we're entering a POWER block
        if re.match(r'\s*POWER\s*$', line):
            in_power_block = True
            result.append(line)
            continue
        
        # Check if we're leaving POWER block (DATA, @, or empty line after connections)
        if in_power_block and (re.match(r'\s*DATA\s', line) or re.match(r'\s*@', line) or re.match(r'\s*;\s*$', line)):
            in_power_block = False
            result.append(line)
            continue
        
        # If we're in a POWER block, swap the pins
        if in_power_block:
            # Match pattern: whitespace pin1 -- pin2 optional_comma
            match = re.match(r'(\s+)(\w+)\s+--\s+(\w+)(,?)(.*)$', line)
            if match:
                indent, pin1, pin2, comma, rest = match.groups()
                # Swap pin1 and pin2
                fixed_line = f"{indent}{pin2} -- {pin1}{comma}{rest}"
                result.append(fixed_line)
                continue
        
        result.append(line)
    
    return '\n'.join(result)

def main():
    # Find all .dev files in examples/rpi
    rpi_dir = Path('examples/rpi')
    dev_files = list(rpi_dir.glob('*.dev'))
    
    print(f"Found {len(dev_files)} .dev files in {rpi_dir}")
    
    for dev_file in sorted(dev_files):
        print(f"\nProcessing {dev_file}...")
        
        # Read the file
        content = dev_file.read_text()
        
        # Fix the content
        fixed_content = fix_power_connections(content)
        
        # Only write if changed
        if content != fixed_content:
            dev_file.write_text(fixed_content)
            print(f"  ✓ Fixed {dev_file}")
        else:
            print(f"  - No changes needed for {dev_file}")

if __name__ == '__main__':
    main()
