import os
import subprocess
# This gets the Column We need which is the 7th Column, from all of the Files and Creates the SVC2.txt File
# Specify the directory containing your files
directory = 'RAWLogs'
output_file = '/home/mario/Downloads/Analysis/Output.txt'

# Open the output file in append mode
with open(output_file, 'a') as out_file:
    # Loop through all files in the directory
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)

        # Check if it's a file (not a subdirectory)
        if os.path.isfile(file_path):
            # Run the 'cut' command using subprocess
            try:
                result = subprocess.run(
                    ['cut', '-d', ' ', '-f', '7', file_path],
                    text=True, capture_output=True, check=True
                )
                # Append the result to the output file
                out_file.write(result.stdout)
                print(f'Processed {filename}')
            except subprocess.CalledProcessError as e:
                print(f"Error processing {filename}: {e}")
