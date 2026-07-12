"""Pełny lokalny raport System, zgodny zakresem z EvidLockV2."""
from __future__ import annotations
import csv, datetime as dt, getpass, json, os, platform, socket, subprocess
from pathlib import Path
from .. import APP_NAME, APP_VERSION, reports
from ..config import REPORTS_DIR
from ..winapi import is_admin

NO_DATA = "Brak danych"

def _valid_product_key(value):
    import re
    return bool(re.fullmatch(r"[A-Z0-9]{5}(?:-[A-Z0-9]{5}){4}",str(value or "").strip().upper()))

def _decode_product_id(value):
    try: data=bytearray(value)
    except Exception: return ""
    if len(data)<67: return ""
    alphabet="BCDFGHJKMPQRTVWXY2346789"; key=list(data[52:67]); result=[]
    for _ in range(25):
        rest=0
        for pos in range(14,-1,-1):
            rest=(rest*256)^key[pos]; key[pos]=rest//24; rest%=24
        result.insert(0,alphabet[rest])
    decoded="-".join("".join(result[i:i+5]) for i in range(0,25,5))
    return decoded if _valid_product_key(decoded) else ""

def _full_windows_product_key():
    candidates=[]
    firmware=_ps("(Get-CimInstance SoftwareLicensingService).OA3xOriginalProductKey",10).strip()
    if _valid_product_key(firmware): candidates.append((firmware.upper(),"OA3xOriginalProductKey / firmware OEM"))
    try:
        import winreg
        path=r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,path) as key:
            for name in ("BackupProductKeyDefault","DigitalProductId","DigitalProductId4"):
                try: value,_=winreg.QueryValueEx(key,name)
                except OSError: continue
                decoded=str(value).strip().upper() if name=="BackupProductKeyDefault" else _decode_product_id(value)
                if _valid_product_key(decoded): candidates.append((decoded,name))
    except Exception: pass
    return candidates[0] if candidates else (NO_DATA,"System nie udostępnił klucza w firmware ani rejestrze Windows")

def _run(args, timeout=20):
    try:
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        return (p.stdout or p.stderr or NO_DATA).strip()
    except Exception as exc: return f"Brak danych: {exc}"

def _ps(code, timeout=25):
    return _run(["powershell.exe","-NoProfile","-NonInteractive","-ExecutionPolicy","Bypass","-Command","$ProgressPreference='SilentlyContinue';$ErrorActionPreference='SilentlyContinue';"+code],timeout)

def _table(code, limit=100, timeout=25):
    return _ps(f"@({code})|Select-Object -First {limit}|Format-Table -AutoSize|Out-String -Width 260",timeout)

def _list(code, limit=10, timeout=20):
    return _ps(f"@({code})|Select-Object -First {limit}|Format-List|Out-String -Width 260",timeout)

def _paths(path, pattern="*", recursive=False, limit=25):
    try:
        found=list(path.rglob(pattern) if recursive else path.glob(pattern))
        return f"Ścieżka: {path}\nLiczba: {len(found)}\n"+"\n".join(f"{p} | {dt.datetime.fromtimestamp(p.stat().st_mtime):%Y-%m-%d %H:%M:%S} | {p.stat().st_size} B" for p in found[:limit])
    except Exception as exc: return f"{path}: {exc}"

