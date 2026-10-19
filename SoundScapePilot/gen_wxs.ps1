$base = "dist\SoundScapePilot\"
$files = Get-ChildItem -Path $base -Recurse -File
$sb = New-Object System.Text.StringBuilder

# Collect unique nested directories (relative to base)
$dirTree = @{}
foreach ($f in $files) {
  $rel = $f.FullName.Substring($base.Length)
  $pdir = [System.IO.Path]::GetDirectoryName($rel)
  if ($pdir -and $pdir -ne ".") {
    $parts = $pdir -split "[\\\/]"
    $accum = ""
    foreach ($part in $parts) {
      $accum = if ($accum) { "$accum\$part" } else { $part }
      if (-not $dirTree.ContainsKey($accum)) {
        $dirTree[$accum] = [System.IO.Path]::GetFileName($accum)
      }
    }
  }
}
$sortedDirs = $dirTree.GetEnumerator() | Sort-Object { $_.Key.Split('\').Count }, { $_.Key }

[void]$sb.AppendLine("<?xml version=`"1.0`" encoding=`"UTF-8`?`">")
[void]$sb.AppendLine("<Wix xmlns=`"http://schemas.microsoft.com/wix/2006/wi`">")
[void]$sb.AppendLine("  <Product Id=`"*`" Name=`"SoundScape Pilot`" Language=`"1033`" Version=`"1.0.0.0`" Manufacturer=`"Redemption Road Music Group`" UpgradeCode=`"a1b2c3d4-e5f6-7890-abcd-ef1234567890`">")
[void]$sb.AppendLine("    <Package InstallerVersion=`"500`" Compressed=`"yes`" InstallScope=`"perMachine`" />")
[void]$sb.AppendLine("    <MajorUpgrade DowngradeErrorMessage=`"A newer version of SoundScape Pilot is already installed.`" />")
[void]$sb.AppendLine("    <MediaTemplate EmbedCab=`"yes`" />")
[void]$sb.AppendLine("    <Feature Id=`"ProductFeature`" Title=`"SoundScape Pilot`" Level=`"1`">")
[void]$sb.AppendLine("      <ComponentGroupRef Id=`"ProductComponents`" />")
[void]$sb.AppendLine("    </Feature>")
[void]$sb.AppendLine("    <UI>")
[void]$sb.AppendLine("      <UIRef Id=`"WixUI_Minimal`" />")
[void]$sb.AppendLine("      <Publish Dialog=`"WelcomeDlg`" Control=`"Next`" Event=`"NewDialog`" Value=`"InstallDirDlg`">NOT Installed</Publish>")
[void]$sb.AppendLine("      <Publish Dialog=`"InstallDirDlg`" Control=`"Back`" Event=`"NewDialog`" Value=`"WelcomeDlg`">1</Publish>")
[void]$sb.AppendLine("      <Publish Dialog=`"InstallDirDlg`" Control=`"Next`" Event=`"InstallFiles`">1</Publish>")
[void]$sb.AppendLine("      <Publish Dialog=`"ExitDialog`" Control=`"Finish`" Event=`"EndDialog`" Value=`"Return`">!IsInstalled AND NOT InstallCancel</Publish>")
[void]$sb.AppendLine("    </UI>")
[void]$sb.AppendLine("    <Property Id=`"WIXUI_INSTALLDIR`" Value=`"INSTALLFOLDER`" />")
[void]$sb.AppendLine("  </Product>")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("  <Fragment>")
[void]$sb.AppendLine("    <Directory Id=`"TARGETDIR`" Name=`"SourceDir`">")
[void]$sb.AppendLine("      <Directory Id=`"ProgramFiles64Folder`" Name=`"PFiles`">")
[void]$sb.AppendLine("        <Directory Id=`"REDMPTIONROAD`" Name=`"Redemption Road Music Group`">")
[void]$sb.AppendLine("          <Directory Id=`"INSTALLFOLDER`" Name=`"SoundScape Pilot`">")

$openStack = @()
foreach ($d in $sortedDirs) {
  $key = $d.Key
  $name = $d.Value
  $parts = $key -split "\\"
  $depth = $parts.Count
  $safeId = "DIR_$($key -replace '[\\\/ .-]', '_')"
  while ($openStack.Count -gt 0 -and $openStack[-1].Count -ge $depth) {
    [void]$sb.AppendLine("          </Directory>")
    $openStack = $openStack[0..($openStack.Count-2)]
  }
  $indent = " " * (10 + $depth * 2)
  [void]$sb.AppendLine("${indent}<Directory Id=`"$safeId`" Name=`"$name`">")
  $openStack += $parts
}
while ($openStack.Count -gt 0) {
  [void]$sb.AppendLine("          </Directory>")
  $openStack = $openStack[0..($openStack.Count-2)]
}
[void]$sb.AppendLine("          </Directory>")
[void]$sb.AppendLine("        </Directory>")
[void]$sb.AppendLine("      </Directory>")
[void]$sb.AppendLine("      <Directory Id=`"ProgramMenuFolder`" Name=`"Programs`">")
[void]$sb.AppendLine("        <Directory Id=`"APPSTARTMENU`" Name=`"SoundScape Pilot`" />")
[void]$sb.AppendLine("      </Directory>")
[void]$sb.AppendLine("      <Directory Id=`"DesktopFolder`" Name=`"Desktop`" />")
[void]$sb.AppendLine("    </Directory>")
[void]$sb.AppendLine("  </Fragment>")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("  <Fragment>")
[void]$sb.AppendLine("    <ComponentGroup Id=`"ProductComponents`">")
$i = 0
foreach ($f in $files) {
  $rel = $f.FullName.Substring($base.Length)
  $fileName = [System.IO.Path]::GetFileName($rel)
  $pdir = [System.IO.Path]::GetDirectoryName($rel)
  $compId = "cmp_$i"
  $fileId = "fil_$i"
  $dirRef = if ($pdir -and $pdir -ne ".") { "DIR_$($pdir -replace '[\\\/ .-]', '_')" } else { "INSTALLFOLDER" }
  $keypath = if ($fileName -eq "SoundScapePilot.exe") { "yes" } else { "no" }
  [void]$sb.AppendLine("      <Component Id=`"$compId`" Directory=`"$dirRef`" Guid=`"{$([guid]::NewGuid())}`">")
  [void]$sb.AppendLine("        <File Id=`"$fileId`" Source=`"$base$rel`" KeyPath=`"$keypath`" />")
  if ($fileName -eq "SoundScapePilot.exe") {
    [void]$sb.AppendLine("        <Shortcut Id=`"shortcutStartMenu`" Name=`"SoundScape Pilot`" Description=`"SoundScape Pilot - Music Industry Command Center`" Target=`"[#$fileId]`" WorkingDirectory=`"INSTALLFOLDER`" Advertise=`"yes`" />")
    [void]$sb.AppendLine("        <RemoveFolder Id=`"removeStartMenu`" Directory=`"APPSTARTMENU`" On=`"uninstall`" />")
    [void]$sb.AppendLine("        <Shortcut Id=`"shortcutDesktop`" Name=`"SoundScape Pilot`" Description=`"SoundScape Pilot - Music Industry Command Center`" Target=`"[#$fileId]`" WorkingDirectory=`"INSTALLFOLDER`" />")
    [void]$sb.AppendLine("        <RemoveFolder Id=`"removeDesktop`" Directory=`"DesktopFolder`" On=`"uninstall`" />")
    [void]$sb.AppendLine("        <RegistryValue Root=`"HKCU`" Key=`"Software\Redemption Road Music Group\SoundScape Pilot`" Name=`"installed`" Type=`"integer`" Value=`"1`" KeyPath=`"yes`" />")
  }
  [void]$sb.AppendLine("        <CreateFolder />")
  [void]$sb.AppendLine("      </Component>")
  $i++
}
[void]$sb.AppendLine("    </ComponentGroup>")
[void]$sb.AppendLine("  </Fragment>")
[void]$sb.AppendLine("</Wix>")
$sb.ToString() | Out-File -Encoding utf8 "soundscape_installer.wxs"
"Generated soundscape_installer.wxs with $($files.Count) files"
