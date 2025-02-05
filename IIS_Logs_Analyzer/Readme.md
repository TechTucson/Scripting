# What is this?
- The purpose of this collection of scripts is to help you analyze what endpoints (applications or directories) are being used. The end goal is to determine what is really used, what is rarely used, and eventually what can I throw away. We've all collected servers, applications, computers, and books it's sometimes difficult to let go, especially if we don't know if it's being used.
  

# Requirements:
- Keep In Mind Directory Structure Needs of Scripts
 - There is a *RAWLogs* Directory which is important, and the rest of the folder structure can be set using the current path. (./)  
- Within the logs the data that we are Analysing is in Position 7, if yours differs, make the necessary changes. 

# Howto: 

- COPY IIS LOGS From %SystemDrive%\inetpub\logs\LogFiles to RAWLogs

- Run Step1.py
  - This step removes the first four lines of all of the files within the RAWLogs directory as these do not contain logs.  
- Run Step2.py
  -  This step takes the 7th Column of all of the files within the RAWLogs Directory and exports the content to Output.txt 
- Run Step3.sh
  -  This step accounts for endpoints that are multiple levels deep (i.e. **Level1/Level2/Level3**) We take evertyhing from the first column back. In our example we just keep **Level1**
  -   ``` cut -d'/' -f1-2 Output.txt >  Output2.txt ```
- Run Step4.sh
  -  This step analyzes the Output2.txt file using the sort command. Counts the entries and sorts them from highest to lowest.
    - sort Output2.txt | uniq -c | sort -nr > Analyzed.txt   

#### Happy Results




