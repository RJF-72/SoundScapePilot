import os
import uuid

base = "dist/SoundScapePilot/"
files = []
for root, dirs, fnames in os.walk(base):
    for f in fnames:
        full = os.path.join(root, f)
        rel = os.path.relpath(full, base)
        files.append((rel, full))

# Collect directories
dirs = set()
for rel, _ in files:
    d = os.path.dirname(rel)
    if d:
        parts = d.split(os.sep)
        acc = ""
        for p in parts:
            acc = os.path.join(acc, p) if acc else p
            dirs.add(acc)

# Sort by depth
sorted_dirs = sorted(dirs, key=lambda x: (x.count(os.sep), x))

lines = []
lines.append('<?xml version="1.0" encoding="UTF-8"?>')
lines.append('<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">')
lines.append('  <Product Id="*" Name="SoundScape Pilot" Language="1033" Version="1.0.0.0" Manufacturer="Redemption Road Music Group" UpgradeCode="a1b2c3d4-e5f6-7890-abcd-ef1234567890">')
lines.append('    <Package InstallerVersion="500" Compressed="yes" InstallScope="perMachine" />')
lines.append('    <MajorUpgrade DowngradeErrorMessage="A newer version of SoundScape Pilot is already installed." />')
lines.append('    <MediaTemplate EmbedCab="yes" />')
lines.append('    <Feature Id="ProductFeature" Title="SoundScape Pilot" Level="1">')
lines.append('      <ComponentGroupRef Id="ProductComponents" />')
lines.append('    </Feature>')
lines.append('    <UI>')
lines.append('      <UIRef Id="WixUI_Minimal" />')
lines.append('      <Publish Dialog="WelcomeDlg" Control="Next" Event="NewDialog" Value="InstallDirDlg">NOT Installed</Publish>')
lines.append('      <Publish Dialog="InstallDirDlg" Control="Back" Event="NewDialog" Value="WelcomeDlg">1</Publish>')
lines.append('      <Publish Dialog="InstallDirDlg" Control="Next" Event="InstallFiles">1</Publish>')
lines.append('      <Publish Dialog="ExitDialog" Control="Finish" Event="EndDialog" Value="Return">!IsInstalled AND NOT InstallCancel</Publish>')
lines.append('    </UI>')
lines.append('    <Property Id="WIXUI_INSTALLDIR" Value="INSTALLFOLDER" />')
lines.append('  </Product>')
lines.append('')
lines.append('  <Fragment>')
lines.append('    <Directory Id="TARGETDIR" Name="SourceDir">')
lines.append('      <Directory Id="ProgramFiles64Folder" Name="PFiles">')
lines.append('        <Directory Id="REDMPTIONROAD" Name="Redemption Road Music Group">')
lines.append('          <Directory Id="INSTALLFOLDER" Name="SoundScape Pilot">')

# Build directory tree with proper nesting
# Map each dir to its parent dir id
dir_info = {}  # relpath -> (name, parent_id)
for d in sorted_dirs:
    parts = d.split(os.sep)
    name = parts[-1]
    parent = os.sep.join(parts[:-1]) if len(parts) > 1 else None
    parent_id = "INSTALLFOLDER" if parent is None else "DIR_" + parent.replace("\\", "_").replace("/", "_").replace(".", "_").replace("-", "_")
    safe_id = "DIR_" + d.replace("\\", "_").replace("/", "_").replace(".", "_").replace("-", "_")
    dir_info[d] = (name, parent_id, safe_id)

# Output directories depth-first with proper nesting
# We need to open parent dirs before children. sorted_dirs is already sorted by depth.
open_stack = []  # list of (depth, safe_id)
for d in sorted_dirs:
    parts = d.split(os.sep)
    depth = len(parts)
    _, _, safe_id = dir_info[d]
    # Close dirs at same or deeper level
    while open_stack and open_stack[-1][0] >= depth:
        lines.append("          </Directory>")
        open_stack.pop()
    indent = " " * (10 + depth * 2)
    name = parts[-1]
    lines.append(f'{indent}<Directory Id="{safe_id}" Name="{name}">')
    open_stack.append((depth, safe_id))

# Close all remaining
while open_stack:
    lines.append("          </Directory>")
    open_stack.pop()

lines.append("          </Directory>")  # close INSTALLFOLDER
lines.append("        </Directory>")  # close REDMPTIONROAD
lines.append("      </Directory>")  # close ProgramFiles64Folder
lines.append('      <Directory Id="ProgramMenuFolder" Name="Programs">')
lines.append('        <Directory Id="APPSTARTMENU" Name="SoundScape Pilot" />')
lines.append('      </Directory>')
lines.append('      <Directory Id="DesktopFolder" Name="Desktop" />')
lines.append('    </Directory>')
lines.append('  </Fragment>')
lines.append('')
lines.append('  <Fragment>')
lines.append('    <ComponentGroup Id="ProductComponents">')

# Map dir relpath to safe_id
dir_id_map = {}
for d, (name, parent_id, safe_id) in dir_info.items():
    dir_id_map[d] = safe_id

i = 0
for rel, full in files:
    fileName = os.path.basename(rel)
    pdir = os.path.dirname(rel)
    compId = f"cmp_{i}"
    fileId = f"fil_{i}"
    dirRef = dir_id_map.get(pdir, "INSTALLFOLDER") if pdir else "INSTALLFOLDER"
    keypath = "yes" if fileName == "SoundScapePilot.exe" else "no"
    # Escape backslashes in source path for XML (WiX uses backslash path separators)
    source = f"dist/SoundScapePilot/{rel}".replace("/", "\\")
    lines.append(f'      <Component Id="{compId}" Directory="{dirRef}" Guid="{str(uuid.uuid4()).upper()}">')
    lines.append(f'        <File Id="{fileId}" Source="{source}" KeyPath="{keypath}" />')
    if fileName == "SoundScapePilot.exe":
        lines.append(f'        <Shortcut Id="shortcutStartMenu" Name="SoundScape Pilot" Description="SoundScape Pilot - Music Industry Command Center" Target="[#{fileId}]" WorkingDirectory="INSTALLFOLDER" Advertise="yes" />')
        lines.append('        <RemoveFolder Id="removeStartMenu" Directory="APPSTARTMENU" On="uninstall" />')
        lines.append(f'        <Shortcut Id="shortcutDesktop" Name="SoundScape Pilot" Description="SoundScape Pilot - Music Industry Command Center" Target="[#{fileId}]" WorkingDirectory="INSTALLFOLDER" />')
        lines.append('        <RemoveFolder Id="removeDesktop" Directory="DesktopFolder" On="uninstall" />')
        lines.append('        <RegistryValue Root="HKCU" Key="Software\\Redemption Road Music Group\\SoundScape Pilot" Name="installed" Type="integer" Value="1" KeyPath="yes" />')
    lines.append('        <CreateFolder />')
    lines.append('      </Component>')
    i += 1

lines.append('    </ComponentGroup>')
lines.append('  </Fragment>')
lines.append('</Wix>')

with open("titan7_installer.wxs", "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")

print(f"Generated titan7_installer.wxs with {len(files)} files")
