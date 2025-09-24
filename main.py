import os
import sys
import shutil
import glob
import csv
import difflib
import re
import xml.etree.ElementTree as ET
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import Counter
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

console = Console()

# ==================== MENU UTAMA ====================
def main_menu():
    console.print("[bold cyan]==============| MENU UTAMA |==============[/bold cyan]\n")
    console.print("1. Proses [green]file txt[/green] → WA Report")
    console.print("2. Proses [yellow]file txt[/yellow] → Event Report")
    console.print("3. Proses [blue]file xml[/blue] → Excel Export")
    console.print("4. Buat [magenta]Template Event[/magenta]")
    console.print("5. Cek [magenta]False Positive[/magenta] Event")
    console.print("6. [green]Tambah Event ke Database[/green]")

    console.print("99. [red]Exit[/red]\n")

    mode = Prompt.ask(
        "[bold white]Pilih mode[/bold white]",
        choices=["1", "2", "3", "4", "5","6", "99"],
        default="1"
    )
    console.print(f"\n[cyan]>> Mode dipilih:[/cyan] {mode}\n")

    if mode in ["1", "2", "3"]:
        table = Table(title="Daftar Shift", show_header=True, header_style="bold magenta")
        table.add_column("Kode", justify="center", style="cyan")
        table.add_column("Nama Shift", justify="center", style="green")
        table.add_column("Waktu", justify="center", style="yellow")

        for k, (nama, jam) in SHIFTS.items():
            table.add_row(k, nama, jam)

        console.print(table)

        shift = Prompt.ask(
            "[bold white]Pilih shift[/bold white]",
            choices=["1", "2", "3", "0"],
            default=get_default_shift()
        )

        if shift == "0":
            return None, None

        console.print(f"\n[cyan]>> Shift dipilih:[/cyan] {shift} - {SHIFTS[shift][0]} ({SHIFTS[shift][1]})\n")
        return mode, shift
    else:
        return mode, None


# ==================== KONSTANTA ====================
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
RESET = "\033[0m"

TEMPLATE_DIR = "templates"
OUTPUT_DIR = "outputs"

SHIFTS = {
    "3": ("Selamat Pagi", "00.00 - 08.00"),
    "1": ("Selamat Sore", "08.00 - 16.00"),
    "2": ("Selamat Malam", "16.00 - 00.00"),
}

BULAN_MAP = {
    "Jan": "Januari", "Feb": "Februari", "Mar": "Maret", "Apr": "April",
    "May": "Mei", "Jun": "Juni", "Jul": "Juli", "Aug": "Agustus",
    "Sep": "September", "Oct": "Oktober", "Nov": "November", "Dec": "Desember",
}

# ==================== SHIFT ====================
def get_default_shift():
    hour = datetime.now().hour
    if 0 <= hour < 8:
        return "3"
    elif 8 <= hour < 16:
        return "1"
    else:
        return "2"

# ==================== LOAD CSV MAGNITUDE ====================
def load_event_magnitudes(csv_file):
    mapping = {}
    try:
        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    event = row["Event Name"].strip()
                    magnitude = int(row["Magnitude"])
                    mapping[event] = magnitude
                except Exception:
                    continue
    except FileNotFoundError:
        print(f"{RED}[WARNING]{RESET} File magnitude '{csv_file}' tidak ditemukan, lanjut tanpa mapping...")
    return mapping

def categorize_magnitude(mag):
    if 1 <= mag <= 3:
        return "Low"
    elif 4 <= mag <= 6:
        return "Medium"
    elif 7 <= mag <= 10:
        return "High"
    return "Unknown"

# ==================== UTIL ====================
def verticalize(raw):
    if not raw or raw == "-":
        return "-"
    lines = [x.strip() for x in raw.splitlines() if x.strip()]
    return "<br>\n".join(lines) + "<br>" if lines else "-"

