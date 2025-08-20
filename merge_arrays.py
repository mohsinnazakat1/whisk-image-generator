import json

def merge_arrays_from_file(input_file, output_file):
    # Read the input file
    with open(input_file, 'r') as f:
        content = f.read()
    
    # Split the content by empty lines to separate arrays
    array_texts = content.split('\n\n\n')
    
    # Parse each array from JSON format
    arrays = []
    for array_text in array_texts:
        if array_text.strip():  # Skip empty strings
            try:
                array = json.loads(array_text)
                arrays.extend(array)  # Extend the list with elements from each array
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
    
    # Write the merged array to output file
    with open(output_file, 'w') as f:
        json.dump(arrays, f, indent=2)
    
    print(f"Successfully merged {len(arrays)} elements into {output_file}")

# Execute the merge
merge_arrays_from_file('input.txt', 'merged_output.json')
