import os
#This deletes the first # lines of all files.. This is not log data
# Specify the directory containing your files
directory = './RAWLogs'

# Loop through all files in the directory
for filename in os.listdir(directory):
    file_path = os.path.join(directory, filename)

    # Check if it's a file (not a subdirectory)
    if os.path.isfile(file_path):
        with open(file_path, 'r') as file:
            lines = file.readlines()

        # Remove the first 3 lines
        lines = lines[4:]

        # Write the remaining lines back to the file
        with open(file_path, 'w') as file:
            file.writelines(lines)

        print(f'Processed {filename}')