# ==================== FILE TXT ====================
def parse_txt_file(file_path):
    parsed_events = []
    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t', quotechar='"')
        for parts in reader:
            if len(parts) <= 3:
                continue

            def get_part(idx):
                return parts[idx].strip() if len(parts) > idx else ""

            event = {
                "event_id": get_part(0),           # NO
                "analyst": get_part(1),            # AGENT NAME
                "ticket_id": get_part(2),          # NO. TICKET IRIS
                "event_type": get_part(3),         # OFFENSES TYPE
                "reason_close": get_part(4),       # Reason Close Offense
                "escalation": get_part(5),         # Escalation
                "link_alert": get_part(6),         # Link Alert (khusus escalation)
                "event_name": get_part(7),         # ALERT NAME
                "magnitude": get_part(8),          # MAGNITUDE
                "tanggal": get_part(9),            # DATE
                "waktu": get_part(10),             # TIME
                "ticket_date": get_part(11),       # TICKET DATE
                "ticket_time": get_part(12),       # TICKET TIME
                "soc_response_time": get_part(13), # SOC RESPONSE TIME
                "user_date": get_part(14),         # USER DATE
                "user_time": get_part(15),         # USER TIME
                "user_response_time": get_part(16),# USER RESPONSE TIME
                "action": get_part(17),            # ACTION
                "event_status": get_part(18),      # EVENT STATUS
                "traffic_flow": get_part(19),      # TRAFFIC FLOW
                "src_ip": verticalize(get_part(20)),      # SRC IP
                "src_country": verticalize(get_part(21)), # SRC COUNTRY
                "dst_ip": verticalize(get_part(22)),      # DST IP
                "dst_port": verticalize(get_part(23)),    # DST PORT
                "dst_country": verticalize(get_part(24)), # DST COUNTRY
                "app_access": get_part(25),        # SERVICE / APP ACCESS
                "user_agent": get_part(26),        # USER AGENT
                "request_server": get_part(27),    # REQUEST SERVER
                "url": verticalize(get_part(28)),  # URL / DNS
                "query": verticalize(get_part(29)),# REQUEST QUERY
                "note": verticalize(get_part(30)), # NOTE
            }
            parsed_events.append(event)
    return parsed_events

# ==================== CLEAN FOLDER ====================
def clean_shift_folder(shift_key):
    shift_outdir = os.path.join(OUTPUT_DIR, f"shift{shift_key}")
    os.makedirs(shift_outdir, exist_ok=True)  # pastikan folder ada

    for item in os.listdir(shift_outdir):
        item_path = os.path.join(shift_outdir, item)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path)
                print(f"{GREEN}[OK]{RESET} File lama dihapus...")
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
                print(f"{GREEN}[OK]{RESET} Folder lama dihapus...")
        except Exception as e:
            print(f"{RED}[WARNING]{RESET} Gagal hapus {item_path}: {e}")

    return shift_outdir


# ==================== WRITE WA ====================
def write_wa(offenses, logs, shift_key, template_file):
    greeting, jam = SHIFTS[shift_key]
    tanggal = datetime.now().strftime("%d/%m/%Y")

    with open(template_file, "r", encoding="utf-8") as f:
        template = f.read()

    offenses_count = Counter(e['event_name'] for e in offenses)
    logs_count = Counter(e['event_name'] for e in logs)

    offenses_str = "\n".join(f"{i}. {name} ({count} events)" for i, (name, count) in enumerate(offenses_count.items(), 1)) or "Tidak ada event terdeteksi"
    logs_str = "\n".join(f"{i}. {name} ({count} events)" for i, (name, count) in enumerate(logs_count.items(), 1)) or "Tidak ada event terdeteksi"

    wa_text = template.replace("{salam}", greeting)\
                      .replace("{tanggal}", tanggal)\
                      .replace("{jam}", jam)\
                      .replace("{offenses}", offenses_str)\
                      .replace("{log_activity}", logs_str)

    shift_outdir = os.path.join(OUTPUT_DIR, f"shift{shift_key}")
    out_file = os.path.join(shift_outdir, f"wa_shift{shift_key}.txt")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(wa_text)

    print(f"{YELLOW}[INFO]{RESET} WA master tersimpan di {out_file}")

# ==================== TEMPLATE EVENT ====================
def check_template(event_name):
    filename = os.path.join(TEMPLATE_DIR, f"{event_name}.txt")
    if not os.path.exists(filename):
        print(f"{RED}[WARNING]{RESET} Template untuk '{event_name}' belum ditemukan, dilewati...")
        return False
    return True

def fill_template(template_content, event_data, mag_map=None):
    filled_content = template_content
    for key, value in event_data.items():
        filled_content = filled_content.replace(f"{{{key}}}", str(value))

    if mag_map:
        event_name = event_data.get("event_name", "")
        magnitude = mag_map.get(event_name)
        if magnitude:
            severity = categorize_magnitude(magnitude)
            filled_content = filled_content.replace("{sev_magnitude}", str(magnitude))
            filled_content = filled_content.replace("{severity}", severity)

    return filled_content

