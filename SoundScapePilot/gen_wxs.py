import os
import uuid

base = "dist/SoundScapePilot/"
files = []
for root, dirs, fnames in os.walk(base):
    for f in sorted(fnames):
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

sorted_dirs = sorted(dirs, key=lambda x: tuple(x.split(os.sep)))

def safe_id(name):
    return "DIR_" + name.replace("\\", "_").replace("/", "_").replace(".", "_").replace("-", "_")

# Map dir relpath to (name, parent_id, safe_id)
dir_info = {}
for d in sorted_dirs:
    parts = d.split(os.sep)
    name = parts[-1]
    parent = os.sep.join(parts[:-1]) if len(parts) > 1 else None
    parent_id = "INSTALLFOLDER" if parent is None else safe_id(parent)
    dir_info[d] = (name, parent_id, safe_id(d))

lines = []
lines.append('<?xml version="1.0" encoding="UTF-8"?>')
lines.append('<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">')
lines.append('  <Product Id="*" Name="SoundScape Pilot" Language="1033" Version="1.0.0.0" Manufacturer="Redemption Road Music Group" UpgradeCode="a1b2c3d4-e5f6-7890-abcd-ef1234567890">')
lines.append('    <Package InstallerVersion="500" Compressed="yes" InstallScope="perUser" Platform="x64" />')
lines.append('    <MajorUpgrade AllowSameVersionUpgrades="yes" DowngradeErrorMessage="A newer version of SoundScape Pilot is already installed." />')
lines.append('    <MediaTemplate EmbedCab="yes" />')
lines.append('    <Feature Id="ProductFeature" Title="SoundScape Pilot" Level="1">')
lines.append('      <ComponentGroupRef Id="ProductComponents" />')
lines.append('    </Feature>')
lines.append('    <UI>')
lines.append('      <UIRef Id="WixUI_Minimal" />')
lines.append('      <Publish Dialog="WelcomeDlg" Control="Next" Event="NewDialog" Value="InstallDirDlg">NOT Installed</Publish>')
lines.append('      <Publish Dialog="InstallDirDlg" Control="Back" Event="NewDialog" Value="WelcomeDlg">1</Publish>')
lines.append('      <Publish Dialog="InstallDirDlg" Control="Next" Event="NewDialog" Value="VerifyReadyDlg">1</Publish>')
lines.append('      <Publish Dialog="InstallDirDlg" Control="ChangeFolder" Property="WIXUI_INSTALLDIR">1</Publish>')
lines.append('    </UI>')
lines.append('    <Property Id="WIXUI_INSTALLDIR" Value="INSTALLFOLDER" />')
lines.append('    <Icon Id="appicon.ico" SourceFile="logo.ico" />')
lines.append('    <Property Id="ARPPRODUCTICON" Value="appicon.ico" />')
lines.append('  </Product>')
lines.append('')
lines.append('  <Fragment>')
lines.append('    <Directory Id="TARGETDIR" Name="SourceDir">')
lines.append('      <Directory Id="AppDataFolder" Name="AppData">')
lines.append('        <Directory Id="REDMPTIONROAD" Name="Redemption Road Music Group">')
lines.append('          <Directory Id="INSTALLFOLDER" Name="SoundScape Pilot">')

# Output directories with proper nesting (stack of directory paths)
open_stack = []
for d in sorted_dirs:
    parts = d.split(os.sep)
    depth = len(parts)
    _, _, safe_id_val = dir_info[d]
    parent = os.sep.join(parts[:-1]) if depth > 1 else None
    while open_stack and (parent is None or open_stack[-1] != parent):
        lines.append("          </Directory>")
        open_stack.pop()
    if depth == 1:
        while open_stack:
            lines.append("          </Directory>")
            open_stack.pop()
    indent = " " * (10 + depth * 2)
    name = parts[-1]
    lines.append(f'{indent}<Directory Id="{safe_id_val}" Name="{name}">')
    open_stack.append(d)

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

dir_id_map = {}
for d, (name, parent_id, safe_id_val) in dir_info.items():
    dir_id_map[d] = safe_id_val

i = 0
for rel, full in files:
    # Skip duplicate license files in dist-info licenses dirs (ICE30)
    if "\\licenses\\" in rel.replace("/", "\\") or rel.endswith("\\licenses\\"):
        continue
    fileName = os.path.basename(rel)
    pdir = os.path.dirname(rel)
    compId = f"cmp_{i}"
    fileId = f"fil_{i}"
    dirRef = dir_id_map.get(pdir, "INSTALLFOLDER") if pdir else "INSTALLFOLDER"
    keypath = "yes" if fileName == "SoundScapePilot.exe" else "no"
    source = f"dist/SoundScapePilot/{rel}".replace("/", "\\")
    new_guid = str(uuid.uuid4()).upper()
    lines.append(f'      <Component Id="{compId}" Directory="{dirRef}" Guid="{{{new_guid}}}">')
    lines.append(f'        <File Id="{fileId}" Source="{source}" KeyPath="{keypath}" />')
    if fileName == "SoundScapePilot.exe":
        lines.append('        <CreateFolder />')
        lines.append(f'      </Component>')
        # Start Menu shortcut component
        lines.append(f'      <Component Id="cmp_shortcut_menu" Directory="APPSTARTMENU" Guid="{{{str(uuid.uuid4()).upper()}}}">')
        lines.append(f'        <Shortcut Id="shortcutStartMenu" Name="SoundScape Pilot" Description="SoundScape Pilot - Music Industry Command Center" Target="[#{fileId}]" WorkingDirectory="INSTALLFOLDER" Icon="appicon.ico" />')
        lines.append('        <RemoveFolder Id="removeStartMenu" Directory="APPSTARTMENU" On="uninstall" />')
        lines.append('        <RegistryValue Root="HKCU" Key="Software\\Redemption Road Music Group\\SoundScape Pilot" Name="startMenuShortcut" Type="integer" Value="1" KeyPath="yes" />')
        lines.append('      </Component>')
        # Desktop shortcut component
        lines.append(f'      <Component Id="cmp_shortcut_desktop" Directory="DesktopFolder" Guid="{{{str(uuid.uuid4()).upper()}}}">')
        lines.append(f'        <Shortcut Id="shortcutDesktop" Name="SoundScape Pilot" Description="SoundScape Pilot - Music Industry Command Center" Target="[#{fileId}]" WorkingDirectory="INSTALLFOLDER" Icon="appicon.ico" />')
        lines.append('        <RegistryValue Root="HKCU" Key="Software\\Redemption Road Music Group\\SoundScape Pilot" Name="desktopShortcut" Type="integer" Value="1" KeyPath="yes" />')
        lines.append('      </Component>')
        i += 1
        continue
    lines.append('        <CreateFolder />')
    lines.append('      </Component>')
    i += 1

lines.append('    </ComponentGroup>')
lines.append('  </Fragment>')
lines.append('</Wix>')

with open("soundscape_installer.wxs", "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")

print(f"Generated soundscape_installer.wxs with {len(files)} files")
