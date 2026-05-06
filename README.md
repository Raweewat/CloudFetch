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

```bash
pip install -r requirements.txt
```

| Package | ใช้สำหรับ |
|---|---|
| `azure-storage-blob` | เชื่อมต่อ Azure Blob Storage |
| `esdk-obs-python` | เชื่อมต่อ Huawei OBS |
| `plyer` | Desktop Notification เมื่อโหลดเสร็จ |

> **หมายเหตุ:** หากยังไม่มี credentials ของ Cloud จริง ให้เปิด **Simulation Mode** เพื่อทดสอบ UI และ Flow ก่อนได้เลย

---

## วิธีรัน

```bash
python main.py
```

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

## ข้อมูลที่ต้องการเพิ่มเติมจากผู้ใช้

ข้อมูลต่อไปนี้จำเป็นสำหรับการพัฒนาต่อ:

| # | ข้อมูล | เหตุผลที่ต้องการ |
|---|---|---|
| 1 | **Authentication Method ของ Azure** ที่ใช้จริง | รองรับทั้ง Connection String, Account Key, SAS Token, และ Managed Identity — ต้องการทราบว่าใช้แบบไหนหลัก |
| 2 | **Huawei OBS Endpoint format** ที่ใช้ | บาง Region ใช้ format ต่างกัน เช่น `obs.ap-southeast-1.myhuaweicloud.com` vs custom endpoint |
| 3 | **ขนาดไฟล์และจำนวนไฟล์โดยประมาณ** | เพื่อ optimize การโหลด (chunk download สำหรับไฟล์ใหญ่, parallel download) |
| 4 | **ต้องการ Parallel Download** หรือไม่ | โหลดหลายไฟล์พร้อมกัน vs ทีละไฟล์ — มีผลต่อ performance และ rate limit ของ Cloud |
| 5 | **Proxy หรือ Network restriction** | บางองค์กรต้องผ่าน Proxy หรือมี firewall — ต้องการ config เพิ่มเติม |
| 6 | **รูปแบบ Variable** เพิ่มเติมนอกจากวันที่ | เช่น ต้องการ variable ที่เป็น range, หรือ variable ที่อ่านจากไฟล์ config |
| 7 | **การ Save / Load Config** | ต้องการ save ค่า Task ที่กรอกไว้เพื่อใช้ซ้ำในครั้งต่อไปหรือไม่ |
| 8 | **OS ที่ใช้งาน** | Windows / macOS / Linux — มีผลต่อ path separator และ notification library |
| 9 | **ต้องการ CLI mode** ด้วยหรือไม่ | รัน headless โดยไม่เปิด GUI เช่น รันผ่าน scheduler หรือ pipeline |
| 10 | **Retry mechanism** เมื่อ network หลุด | ต้องการ retry กี่ครั้ง และ delay เท่าไหร่ระหว่าง retry |