def write_event_details(events, shift_key, mag_map=None):
    shift_outdir = os.path.join(OUTPUT_DIR, f"shift{shift_key}")
    os.makedirs(shift_outdir, exist_ok=True)

    processed_event_names = set()
    valid_types = ["Log Activity", "Offensess"]

    line_counter = 0  # penghitung baris untuk selang-seling

    for event_data in events:
        event_name = event_data.get("event_name", "").strip().strip('"')
        ticket_id = event_data.get("ticket_id", "").strip()
        event_type = event_data.get("event_type", "").strip()

        if not ticket_id or event_type not in valid_types:
            continue

        unique_key = f"{event_name}_{ticket_id}_{event_type}"
        if unique_key in processed_event_names:
            continue

        if check_template(event_name):
            template_file = os.path.join(TEMPLATE_DIR, f"{event_name}.txt")
            with open(template_file, "r", encoding="utf-8") as f:
                template = f.read()

            filled_template = fill_template(template, event_data, mag_map)
            out_file_unique = os.path.join(
                shift_outdir, f"{event_name}_{ticket_id}_{event_type}.txt"
            )

            with open(out_file_unique, "w", encoding="utf-8") as f:
                f.write(filled_template)

            # pilih warna selang-seling (cyan ↔ magenta)
            color = CYAN if line_counter % 2 == 0 else MAGENTA
            print(f"{GREEN}[OK]{RESET} {color}{event_name} | {ticket_id} | {event_type}{RESET}")

            processed_event_names.add(unique_key)
            line_counter += 1

# ==================== FILE XML ====================
def xml_to_excel(xml_file, shift_key):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    rows = []
    closed_date_sample = None

    for offense in root.findall("OffenseForm"):
        closed_date = offense.findtext("formattedClosedDate", "")
        if closed_date and not closed_date_sample:
            closed_date_sample = closed_date

        rows.append({
            "id": offense.findtext("id", ""),
            "magnitude": offense.findtext("magnitude", ""),
            "closeUser": offense.findtext("closeUser", ""),
            "formattedClosedDate": closed_date,
            "localizedCloseReason": offense.findtext("localizedCloseReason", ""),
            "deviceOrderBy": offense.findtext("deviceOrderBy", ""),
            "escapedFormattedOffenseSource": offense.findtext("escapedFormattedOffenseSource", ""),
            "formattedOffenseType": offense.findtext("formattedOffenseType", ""),
            "description": offense.findtext("description", ""),
            "severity": offense.findtext("severity", ""),
            "eventCount": offense.findtext("eventCount", ""),
            "eventDescription": offense.findtext("eventDescription", ""),
            "startTime": offense.findtext("startTime", ""),
            "endTime": offense.findtext("endTime", ""),
            "attacker": offense.findtext("attacker", ""),
            "target": offense.findtext("target", ""),
            "deviceCount": offense.findtext("deviceCount", ""),
            "targetNetwork": offense.findtext("targetNetwork", ""),
            "attackerNetwork": offense.findtext("attackerNetwork", ""),
            "usernameOrderBy": offense.findtext("usernameOrderBy", ""),
        })

    df = pd.DataFrame(rows)

    tanggal_file = "UnknownDate"
    if closed_date_sample:
        parts = closed_date_sample.split()
        if len(parts) >= 3:
            hari = parts[0].zfill(2)
            bulan = BULAN_MAP.get(parts[1], parts[1])
            tahun = parts[2]
            tanggal_file = f"{hari} {bulan} {tahun}"

    salam, jam = SHIFTS.get(shift_key, ("Shift Tidak Dikenal", ""))

    base_name = f"FollowUp & Closed Offenses List - {tanggal_file} ( Shift {shift_key} ).xlsx"
    output_dir = Path("./outputs/")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_excel = output_dir / base_name 
    df.to_excel(output_excel, index=False)
    print(f"{GREEN}[OK]{RESET} Excel berhasil dibuat: {output_excel}")

