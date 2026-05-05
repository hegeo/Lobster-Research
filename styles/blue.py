# -*- coding: utf-8 -*-
"""
iOS Liquid Style - inspired by Apple design language.
Clean, fluid, minimal with soft shadows and generous whitespace.

Palette:
  Primary:    #6366F1 (Indigo)
  Secondary:  #8B5CF6 (Violet)
  Background: #F8FAFC (Slate 50)
  Text:       #0F172A (Slate 900)
"""

CSS = """
@page {
  size: A4;
  margin: 15mm 18mm;
  @top-left     { content: none; }
  @top-center   { content: none; }
  @top-right    { content: none; }
  @bottom-left  { content: none; }
  @bottom-center{ content: none; }
  @bottom-right { content: none; }
}

@media print {
  body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  @page { margin: 0; }
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, 'SF Pro Display', 'SF Pro Text', 'PingFang SC',
               'Helvetica Neue', 'Microsoft YaHei', sans-serif;
  font-size: 14px;
  color: #0F172A;
  background: #f8f6ff;
  line-height: 1.65;
  padding: 0;
  margin: 0;
}

.page-frame {
  background: #FFFFFF;
  overflow: hidden;
  margin: 4%;
}

/* ══ 封面 ═══════════════════════════════════════════ */
.cover {
  width: 100%;
  min-height: 280mm;
  background: linear-gradient(160deg, #ffffff 0%, #8B5CF6 50%, #7543e4 100%);
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 20mm 20mm 20mm 20mm;
  page-break-after: always;
}
.cover .cover-inner {
  background: #ffffff;
  padding: 44px 52px;
  border: 1px solid rgba(255, 255, 255, 0.35);
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.10);
}
.cover .cover-label {
  font-size: 12px;
  color: #5c5c5c;
  font-weight: 600;
  letter-spacing: 2.5px;
  text-transform: uppercase;
  margin-bottom: 20px;
}
.cover .cover-title {
  font-size: 30px;
  font-weight: 700;
  color: #000000;
  line-height: 1.25;
  margin-bottom: 14px;
  letter-spacing: -0.5px;
}
.cover .cover-subtitle {
  font-size: 14px;
  color: #5c5c5c;
  margin-bottom: 32px;
  line-height: 1.55;
}
.cover .cover-meta {
  display: flex;
  gap: 15px;
  font-size: 12px;
  color: #5c5c5c;
}
.cover .cover-lobster {
  font-size: 32px;
  margin-top: 24px;
}

/* ══ 概览表格 ═════════════════════════════════════ */
.overview-table-wrap {
  margin: 15px 20px;
  background: #FFFFFF;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 6px 20px rgba(0,0,0,0.04);
}
.overview-table-wrap h3 {
  font-size: 14px;
  color: #6366F1;
  font-weight: 600;
  margin: 16px 20px 10px;
  letter-spacing: 0.3px;
}
.overview-table-wrap table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
}
.overview-table-wrap th {
  background: #F8FAFC;
  color: #64748B;
  padding: 10px 16px;
  text-align: left;
  font-weight: 600;
  font-size: 11px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  border-bottom: 1px solid #E2E8F0;
}
.overview-table-wrap td {
  padding: 10px 16px;
  border-bottom: 1px solid #F1F5F9;
  vertical-align: top;
  color: #334155;
}
.overview-table-wrap tr:last-child td { border-bottom: none; }
.overview-table-wrap tr:nth-child(even) td { background: #FAFBFE; }

/* ══ 章节 ═════════════════════════════════════════ */
.section {
  margin: 32px 0;
}
.section-title {
  font-size: 18px;
  font-weight: 700;
  color: #0F172A;
  background-color: #f5f2ff;
  padding: 14px 0 14px 16px;
  border-left: 4px solid #6366F1;
  margin-bottom: 4px;
  letter-spacing: -0.3px;
}
.subsection {
  margin: 12px 0;
  background: #FFFFFF;
  padding: 18px 24px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.subsection-title {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 10px;
}
.subsection-content {
  font-size: 13.5px;
  color: #475569;
  line-height: 1.8;
  margin-bottom: 10px;
  text-align: justify;
}

/* ══ 高亮框 ═══════════════════════════════════════ */
.highlight-box {
  background: #EEF2FF;
  padding: 14px 18px;
  margin: 12px 0;
  font-size: 13px;
  color: #3730A3;
  line-height: 1.7;
}
.highlight-box::before {
  content: "";
  display: none;
}

/* ══ 数据表格 ═════════════════════════════════════ */
.data-table-wrap {
  margin: 14px 0;
  overflow-x: auto;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.data-table-wrap table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
}
.data-table-wrap th {
  background: #F8FAFC;
  color: #64748B;
  padding: 9px 14px;
  text-align: left;
  font-weight: 600;
  font-size: 11px;
  letter-spacing: 0.3px;
  border-bottom: 1px solid #E2E8F0;
}
.data-table-wrap td {
  padding: 8px 14px;
  border-bottom: 1px solid #F1F5F9;
  min-width: 100px;
  color: #334155;
}
.data-table-wrap tr:nth-child(even) td { background: #FAFBFE; }
.data-table-wrap tr:last-child td { border-bottom: none; }

/* ══ 摘要 ═════════════════════════════════════════ */
.summary-box {
  background: linear-gradient(135deg, #FFFFFF 0%, #E0E7FF 100%);
  padding: 22px 26px;
  margin: 32px 0;
}
.summary-box .summary-label {
  font-size: 12px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #6366F1;
  margin-bottom: 12px;
  font-weight: 600;
}
.summary-box .summary-text {
  font-size: 13.5px;
  line-height: 1.8;
  color: #1E293B;
}

/* ══ 龙虾寄语 ═════════════════════════════════════ */
.quote-box {
  background: linear-gradient(135deg, #FFFFFF 0%, #8B5CF6 100%);
  color: white;
  padding: 20px 28px;
  margin: 24px 0;
  text-align: center;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.3px;
}

/* ══ 免责声明 ═════════════════════════════════════ */
.disclaimer {
  font-size: 10.5px;
  color: #94A3B8;
  border-top: 1px solid #F1F5F9;
  padding-top: 14px;
  margin-top: 32px;
  line-height: 1.6;
}

/* ══ 指标卡 ═══════════════════════════════════════ */
.metrics-bar {
  display: flex;
  gap: 14px;
  margin: 30px 20px 20px 20px;
  flex-wrap: wrap;
}
.metric-card {
  background: #FFFFFF;
  padding: 14px 18px;
  text-align: center;
  min-width: 100px;
  flex: 1;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03);
}
.metric-card .metric-label {
  font-size: 10px;
  color: #94A3B8;
  letter-spacing: 1px;
  font-weight: 500;
}
.metric-card .metric-value {
  font-size: 22px;
  font-weight: 700;
  color: #6366F1;
  margin: 6px 0;
  letter-spacing: -0.5px;
}
.metric-card .metric-change {
  font-size: 11px;
  color: #64748B;
}

/* ══ 分页控制 ═════════════════════════════════════ */
.page-break { page-break-before: always; }
"""
