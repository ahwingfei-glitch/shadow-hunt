#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""法证报告生成器 - 生成 PDF 格式的案件检测报告"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors


@dataclass
class DetectionResult:
    """检测结果"""
    label: str          # 行为标签
    confidence: float   # 置信度
    timestamp: str      # 时间戳
    evidence: Optional[str] = None  # 证据截图路径


@dataclass
class CaseInfo:
    """案件信息"""
    case_id: str        # 案件编号
    location: str       # 地点
    start_time: str     # 开始时间
    end_time: str       # 结束时间
    description: str    # 案件描述


class ForensicReportGenerator:
    """法证报告生成器"""

    def __init__(self, font_path: str = None):
        """初始化并注册中文字体"""
        self.font_name = "SimHei"
        font = font_path or "C:/Windows/Fonts/simhei.ttf"
        if Path(font).exists():
            pdfmetrics.registerFont(TTFont(self.font_name, font))
        self._setup_styles()

    def _setup_styles(self):
        """配置样式"""
        self.styles = getSampleStyleSheet()
        self.styles.add(ParagraphStyle(
            name='ChineseTitle', fontName=self.font_name, fontSize=18,
            alignment=1, spaceAfter=20
        ))
        self.styles.add(ParagraphStyle(
            name='Chinese', fontName=self.font_name, fontSize=10, leading=14
        ))

    def generate(self, case: CaseInfo, results: List[DetectionResult],
                 output_path: str) -> str:
        """生成 PDF 报告"""
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                                leftMargin=2*cm, rightMargin=2*cm)
        story = []

        # 标题
        story.append(Paragraph("法证分析报告", self.styles['ChineseTitle']))
        story.append(Spacer(1, 0.5*cm))

        # 案件信息表
        case_data = [
            ["案件编号", case.case_id, "地点", case.location],
            ["开始时间", case.start_time, "结束时间", case.end_time],
            ["案件描述", case.description, "", ""]
        ]
        story.append(self._create_table(case_data, [3*cm, 5*cm, 3*cm, 5*cm]))
        story.append(Spacer(1, 0.8*cm))

        # 检测结果
        story.append(Paragraph("检测结果", self.styles['Chinese']))
        story.append(Spacer(1, 0.3*cm))

        result_rows = [["序号", "行为标签", "置信度", "时间戳"]]
        for i, r in enumerate(results, 1):
            result_rows.append([str(i), r.label, f"{r.confidence:.2%}", r.timestamp])
        story.append(self._create_table(result_rows, [1.5*cm, 6*cm, 3*cm, 5*cm]))

        # 页脚
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph(
            f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            self.styles['Chinese']
        ))

        doc.build(story)
        return output_path

    def _create_table(self, data, col_widths) -> Table:
        """创建表格"""
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        return table


def create_report_generator(font_path: str = None) -> ForensicReportGenerator:
    """工厂函数"""
    return ForensicReportGenerator(font_path)