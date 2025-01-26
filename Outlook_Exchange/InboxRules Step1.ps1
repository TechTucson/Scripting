<#  
 .SYNOPSIS  
     
    The scripts used to get the user who is forwarding or redirecting their email to external 
 
 .DESCRIPTION  
 
   In Some organization its prohibited to forward the email to external. 
   The script check entire organization and provide users list who has forward rule Enabled with Rule details 
    
 
.EXAMPLES 
 
 .\PowerShell_Script_InboxRule_forwarding_external.ps1 
 
        
 
 .NOTES  
    Author  : Kamaraj Ulaganathan 
    Email: kamaraj0926@outlook.com  
    Requires: PowerShell Version 2.0 
 
    #>   
     
     
 
 
$orgmailbox = Get-Mailbox  -ResultSize unlimited 
 
$count = $orgmailbox.count 
 
Write-Host " Total Mailbox count(in a org or from file): $Count" 
 
$output = @() 
 
foreach ($mailbox in $orgmailbox) 
 
{ 
 
$rules = Get-InboxRule -mailbox $mailbox -ErrorAction:SilentlyContinue | where{($_.forwardto -ne $null) -or ($_.redirectto -ne $null) -or ($_.ForwardAsAttachmentTo -ne $null) -and ($_.ForwardTo -notmatch "EX:/") -and ($_.RedirectTo -notmatch "EX:/") -and ($_.ForwardAsAttachmentTo -notmatch "EX:/")} 
$ident = Get-Mailbox -identity $mailbox |select Identity
$result = $rules | Select @{n="user";e={$Mailbox}},@{n="Rule Name";e={$_.name}},Enabled,@{Name="ForwardTo";Expression={[string]::join(";",($_.forwardTo))}},@{Name="RedirectTo";Expression={[string]::join(";",($_.redirectTo))}},@{Name="ForwardAsAttachmentTo";Expression={[string]::join(";",($_.ForwardAsAttachmentTo))}}
 
$output +=$result
Write-Host "." -NoNewline # To Show Progress..... 
 
} 
 
$output | Export-CSV c:\temp\scripts\inboxrilesstep1.csv  
 
Invoke-Expression c:\temp\scripts\inboxrilesstep1.csv 
