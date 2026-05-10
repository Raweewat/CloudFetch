# CloudFetch — Cloud Storage Download Tool

เครื่องมือสำหรับโหลดไฟล์จาก **Azure Blob Storage** และ **Huawei OBS** แบบ GUI พร้อมระบบจัดการไฟล์อัตโนมัติ

---

## โครงสร้างโปรเจกต์

```
CloudFetch/
├── main.py                     # Entry point
├── requirements.txt
├── gui/
│   ├── styles.py               # สี / Font ทั้งหมดของ UI
│   └── main_window.py          # หน้าจอหลัก (Tkinter GUI)
├── core/
│   ├── azure_client.py         # Wrapper สำหรับ Azure Blob Storage SDK
│   ├── huawei_client.py        # Wrapper สำหรับ Huawei OBS SDK
│   ├── simulation_client.py    # Client จำลองสำหรับทดสอบโดยไม่ต้อง connect จริง
│   ├── file_organizer.py       # จัดการ Path และสร้างโฟลเดอร์ Result
│   └── download_manager.py     # Orchestrator หลัก (รัน Thread, resolve ตัวแปร, จัดการ error)
└── utils/
    └── logger.py               # สร้างไฟล์ Report_log เมื่อมีไฟล์ที่โหลดไม่สำเร็จ
```

---

## การติดตั้ง

### ความต้องการของระบบ

| รายการ | ข้อกำหนด |
|---|---|
| Python | **3.7 ขึ้นไป** |
| GUI | ต้องการ Tkinter (มาพร้อม Python บน Windows) |
| เครือข่าย | Internet access สำหรับ Azure / Huawei OBS (ไม่จำเป็นใน Simulation Mode) |

**Tkinter ตามแต่ละ OS:**
- **Windows** — Tkinter ติดมากับ Python โดยอัตโนมัติ ไม่ต้องติดตั้งเพิ่ม
- **Linux (Debian/Ubuntu)** — `sudo apt install python3-tk`
- **Linux (Fedora/RHEL)** — `sudo dnf install python3-tkinter`
- **macOS** — ปกติติดมากับ Python หากเปิดไม่ได้ให้รัน `brew install python-tk`

### ติดตั้ง Dependencies

```bash
pip install -r requirements.txt
```

| Package | เวอร์ชันขั้นต่ำ | ใช้สำหรับ | จำเป็นเมื่อ |
|---|---|---|---|
| `azure-storage-blob` | 12.19.0 | เชื่อมต่อ Azure Blob Storage | ใช้ Azure mode |
| `esdk-obs-python` | 3.22.0 | เชื่อมต่อ Huawei OBS | ใช้ Huawei OBS mode |
| `plyer` | 2.1.0 | Desktop Notification เมื่อโหลดเสร็จ | Optional — หากไม่มีจะแสดงเป็น messagebox แทน |

> **หมายเหตุ:** หากยังไม่มี credentials ของ Cloud จริง ให้เปิด **Simulation Mode** เพื่อทดสอบ UI และ Flow ก่อนได้เลย

---

## วิธีรัน

```bash
python main.py
```

---

## ข้อมูลที่ต้องเตรียม (Credentials & Configuration)

โปรแกรม**ไม่บันทึก credentials** ไว้ในไฟล์ใดๆ — ต้องกรอกทุกครั้งที่เปิดโปรแกรม

### Azure Blob Storage

**Mode 1 — Connection String**
```
DefaultEndpointsProtocol=https;AccountName=<ชื่อบัญชี>;AccountKey=<คีย์>;EndpointSuffix=core.windows.net
```
หาได้จาก: Azure Portal → Storage Account → **Access Keys** → Connection string

**Mode 2 — Account Name + Account Key**
| Field | รายละเอียด | ตัวอย่าง |
|---|---|---|
| Account Name | ชื่อ Storage Account | `mystorageaccount` |
| Account Key | Base64-encoded key | `dGhpcyBpcyBhIHRlc3Q=...` |

หาได้จาก: Azure Portal → Storage Account → **Access Keys**

---

### Huawei OBS

| Field | รายละเอียด | ตัวอย่าง |
|---|---|---|
| Access Key (AK) | รหัสประจำตัว | `AKIAIOSFODNN7EXAMPLE` |
| Secret Key (SK) | Secret ที่ใช้คู่กับ AK | `wJalrXUtnFEMI/K7MDENG/...` |
| Endpoint | URL ของ OBS Region | `obs.ap-southeast-1.myhuaweicloud.com` |

หาได้จาก: Huawei Cloud Console → **My Credentials** → Access Keys
> Endpoint format อาจต่างกันตาม Region — ตรวจสอบได้จาก Huawei Cloud Console > OBS > Bucket ที่ต้องการ

---

### ข้อมูลต่อ Download Task

| Field | รายละเอียด | หมายเหตุ |
|---|---|---|
| Bucket / Container | ชื่อ Container (Azure) หรือ Bucket (OBS) | จำเป็น |
| Cloud Path / Prefix | Path ภายใน Bucket | เว้นว่าง = root ของ Container |
| Filename Pattern | ชื่อไฟล์หรือ pattern | เว้นว่าง = โหลดทุกไฟล์ใน Path |