# ==================== LOAD DATABASE EVENT ====================
def load_event_names(csv_file="./database/events_magnitude_list.csv"):
    events = []
    try:
        with open(csv_file, newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "Event Name" in row and row["Event Name"].strip():
                    events.append(row["Event Name"].strip())
    except FileNotFoundError:
        print(f"{RED}[WARNING]{RESET} File '{csv_file}' tidak ditemukan. Validasi event dilewati.")
    return events

# ==================== SUGGERTON EVENT ====================
def suggest_event(event_name, valid_events):
    event_name_lower = event_name.lower()

    substring_matches = [e for e in valid_events if event_name_lower in e.lower()]
    if substring_matches:
        return substring_matches[:5]

    suggestions_lower = difflib.get_close_matches(event_name_lower, [e.lower() for e in valid_events], n=3, cutoff=0.5)
    suggestions = []
    for s in suggestions_lower:
        original = next(e for e in valid_events if e.lower() == s)
        suggestions.append(original)

    return suggestions

def list_events(valid_events):
    print(f"\n{YELLOW}[INFO]{RESET} Daftar Event yang tersedia di database:")
    for i, event in enumerate(valid_events, 1):
        print(f"  {i}. {event}")
    print()


# ==================== GENERATOR TEMPLATE EVENT ====================
def get_multiline_input(prompt):
    print(prompt + " (ketik END di baris baru untuk selesai):")
    lines = []
    while True:
        line = input()
        if line.strip().upper() == "END":
            break
        lines.append(line)
    return "\n".join(lines)

def generate_template(event_name, deskripsi, mitigasi):
    TEMPLATE_FILE = "./templates/Tamplate.txt"
    OUTPUT_DIR = "templates"

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        base_template = f.read()

    filled_template = base_template.replace("{deskripsi}", deskripsi).replace("{mitigasi}", mitigasi)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_name = event_name
    out_file = os.path.join(OUTPUT_DIR, f"{safe_name}.txt")

    # kalau file sudah ada → tanya overwrite
    if os.path.exists(out_file):
        choice = Prompt.ask(
            f"{YELLOW}[INFO]{RESET} File '{out_file}' sudah ada. Timpa?",
            choices=["y", "n"], default="n"
        )
        if choice.lower() != "y":
            print(f"{RED}[CANCEL]{RESET} Template '{event_name}' tidak dibuat.")
            return

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(filled_template)

    print(f"{GREEN}[OK]{RESET} Template event '{event_name}' berhasil dibuat di {out_file}")

# ==================== LOAD FALSE POSITIVE ====================
def normalize(text):
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text

def load_false_positive(file_path="./database/False_Positive.txt"):
    fp_events = set()
    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                event_name = line.strip()
                if event_name:
                    fp_events.add(normalize(event_name))
    except FileNotFoundError:
        print(f"{YELLOW}[WARNING]{RESET} File {file_path} tidak ditemukan.")
    return fp_events

def check_event_status(event_name, fp_events, valid_events):
    norm_name = normalize(event_name)

    # Kalau event ada di database
    if any(norm_name == normalize(e) for e in valid_events):
        # Kalau event termasuk FP
        if norm_name in [normalize(e) for e in fp_events]:
            return "FP", None
        else:
            return "VALID", None

    # Kalau tidak ada di database → Unknown + Suggestion
    suggestions = suggest_event(event_name, valid_events)
    return "UNKNOWN", suggestions
def print_false_positive_summary(events, fp_events, valid_events):
    detected_fp = []
    detected_unknown = []

    for e in events:
        status, suggestions = check_event_status(e["event_name"], fp_events, valid_events)
        if status == "FP":
            detected_fp.append(e["event_name"])
        elif status == "UNKNOWN":
            detected_unknown.append((e["event_name"], suggestions))

    # Tampilkan False Positive
    if detected_fp:
        console.print("\n[bold red]============== FALSE POSITIVE DETECTION ==============[/bold red]")
        for i, name in enumerate(set(detected_fp), 1):
            console.print(f"[red]{i}.[/red] {name}")
        console.print("[bold red]======================================================[/bold red]\n")
    else:
        console.print("\n[bold red]===== FALSE POSITIVE DETECTION =====[/bold red]")
        console.print("[green]Tidak ada event False Positive terdeteksi.[/green]")
        console.print("[bold red]====================================[/bold red]\n")

    # Tampilkan Unknown Event
    if detected_unknown:
        console.print("\n[bold yellow]============== UNKNOWN EVENTS ==============[/bold yellow]")
        
        for i, (name, suggestions) in enumerate(detected_unknown, 1):
            console.print(f"[yellow]{i}. {name}[/yellow]")
            if suggestions:
                console.print(f"   [green]Mungkin maksud Anda:[/green] {', '.join(suggestions)}")
        console.print("[bold yellow]======================================================[/bold yellow]\n")

# ==================== MANU ====================
def run_mode_1(shift, fp_events):
    txt_files = glob.glob("./input/*.txt")
    wa_template_file = os.path.join(TEMPLATE_DIR, "wa.txt")

    if not txt_files:
        print(f"{RED}[ERROR]{RESET} file .txt tidak ditemukan!")
        return

    if not os.path.exists(wa_template_file):
        print(f"{RED}[ERROR]{RESET} Template WA '{wa_template_file}' tidak ditemukan!")
        return

    clean_shift_folder(shift)

    all_events = []
    for txt_file in txt_files:
        all_events.extend(parse_txt_file(txt_file))

    mag_map = load_event_magnitudes(os.path.join("database", "events_magnitude_list.csv"))

    offenses = [e for e in all_events if e["event_type"].strip() == "Offensess"]
    log_activities = [e for e in all_events if e["event_type"].strip() == "Log Activity"]

    valid_events = load_event_names()
    write_wa(offenses, log_activities, shift, wa_template_file)
    print_false_positive_summary(all_events, fp_events, valid_events)

    



def run_mode_2(shift, fp_events):
    """Event Report (dari TXT) — buat file detail per event berdasarkan template."""
    txt_files = glob.glob("./input/*.txt")
    if not txt_files:
        print(f"{RED}[ERROR]{RESET} file .txt tidak ditemukan!")
        return

    shift_outdir = clean_shift_folder(shift)

    all_events = []
    for txt_file in txt_files:
        all_events.extend(parse_txt_file(txt_file))

    # Load magnitude mapping
    mag_map = load_event_magnitudes(os.path.join("database", "events_magnitude_list.csv"))

    valid_events = load_event_names()

    write_event_details(all_events, shift, mag_map)

    print_false_positive_summary(all_events, fp_events, valid_events)




def run_mode_3(shift):
    """XML → Excel"""
    xml_files = glob.glob("./input/*.xml")
    if not xml_files:
        print(f"{RED}[ERROR]{RESET} file .xml tidak ditemukan!")
        return

    for xml_file in xml_files:
        xml_to_excel(xml_file, shift)
        try:
            os.remove(xml_file)
            print(f"{YELLOW}[INFO]{RESET} File {xml_file} berhasil dihapus.")
        except Exception as e:
            print(f"{RED}[ERROR]{RESET} Gagal menghapus {xml_file}: {e}")


def run_mode_4():
    valid_events = load_event_names()  # list event dari CSV

    while True:
        console.print("Masukkan Nama Event ([red]Exit[/red], [yellow]List[/yellow])")
        event_name = Prompt.ask(">> ").strip()

        if event_name.lower() == "exit":
            print(f"{YELLOW}[INFO]{RESET} Kembali ke menu utama.\n")
            return  # <-- balik ke main_menu
        if event_name.lower() == "list":
            list_events(valid_events)
            continue
        if not event_name:
            print(f"{RED}[ERROR]{RESET} Nama event tidak boleh kosong!\n")
            continue

        # cek exact match
        matches = [e for e in valid_events if e.lower() == event_name.lower()]
        if not matches:
            # tampilkan suggestion
            suggestions = suggest_event(event_name, valid_events)
            if suggestions:
                print(f"{RED}[ERROR]{RESET} Event '{event_name}' tidak ada di database.")
                print(f"{YELLOW}[INFO]{RESET} Mungkin maksud Anda:")
                for i, s in enumerate(suggestions, 1):
                    print(f"  {i}. {s}")
                print()

                choice = Prompt.ask("Pilih nomor suggestion atau ketik ulang nama event (atau 'skip')", default="skip")
                if choice.isdigit() and 1 <= int(choice) <= len(suggestions):
                    event_name = suggestions[int(choice) - 1]
                    print(f"{GREEN}[OK]{RESET} Anda memilih: {event_name}\n")
                elif choice.lower() == "skip":
                    continue
                else:
                    event_name = choice.strip()
                    if not any(e.lower() == event_name.lower() for e in valid_events):
                        print(f"{RED}[ERROR]{RESET} Event '{event_name}' tetap tidak valid.\n")
                        continue
            else:
                print(f"{RED}[ERROR]{RESET} Event '{event_name}' tidak ada di database.\n")
                continue
        else:
            event_name = matches[0]

        # cek apakah file template sudah ada
        out_file = os.path.join("templates", f"{event_name}.txt")
        if os.path.exists(out_file):
            choice = Prompt.ask(
                f"{YELLOW}[INFO]{RESET} Template '{event_name}' sudah ada. Timpa?",
                choices=["y", "n"], default="n"
            )
            if choice.lower() != "y":
                print(f"{RED}[CANCEL]{RESET} Template '{event_name}' dilewati.\n")
                continue

        deskripsi = get_multiline_input("Masukkan Deskripsi Event")
        mitigasi = get_multiline_input("Masukkan Mitigasi Event")
        generate_template(event_name, deskripsi, mitigasi)

def run_mode_5(fp_events):
    valid_events = load_event_names()
    while True:
        console.print("Masukkan Nama Event ([red]Exit[/red], [yellow]ListFP[/yellow], [yellow]ListDB[/yellow])")
        event = Prompt.ask(">> ").strip()
        if event.lower() == "exit":
            print(f"{YELLOW}[INFO]{RESET} Kembali ke menu utama.\n")
            return
        if event.lower() == "listfp":
            print(f"\n{RED}===== DAFTAR FALSE POSITIVE ====={RESET}")
            for i, ev in enumerate(fp_events, 1):
                print(f"{RED}{i}. {ev}{RESET}")
            print(f"{RED}================================={RESET}\n")
            continue
        if event.lower() == "listdb":
            list_events(valid_events)
            continue

        status, suggestions = check_event_status(event, fp_events, valid_events)

        if status == "FP":
            print(f"{RED}[INFO]{RESET} Event '{event}' termasuk {RED}[FALSE POSITIVE]{RESET}")
        elif status == "VALID":
            print(f"{GREEN}[INFO]{RESET} Event '{event}' {GREEN}BUKAN false positive (valid){RESET}")
        elif status == "UNKNOWN":
            print(f"{YELLOW}[WARNING]{RESET} Event '{event}' tidak ditemukan di database event list.")
            if suggestions:
                print(f"{GREEN}[SUGGESTION]{RESET} Mungkin maksud anda: {', '.join(suggestions)}")

def run_mode_6():
    csv_file = "./database/events_magnitude_list.csv"

    # Load event database yang sudah ada
    existing_events = load_event_names(csv_file)

    while True:
        console.print("\n[bold cyan]Masukkan Nama Event Baru ([red]Exit[/red])[/bold cyan]")
        event_name = Prompt.ask(">> ").strip()

        if event_name.lower() == "exit":
            print(f"{YELLOW}[INFO]{RESET} Kembali ke menu utama.\n")
            return

        if not event_name:
            print(f"{RED}[ERROR]{RESET} Nama event tidak boleh kosong!\n")
            continue

        # Cek duplikat
        if any(event_name.lower() == e.lower() for e in existing_events):
            print(f"{YELLOW}[WARNING]{RESET} Event '{event_name}' sudah ada di database!")
            continue

        # Input magnitude
        while True:
            try:
                magnitude = int(Prompt.ask("Masukkan Magnitude (1–10)"))
                if not 1 <= magnitude <= 10:
                    raise ValueError
                break
            except ValueError:
                print(f"{RED}[ERROR]{RESET} Magnitude harus berupa angka antara 1 sampai 10.")

        # Tambahkan ke CSV
        try:
            with open(csv_file, "a", newline='', encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([event_name, magnitude])
            print(f"{GREEN}[OK]{RESET} Event '{event_name}' (Magnitude: {magnitude}) berhasil ditambahkan!")
            existing_events.append(event_name)  # Update list lokal
        except Exception as e:
            print(f"{RED}[ERROR]{RESET} Gagal menambahkan event: {e}")

# ==================== MAIN ====================
if __name__ == "__main__":
    try:
        false_positive_events = load_false_positive()

        while True:
            default_shift = get_default_shift()
            mode, shift = main_menu()

            if mode == "1":
                run_mode_1(shift, false_positive_events)
            elif mode == "2":
                run_mode_2(shift, false_positive_events)
            elif mode == "3":
                run_mode_3(shift) 
            elif mode == "4":
                run_mode_4()       
            elif mode == "5":
                run_mode_5(false_positive_events)
            elif mode == "6":
                run_mode_6()
            elif mode == "99":
                print(f"{YELLOW}[INFO]{RESET} Program dihentikan user (Exit).")
                break
            else:
                print(f"{RED}[ERROR]{RESET} Mode tidak dikenal.")

    except KeyboardInterrupt:
        print(f"\n{YELLOW}[INFO]{RESET} Program dihentikan oleh user (CTRL+C).")
        sys.exit(0)
