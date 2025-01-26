
##POWERSHELL: LIST ALL MAILBOX FOLDER DELEGATE ACCESS FOR A MAILBOX
$ErrorActionPreference="SilentlyContinue"
Stop-Transcript | out-null
$ErrorActionPreference = "Continue"
Start-Transcript -path C:\users\__amariouribe\desktop\output.txt -append

$mbx = "sgoldschmid"
$permissions = @()
$Folders = Get-MailboxFolderStatistics $mbx | % {$_.folderpath} | % {$_.replace(“/”,”\”)}
$list = ForEach ($F in $Folders)
   {
    $FolderKey = $mbx + ":" + $F
    $Permissions += Get-MailboxFolderPermission -identity $FolderKey -ErrorAction SilentlyContinue | Where-Object {$_.User -notlike “Default” -and $_.User -notlike “Anonymous” -and $_.AccessRights -notlike “None”}
   }
$permissions

# Do some stuff
Stop-Transcript
