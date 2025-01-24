### What does this do?
It combs through Windows DNS Log Files and let's you know what is being queried and how many times. ( i.e. google.com)

### Requirements: 
DNS Logging Must be Enabled. 

Enable Debug Logging on the DNS server for this.

    Open DNS Manager from the Tools menu of Server Manager
    Right-click the DNS server in the left pane and click Properties
    Click the Debug Logging tab and check the Log packets for debugging checkbox
    To minimize the amount of data being logged, uncheck the following checkboxes:
        Packet direction - Outgoing
        Transport protocol - TCP
        Packet contents - Updates
        Packet type - Response
    In the Log file section, type a path and file name for the log. Alter the Maximum size (bytes) value if necessary.
    Click OK.
    
![image](https://github.com/user-attachments/assets/e6e9d63a-abc8-486c-8805-5ff2808e4d55)


 
Keep In Mind Directory Structure Needs of Scripts 
The Data that we are Analysing is in the last Position of the log entries, if yours differs, make the necessary changes.

### Howto:

COPY DNS LOGS From C:\DNS.log to RAWLogs

Run Step1.py Run Step2.sh Run Step3.sh Run Step4.sh

Happy Results