---

## อธิบายแต่ละ Feature

### 1. Cloud & Credentials
เลือก Cloud Provider ที่ต้องการใช้งาน:
- **Azure Blob Storage**: ระบุ Connection String *หรือ* Account Name + Account Key
- **Huawei OBS**: ระบุ Access Key (AK), Secret Key (SK), และ Endpoint URL

### 2. Variables (ตัวแปร)
กำหนดตัวแปรชื่อ-ค่า เพื่อใช้แทนใน Filename Pattern

ตัวอย่าง:
```
Name: date    Value: 20240101
```
จากนั้นใช้ `{date}` ใน Filename Pattern ของ Task ได้เลย

### 3. Download Tasks
แต่ละ Task ประกอบด้วย:
| Field | ความหมาย | ตัวอย่าง |
|---|---|---|
| Bucket / Container | ชื่อ Container หรือ OBS Bucket | `my-storage` |
| Cloud Path / Prefix | Path ภายใน Bucket | `data/reports/2024/` |
| Filename Pattern | ชื่อไฟล์หรือ Pattern | `report_{date}.csv` |

**Filename Pattern รองรับ:**
- ชื่อไฟล์ตรงๆ → `report.csv`  (โหลดไฟล์นั้นอย่างเดียว)
- Wildcard `*` → `data_*.csv`  (โหลดทุกไฟล์ที่ match)
- Variable → `report_{date}.csv`  (แทนค่าตัวแปรก่อน)
- ผสม → `*_{date}.parquet`
- เว้นว่าง → โหลดทุกไฟล์ใน Path

สามารถกด **+ Add Task** เพื่อเพิ่ม Task หลายๆ อัน รันใน 1 ครั้ง

### 4. โครงสร้างไฟล์ที่บันทึก

```
Result/
└── DDMMYYYY/              ← วันที่รัน (ค.ศ.) เช่น 06052026
    ├── data/reports/2024/ ← สร้างตาม Cloud Path ของแต่ละ Task
    │   ├── report_20240101.csv
    │   └── report_20240102.csv
    ├── logs/archive/
    │   └── log_20240101.txt
    └── Report_log_20260506_120000.txt   ← มีเฉพาะเมื่อมีไฟล์ที่โหลดไม่สำเร็จ
```

### 5. การจัดการ Error (Skip & Log)
- หากโหลดไฟล์ใดไม่สำเร็จ → ข้ามไป (Skip) และทำไฟล์อื่นต่อ
- สร้าง `Report_log_<timestamp>.txt` บันทึกทุกไฟล์ที่ล้มเหลว พร้อมสาเหตุ
- ตัวอย่างเนื้อหาใน Report log:
  ```
  [1] report_missing.csv
      Bucket    : my-container
      Path      : data/reports/
      Reason    : No files matched pattern
      Timestamp : 2026-05-06 12:00:01
  ```

### 6. Popup Notification เมื่อรันเสร็จ
- แสดง Desktop Notification (ผ่าน `plyer`)
- แสดง Popup Dialog สรุปผล: จำนวนไฟล์ที่โหลดสำเร็จ / ล้มเหลว / Path ที่มีปัญหา

### 7. Simulation Mode
เปิด **Simulation Mode** (checkbox มุมขวาบน Header) เพื่อ:
- ทดสอบ UI และ Flow ทั้งหมดโดยไม่ต้อง connect Cloud จริง
- สร้างไฟล์จำลองใน Output Directory แทนการโหลดจริง
- เหมาะสำหรับทดสอบ Path และ Variable ก่อน Go-Live

---

## Flow การทำงาน

```
User กรอก Input
       ↓
กด [Run Download]
       ↓
Download Manager เริ่ม Thread
       ↓
  ┌── สำหรับแต่ละ Task ──┐
  │  Resolve Variables    │
  │  List files in Path   │
  │  Filter by Pattern    │
  │  Download each file   │
  │  Save to Result/Date/Path/
  │  Log failures         │
  └───────────────────────┘
       ↓
สร้าง Report_log (ถ้ามี error)
       ↓
แสดง Popup Notification
```

---

## ข้อจำกัดที่ทราบ (Known Limitations)

| ข้อจำกัด | รายละเอียด |
|---|---|
| Huawei OBS file listing | list ได้สูงสุด **1,000 ไฟล์ต่อ path** — ไฟล์ที่เกินจะไม่ถูกโหลด |
| Simulation Mode | มีเพียง 7 mock files เท่านั้น (ใช้ทดสอบ UI/Flow เท่านั้น) |
| Save/Load Config | ยังไม่มีระบบบันทึกค่า — ต้องกรอก credentials และ tasks ใหม่ทุกครั้ง |
| Platform | UI ออกแบบสำหรับ Windows (Segoe UI font, mouse scroll) — บน macOS/Linux รูปลักษณ์อาจต่างออกไปเล็กน้อย |
