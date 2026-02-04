import psutil
import platform
import os
import shutil
import subprocess
import json
import matplotlib.pyplot as plt

# --- KONFIGURASI WARNA ---
def get_color_and_status(percent):
    if percent >= 88:
        return 'green', 'Sehat'
    elif 70 <= percent < 88:
        return 'gold', 'Warning'
    else:
        return 'red', 'Kritis'

# --- FUNGSI CEK KETERSEDIAAN SMARTCTL ---
def is_smartctl_available():
    """Mengecek apakah smartctl terinstall di sistem."""
    return shutil.which("smartctl") is not None

# --- FUNGSI AMBIL DATA (LINUX / ADVANCED) ---
def get_smart_data_linux(device_path):
    """
    Hanya dijalankan jika smartctl ada.
    Memiliki timeout 2 detik agar TIDAK STUCK.
    """
    raw_device = ''.join([i for i in device_path if not i.isdigit()])
    info = {'temp': 0, 'health': 0, 'model': 'Unknown', 'has_smart': False}

    try:
        # Timeout 2 detik = Anti Stuck
        cmd = ['smartctl', '-j', '-a', raw_device]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        
        if result.stdout:
            data = json.loads(result.stdout)
            info['has_smart'] = True
            info['model'] = data.get('model_name', raw_device)
            
            # Ambil Suhu
            try:
                info['temp'] = data['temperature']['current']
            except KeyError:
                info['temp'] = 0

            # Hitung Health (NVMe / SATA)
            if 'nvme_smart_health_information_log' in data:
                used = data['nvme_smart_health_information_log'].get('percentage_used', 0)
                info['health'] = 100 - used
            elif 'ata_smart_attributes' in data:
                health_found = False
                for attr in data['ata_smart_attributes']['table']:
                    if attr['id'] in [177, 231, 233]: 
                        info['health'] = attr['value']
                        health_found = True
                        break
                if not health_found:
                    passed = data.get('smart_status', {}).get('passed', True)
                    info['health'] = 100 if passed else 50
            else:
                # Default jika tidak ada data spesifik tapi passed
                info['health'] = 100

    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        # Jika timeout atau error, kembalikan data kosong (aman)
        pass
    except Exception:
        pass
    
    return info

# --- FUNGSI GRAFIK ---
def show_dashboard(disks, os_name):
    if not disks: return

    # Siapkan data untuk grafik
    labels = []
    values = []
    colors = []
    
    # Mode tampilan beda tergantung ketersediaan data SMART
    is_health_mode = any(d.get('has_smart', False) for d in disks)

    for d in disks:
        labels.append(f"{d['device']}\n({d['mount']})")
        
        if is_health_mode and d.get('has_smart', False):
            # Tampilkan Health jika ada
            values.append(d['health'])
            colors.append(get_color_and_status(d['health'])[0])
            title_text = "Disk Health Monitoring"
            xlabel_text = "Health (%)"
            max_val = 100
        else:
            # Tampilkan Kapasitas Used % jika tidak ada smartctl (Windows Default)
            values.append(d['percent_used'])
            colors.append('skyblue')
            title_text = "Disk Usage Monitoring (Space Used)"
            xlabel_text = "Used Space (%)"
            max_val = 100

    plt.figure(figsize=(10, 6))
    bars = plt.barh(labels, values, color=colors)
    
    plt.title(f"{title_text} - {os_name}")
    plt.xlabel(xlabel_text)
    plt.xlim(0, max_val)

    # Label pada bar
    for bar, val, d in zip(bars, values, disks):
        width = bar.get_width()
        
        if is_health_mode and d.get('has_smart', False):
            # Teks Mode Health
            temp_txt = f" | {d['temp']}°C" if d['temp'] > 0 else ""
            status = get_color_and_status(val)[1]
            txt = f"{val}%{temp_txt} [{status}]"
        else:
            # Teks Mode Kapasitas
            txt = f"{val}% Used"

        plt.text(width + 1, bar.get_y() + bar.get_height()/2, 
                 txt, va='center', fontweight='bold')

    plt.tight_layout()
    print("\n[INFO] Grafik ditampilkan...")
    try:
        plt.show()
    except:
        plt.savefig("disk_monitor.png")
        print("[INFO] Grafik disimpan ke 'disk_monitor.png'")

# --- MAIN LOGIC ---
def scan_system():
    os_name = platform.system()
    has_smartctl = is_smartctl_available()
    
    print("="*50)
    print(f"OS: {os_name} | Smartctl: {'Available' if has_smartctl else 'Not Found'}")
    print("="*50)

    final_disks = []
    processed_mounts = set()

    try:
        partitions = psutil.disk_partitions(all=False)
        for part in partitions:
            # Filter Loop/Ram
            if os_name == "Linux" and ('loop' in part.device or 'ram' in part.device): continue
            if "cdrom" in part.opts or part.fstype == "": continue
            
            if part.mountpoint in processed_mounts: continue
            processed_mounts.add(part.mountpoint)

            try:
                usage = psutil.disk_usage(part.mountpoint)
                
                disk_data = {
                    'device': part.device,
                    'mount': part.mountpoint,
                    'percent_used': usage.percent,
                    'has_smart': False,
                    'temp': 0,
                    'health': 0
                }

                # LOGIKA LINUX (Cek Suhu & Health)
                # Hanya jalan jika OS Linux DAN user adalah Root DAN smartctl ada
                if os_name == "Linux" and os.geteuid() == 0 and has_smartctl:
                    print(f"Deep Scan (SMART): {part.device}...", end=" ", flush=True)
                    smart_info = get_smart_data_linux(part.device)
                    if smart_info['has_smart']:
                        disk_data.update(smart_info)
                        print("Done.")
                    else:
                        print("Skipped (No SMART data).")
                else:
                    # Windows atau Linux Non-Root
                    print(f"Basic Scan: {part.device}")

                final_disks.append(disk_data)

            except Exception as e:
                continue

        if final_disks:
            show_dashboard(final_disks, os_name)
        else:
            print("Tidak ada disk ditemukan.")

    except Exception as e:
        print(f"Error Scan: {e}")

if __name__ == "__main__":
    scan_system()