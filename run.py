import os
import sys
import shutil
import csv
from datetime import datetime
from collections import Counter

# --- Warna ANSI ---
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RESET = "\033[0m"

TEMPLATE_DIR = "templates"
OUTPUT_DIR = "outputs"

SHIFTS = {
    "3": ("Selamat Pagi", "00.00 - 08.00"),
    "1": ("Selamat Sore", "08.00 - 16.00"),
    "2": ("Selamat Malam", "16.00 - 00.00"),
}

def get_default_shift():
    hour = datetime.now().hour
    if 0 <= hour < 8:
        return "3"  # Pagi
    elif 8 <= hour < 16:
        return "1"  # Sore
    else:
        return "2"  # Malam

# --- Fungsi bantu untuk verticalize multiline field ---
def verticalize(raw):
    if not raw or raw == "-":
        return "-"
    # hapus baris kosong sebelum join
    lines = [x.strip() for x in raw.splitlines() if x.strip()]
    return "<br>\n".join(lines) + "<br>" if lines else "-"

# --- Parser raw.txt dengan multiline bersih ---
def parse_raw_file(file_path):
    parsed_events = []
    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t', quotechar='"')
        for parts in reader:
            if len(parts) <= 3:
                continue

            def get_part(idx):
                return parts[idx].strip() if len(parts) > idx else ""

            src_ip_raw = get_part(20)
            src_country_raw = get_part(21)
            dst_ip_raw = get_part(22)
            dst_port_raw = get_part(23)

            event = {
                "event_id": get_part(0),
                "analyst": get_part(1),
                "ticket_id": get_part(2),
                "event_type": get_part(3),
                "event_name": get_part(7) or get_part(4),
                "category": get_part(8),
                "magnitude": get_part(9),
                "tanggal": get_part(10),
                "waktu": get_part(11),
                "src_ip": verticalize(src_ip_raw),
                "src_country": verticalize(src_country_raw),
                "dst_ip": verticalize(dst_ip_raw),
                "dst_port": verticalize(dst_port_raw),
                "dst_asset": get_part(24),
                "query": verticalize(get_part(29) or "-"),  # query
                "url": verticalize(get_part(28) or "-"),    # URL
            }
            parsed_events.append(event)
    return parsed_events

# --- Bersihkan folder shift ---
def clean_shift_folder(shift_key):
    shift_outdir = os.path.join(OUTPUT_DIR, f"shift{shift_key}")
    if os.path.exists(shift_outdir):
        try:
            for root, dirs, files in os.walk(shift_outdir):
                for f in files:
                    os.remove(os.path.join(root, f))
            shutil.rmtree(shift_outdir)
        except PermissionError:
            print(f"{RED}[WARNING]{RESET} Tidak bisa hapus folder shift: {shift_outdir}")
    os.makedirs(shift_outdir, exist_ok=True)
    return shift_outdir

# --- WA Master ---
def write_wa(offenses, logs, shift_key, template_file):
    greeting, jam = SHIFTS[shift_key]
    tanggal = datetime.now().strftime("%d/%m/%Y")

    with open(template_file, "r", encoding="utf-8") as f:
        template = f.read()

    offenses_count = Counter(e['event_name'] for e in offenses)
    logs_count = Counter(e['event_name'] for e in logs)

    if offenses_count:
        offenses_str = "\n".join(f"{i}. {name} ({count} event{'s' if count>1 else ''})"
                                 for i, (name, count) in enumerate(offenses_count.items(), 1))
    else:
        offenses_str = "Tidak ada event terdeteksi"

    if logs_count:
        logs_str = "\n".join(f"{i}. {name} ({count} event{'s' if count>1 else ''})"
                             for i, (name, count) in enumerate(logs_count.items(), 1))
    else:
        logs_str = "Tidak ada event terdeteksi"

    wa_text = template.replace("{salam}", greeting)\
                      .replace("{tanggal}", tanggal)\
                      .replace("{jam}", jam)\
                      .replace("{offenses}", offenses_str)\
                      .replace("{log_activity}", logs_str)

    shift_outdir = os.path.join(OUTPUT_DIR, f"shift{shift_key}")
    os.makedirs(shift_outdir, exist_ok=True)
    out_file = os.path.join(shift_outdir, f"wa_shift{shift_key}.txt")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(wa_text)

    print(f"{YELLOW}[INFO]{RESET} WA master tersimpan di {out_file}")

# --- Detail per event ---
def check_template(event_name):
    filename = os.path.join(TEMPLATE_DIR, f"{event_name}.txt")
    if not os.path.exists(filename):
        print(f"{RED}[WARNING]{RESET} Template untuk '{event_name}' belum ditemukan, dilewati...")
        return False
    return True

def fill_template(template_content, event_data):
    filled_content = template_content
    for key, value in event_data.items():
        if key in ["src_ip", "src_country", "dst_ip", "dst_port"]:
            # tampil vertikal
            value_str = value
        else:
            value_str = str(value)
        filled_content = filled_content.replace(f"{{{key}}}", value_str)
    return filled_content

def write_event_details(events, shift_key):
    shift_outdir = os.path.join(OUTPUT_DIR, f"shift{shift_key}")
    os.makedirs(shift_outdir, exist_ok=True)

    processed_event_names = set()

    for event_data in events:
        event_name = event_data["event_name"]
        if event_name in processed_event_names:
            continue

        if check_template(event_name):
            filename = os.path.join(TEMPLATE_DIR, f"{event_name}.txt")
            with open(filename, "r", encoding="utf-8") as f:
                template = f.read()

            filled_template = fill_template(template, event_data)
            ticket_id = event_data.get("ticket_id", "")
            out_file_unique = os.path.join(shift_outdir, f"{event_name}_{ticket_id}.txt")

            with open(out_file_unique, "w", encoding="utf-8") as f:
                f.write(filled_template)

            print(f"{GREEN}[OK]{RESET} File detail untuk '{event_name}' (Ticket ID: {ticket_id}) dibuat di {out_file_unique}")
            processed_event_names.add(event_name)

# --- MAIN ---
if __name__ == "__main__":
    raw_file = "raw.txt"
    wa_template_file = os.path.join(TEMPLATE_DIR, "wa.txt")

    if not os.path.exists(raw_file):
        print(f"{RED}[ERROR]{RESET} raw.txt tidak ditemukan!")
        exit()
    if not os.path.exists(wa_template_file):
        print(f"{RED}[ERROR]{RESET} Template WA '{wa_template_file}' tidak ditemukan!")
        exit()

    default_shift = get_default_shift()

    
    try:
        shift = input(f"Pilih shift (1=Sore, 2=Malam, 3=Pagi) [default={default_shift}]: ").strip() or default_shift
    except KeyboardInterrupt:
        print(f"\n{YELLOW}[INFO]{RESET} Input dibatalkan, Keluar .....")
        sys.exit(0) 

    clean_shift_folder(shift)
    all_events = parse_raw_file(raw_file)

    # Debug event_type dan event_name
    print(f"{GREEN}[DEBUG]{RESET} Semua event_type yang terdeteksi:")
    for e in all_events:
        print(f"- '{e['event_type']}' | '{e['event_name']}'")

    offenses = [e for e in all_events if e["event_type"].strip() == "Offensess"]
    log_activities = [e for e in all_events if e["event_type"].strip() == "Log Activity"]

    write_wa(offenses, log_activities, shift, wa_template_file)
    write_event_details(all_events, shift)