def collect_system_data(progress=None):
    def step(n,text):
        if progress: progress(n * 100,text)
    step(.03,"Windows, komputer i domena")
    product_key,product_key_source=_full_windows_product_key()
    data=[
      ("Windows",[("Wersja i edycja",_list("Get-ComputerInfo|Select WindowsProductName,WindowsEditionId,WindowsDisplayVersion,WindowsVersion,OsBuildNumber,OsArchitecture,OsInstallDate,OsLastBootUpTime,TimeZone",1)),("Licencja",_list("Get-CimInstance SoftwareLicensingProduct|? {$_.PartialProductKey -and $_.Name -match 'Windows'}|Sort LicenseStatus -Descending|Select -First 1 Name,Description,LicenseStatus,PartialProductKey,ProductKeyChannel",1)),("Pełny klucz produktu Windows",product_key),("Źródło pełnego klucza",product_key_source)]),
      ("Komputer i domena",[("Komputer",socket.gethostname()),("FQDN",socket.getfqdn()),("Użytkownik",getpass.getuser()),("Domena",os.getenv("USERDNSDOMAIN") or os.getenv("USERDOMAIN") or NO_DATA),("Administrator","Tak" if is_admin() else "Nie")])]
    step(.12,"Procesor, pamięć i sprzęt")
    data += [
      ("Procesor",[("CPU",_list("Get-CimInstance Win32_Processor|Select Name,Manufacturer,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed,ProcessorId",4)),("Architektura",platform.machine())]),
      ("Pamięć",[("RAM",_table("Get-CimInstance Win32_PhysicalMemory|Select BankLabel,Manufacturer,PartNumber,SerialNumber,Capacity,Speed",32)),("Stan",_list("Get-CimInstance Win32_OperatingSystem|Select TotalVisibleMemorySize,FreePhysicalMemory,TotalVirtualMemorySize,FreeVirtualMemory",1))]),
      ("Sprzęt",[("Komputer i UUID",_list("Get-CimInstance Win32_ComputerSystemProduct|Select Vendor,Name,IdentifyingNumber,UUID",4)),("BIOS/UEFI",_list("Get-CimInstance Win32_BIOS|Select Manufacturer,Name,SerialNumber,SMBIOSBIOSVersion,ReleaseDate",4)),("Płyta główna",_list("Get-CimInstance Win32_BaseBoard|Select Manufacturer,Product,SerialNumber,Version",4)),("Dyski fizyczne",_table("Get-CimInstance Win32_DiskDrive|Select Model,SerialNumber,InterfaceType,MediaType,Size,Status",40)),("SMART",_table("Get-CimInstance -Namespace root\\wmi -Class MSStorageDriver_FailurePredictStatus|Select InstanceName,PredictFailure,Reason",40))])]
    step(.28,"Dyski, katalogi i sieć")
    data += [
      ("Katalogi systemowe",[("Windows",os.getenv("WINDIR",NO_DATA)),("System32",str(Path(os.getenv("WINDIR",r"C:\Windows"))/"System32")),("TEMP",os.getenv("TEMP",NO_DATA)),("Aplikacja",str(Path.cwd()))]),
      ("Dyski logiczne",[("Woluminy",_table("Get-CimInstance Win32_LogicalDisk|Select DeviceID,VolumeName,DriveType,FileSystem,Size,FreeSpace,ProviderName",64))]),
      ("Dane sieciowe",[("Konfiguracja IP",_run(["ipconfig","/all"])),("Profile Wi-Fi",_run(["netsh","wlan","show","profiles"])),("Interfejs Wi-Fi",_run(["netsh","wlan","show","interfaces"])),("ARP",_run(["arp","-a"])),("Karty",_table("Get-NetAdapter|Select Name,InterfaceDescription,Status,MacAddress,LinkSpeed",64)),("Historia Wi-Fi",_table("Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-WLAN-AutoConfig/Operational';Id=8001,8002,8003,11000,11001} -MaxEvents 40|Select TimeCreated,Id,Message",40))])]
    step(.48,"Programy, aktualizacje i sterowniki")
    data += [
      ("Programy",[("Zainstalowane programy",_table("Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*,HKLM:\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*,HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*|? DisplayName|Sort DisplayName -Unique|Select DisplayName,DisplayVersion,Publisher,InstallDate,InstallLocation",350,40))]),
      ("Aktualizacje i sterowniki",[("Aktualizacje",_table("Get-HotFix|Sort InstalledOn -Descending|Select HotFixID,Description,InstalledOn,InstalledBy",120)),("Sterowniki urządzeń",_table("Get-CimInstance Win32_PnPSignedDriver|Sort DeviceName|Select DeviceName,Manufacturer,DriverVersion,DriverDate",180,40)),("Sterowniki systemowe",_table("Get-CimInstance Win32_SystemDriver|Sort Name|Select Name,State,StartMode,PathName",150,35))])]
    step(.66,"Procesy, usługi i autostart")
    data.append(("Procesy, usługi i autostart",[("Procesy",_table("Get-Process|Sort ProcessName|Select ProcessName,Id,CPU,WorkingSet,Path",180)),("Usługi",_table("Get-Service|Sort Name|Select Name,DisplayName,Status,StartType",220)),("Porty i połączenia",_run(["netstat","-ano"])),("Autostart",_table("Get-CimInstance Win32_StartupCommand|Sort Name|Select Name,Command,Location,User",150))]))
    step(.78,"Artefakty śledcze")
    app=Path(os.getenv("APPDATA","")); local=Path(os.getenv("LOCALAPPDATA","")); win=Path(os.getenv("WINDIR",r"C:\Windows")); recent=app/"Microsoft/Windows/Recent"
    data.append(("Dane śledcze",[("Prefetch",_paths(win/"Prefetch","*.pf")),("Recent Files",_paths(recent)),("Jump Lists",_paths(recent/"AutomaticDestinations","*.automaticDestinations-ms")),("LNK",_paths(recent,"*.lnk")),("Timeline",_paths(local/"ConnectedDevicesPlatform","ActivitiesCache.db",True)),("Amcache",_paths(win/"AppCompat/Programs","Amcache.hve")),("Recycle Bin",_paths(Path(os.getenv("SystemDrive","C:"))/"$Recycle.Bin",recursive=True)),("ShimCache",_list("Get-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\AppCompatCache'",2))]))
    step(.87,"Certyfikaty i historia USB")
    data += [
      ("Certyfikaty",[("Użytkownik",_table("Get-ChildItem Cert:\\CurrentUser\\My|Select Subject,Issuer,NotBefore,NotAfter,Thumbprint",100)),("Komputer",_table("Get-ChildItem Cert:\\LocalMachine\\My|Select Subject,Issuer,NotBefore,NotAfter,Thumbprint",100)),("Zaufane urzędy",_table("Get-ChildItem Cert:\\LocalMachine\\Root|Select Subject,Issuer,NotAfter,Thumbprint",150))]),
      ("Historia urządzeń USB",[("USBSTOR",_table("Get-ChildItem 'HKLM:\\SYSTEM\\CurrentControlSet\\Enum\\USBSTOR' -Recurse|Select Name",150)),("Dyski USB",_table("Get-PnpDevice -Class DiskDrive|Select FriendlyName,InstanceId,Status",100)),("Urządzenia przenośne",_table("Get-PnpDevice|? {$_.Class -match 'WPD|Phone|Portable'}|Select FriendlyName,Class,InstanceId,Status",100)),("Drukarki i kamery",_table("Get-PnpDevice|? {$_.Class -match 'Printer|Camera|Image'}|Select FriendlyName,Class,InstanceId,Status",100))]),
      ("Proces aplikacji",[("Aplikacja",APP_NAME),("Wersja",APP_VERSION),("PID",str(os.getpid())),("Python",platform.python_version()),("Data",f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}")])]
    step(.93,"Zapisywanie raportów")
    return data

def generate_full_report(output_dir=None, progress=None):
    sections=collect_system_data(progress); folder=Path(output_dir) if output_dir else REPORTS_DIR/"System"; folder.mkdir(parents=True,exist_ok=True)
    base=folder/f"raport_systemowy_{dt.datetime.now():%Y%m%d_%H%M%S}"; payload={s:dict(r) for s,r in sections}
    paths={ext:base.with_suffix("."+ext) for ext in ("pdf","csv","json","txt")}
    paths["json"].write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    paths["txt"].write_text("EVIDLOCK LIGHT - PEŁNY RAPORT SYSTEMOWY\n"+"="*60+"\n\n"+"\n\n".join(f"[{s}]\n"+"\n".join(f"{k}: {v}" for k,v in r) for s,r in sections),encoding="utf-8")
    with paths["csv"].open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.writer(f,delimiter=";"); w.writerow(["Sekcja","Pole","Wartość"])
        for s,rows in sections:
            for k,v in rows: w.writerow([s,k,v])
    pdf_sections=[]
    for i,(s,rows) in enumerate(sections):
        split_rows=[]
        for key,value in rows:
            lines=str(value).splitlines() or [NO_DATA]
            for part in range(0,len(lines),30): split_rows.append((key if part==0 else f"{key} (ciąg dalszy)","\n".join(lines[part:part+30])))
        pdf_sections.append({"title":s,"rows":split_rows,"page_break":i>0})
    reports.write_professional_pdf("EvidLock Light - pełny raport systemowy",pdf_sections,paths["pdf"],"Lokalny raport komputera i Windows znany z EvidLockV2.",{"Komputer":socket.gethostname(),"Użytkownik":getpass.getuser(),"Administrator":"Tak" if is_admin() else "Nie"})
    if progress: progress(100,"Raport gotowy")
    return {k:str(v) for k,v in paths.items()}|{"sections":len(sections)}
