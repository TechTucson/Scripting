Get-AdUser -Filter * -Properties * | Foreach {
   Write-Host "- " $_.Name
   if ($_.HomeDrive -ne $null) {
    Write-Host -NoNewline "|-  Current home:" $_.HomeDrive "->" $_.HomeDirectory": removing... "
    Set-AdUser -Identity $_.DistinguishedName -HomeDirectory $null -HomeDrive $null
    Write-Host "Done."
   }
}
