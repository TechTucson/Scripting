#Remote scriptPath Value 
 
Import-module ActiveDirectory  
Get-ADUser -Filter * -SearchBase "OU=User Accounts,DC=santhosh,DC=lab" | Set-ADUser -Clear scriptPath 
 
#Update or set scriptPath Value  
 
 
Import-module ActiveDirectory  
Get-ADUser -Filter * -SearchBase "OU=User Accounts,DC=santhosh,DC=lab" | Set-ADUser –scriptPath “\\San01\test.bat” 
