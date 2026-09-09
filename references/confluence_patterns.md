# Confluence PRD Patterns & Macro Reference Guide

Dokumen referensi ini merinci pemetaan tag XML Confluence Storage Format, elemen HTML Confluence View/Export, dan pola dokumen PRD (*Product Requirement Document*) ke Markdown standar.

---

## 1. Confluence Storage Format (XHTML) Mapping

| Confluence Storage Tag | Arti & Fungsi | Format Markdown Target |
| :--- | :--- | :--- |
| `<ac:structured-macro ac:name="jira">` | Macro Jira Issue link + status | `• [KEY](https://jira.../browse/KEY) - Summary `Status`` |
| `<ac:structured-macro ac:name="status">` | Status Lozenge badge | `` `STATUS` `` |
| `<ac:structured-macro ac:name="info">` | Info Callout Panel | `> [!NOTE]`<br>`> Isi catatan...` |
| `<ac:structured-macro ac:name="warning">` | Warning Alert Panel | `> [!WARNING]`<br>`> Peringatan...` |
| `<ac:structured-macro ac:name="tip">` | Tip/Success Panel | `> [!TIP]`<br>`> Saran/Tip...` |
| `<ac:structured-macro ac:name="note">` | Caution/Note Panel | `> [!CAUTION]`<br>`> Catatan khusus...` |
| `<ac:structured-macro ac:name="code">` | Code snippet dengan syntax brush | ```` ```lang ````<br>code block<br>```` ``` ```` |
| `<ac:structured-macro ac:name="expand">` | Collapsible section | `<details><summary>Title</summary>\n\nContent\n\n</details>` |
| `<ac:structured-macro ac:name="widget">` / `iframe` | Embed Figma / Miro | `[Figma Design](url)` atau `[Miro Board](url)` |
| `<ac:image><ri:attachment ri:filename="..."/></ac:image>` | Gambar lampiran lokal | `![filename](assets/filename)` |
| `<ac:link><ri:page ri:content-title="..."/></ac:link>` | Tautan antar halaman Confluence | `[Page Title](#anchor)` |
| `<ac:task-list><ac:task>...</ac:task></ac:task-list>` | Daftar centang (Checklist) | `- [x] Selesai`<br>`- [ ] Belum selesai` |

---

## 2. Pola Penanganan Tabel Bersarang (Nested Tables)

Pada PRD Confluence, cell tabel sering kali memuat sub-tabel (misal pada *User Story Acceptance Criteria* atau *Master Config*):

### Masalah pada Markdown Biasa:
Markdown standar memisahkan baris dengan tanda pipe `|` dan baris baru `\n`. Jika di dalam satu cell terdapat karakter `|` atau `\n`, tabel luar akan rusak (*broken tables*).

### Solusi Confluence PRD Converter:
Sub-tabel dikonversi menjadi tag HTML `<table>` mini yang valid dan dirapatkan (*compacted*) dalam satu baris:

```markdown
| No | Feature | Details & Config | Status |
| --- | --- | --- | --- |
| 1 | User Authentication | <table><thead><tr><th>Param</th><th>Type</th><th>Req</th></tr></thead><tbody><tr><td>email</td><td>string</td><td>true</td></tr><tr><td>password</td><td>string</td><td>true</td></tr></tbody></table> | `ACTIVE` |
```

---

## 3. Pola Ekstraksi Embed Figma & Miro

Confluence macro sering kali membungkus Figma atau Miro dalam URL embed yang panjang atau ter-encode:
- **Figma**: `https://www.figma.com/embed?embed_host=confluence&url=https%3A%2F%2Fwww.figma.com%2Ffile%2FAbCdEf%2FDesign-System%3Fnode-id%3D0%3A1`
  - *Dikonversi menjadi*: `[Figma Design](https://www.figma.com/file/AbCdEf/Design-System?node-id=0%3A1)`
- **Miro**: `https://miro.com/app/live-embed/uXjVO12345=/?moveToViewport=-100...`
  - *Dikonversi menjadi*: `[Miro Board](https://miro.com/app/board/uXjVO12345=/)`

---

## 4. Pola Struktur Dokumen PRD Standar

Struktur PRD ideal yang dihasilkan oleh converter:
1. **# [PRD] Judul Dokumen**
2. **Metadata Dokumen** (Author, Versi, Status, Link Jira Epic/Story, Figma/Miro links)
3. **1. Background & Business Objective**
4. **2. User Persona & Scope**
5. **3. User Stories & Acceptance Criteria** (Tabel dengan sub-tabel & Jira lozenge)
6. **4. UI/UX Flow & Wireframes** (Link Figma + Mockup images)
7. **5. Technical Specifications & Master Config** (Tabel config & Schema payload)
8. **6. Security & Threat Modeling (ITPF / STRIDE)** (Tabel matriks keamanan)
9. **7. Data Tracking & Analytics Metrics** (Tabel event tagging)
10. **8. Rollout Plan & Dependencies** (Checklist task list & dependency table)
