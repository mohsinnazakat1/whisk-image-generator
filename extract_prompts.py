import re
import json

def extract_visual_prompts_from_file(filename):
    """
    Reads a text file and extracts all visual prompt strings from 'text' arrays
    Saves the result to an output JSON file
    """
    try:
        # Read the file content
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Extract visual prompts using regex
        pattern = r'text\s*\[\s*((?:"(?:[^"\\]|\\.)*"(?:\s*,\s*)?)*)\s*\]'
        matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
        
        all_strings = []
        
        for match in matches:
            strings_text = match.strip()
            if strings_text:
                # Extract individual quoted strings
                string_pattern = r'"((?:[^"\\]|\\.)*)"'
                individual_strings = re.findall(string_pattern, strings_text)
                
                for s in individual_strings:
                    if s.strip():
                        # Clean up escape sequences
                        cleaned_string = s.replace('\\"', '"').replace('\\\\', '\\')
                        all_strings.append(cleaned_string.strip())
        
        # Save to output file
        output_filename = "visual_prompts_output.json"
        with open(output_filename, 'w', encoding='utf-8') as outfile:
            json.dump(all_strings, outfile, indent=2, ensure_ascii=False)
        
        print(f"✅ Successfully extracted {len(all_strings)} visual prompts")
        print(f"✅ Saved to '{output_filename}'")
        
        return all_strings
        
    except FileNotFoundError:
        print(f"❌ Error: File '{filename}' not found.")
        return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def extract_visual_prompts_from_string(content, output_filename="visual_prompts_output.json"):
    """
    Alternative version that takes string content directly
    """
    pattern = r'text\s*\[\s*((?:"(?:[^"\\]|\\.)*"(?:\s*,\s*)?)*)\s*\]'
    matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
    
    all_strings = []
    
    for match in matches:
        strings_text = match.strip()
        if strings_text:
            string_pattern = r'"((?:[^"\\]|\\.)*)"'
            individual_strings = re.findall(string_pattern, strings_text)
            
            for s in individual_strings:
                if s.strip():
                    cleaned_string = s.replace('\\"', '"').replace('\\\\', '\\')
                    all_strings.append(cleaned_string.strip())
    
    # Save to output file
    with open(output_filename, 'w', encoding='utf-8') as outfile:
        json.dump(all_strings, outfile, indent=2, ensure_ascii=False)
    
    print(f"✅ Successfully extracted {len(all_strings)} visual prompts")
    print(f"✅ Saved to '{output_filename}'")
    
    return all_strings

# Main execution
def main():
    # Method 1: Read from file
    filename = "paste.txt"
    visual_prompts = extract_visual_prompts_from_file(filename)
    
    # Display first few examples for verification
    if visual_prompts:
        print(f"\n📋 First 3 examples:")
        for i, prompt in enumerate(visual_prompts[:3]):
            print(f"[{i}]: {prompt[:100]}...")
    
    return visual_prompts

if __name__ == "__main__":
    # Run the extraction
    prompts_array = main()
