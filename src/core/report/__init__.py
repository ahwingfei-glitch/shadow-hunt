#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""猎影 (Shadow Hunt) - 报告生成模块"""

from .generator import (
    ForensicReportGenerator, CaseInfo, DetectionResult,
    create_report_generator
)

__all__ = [
    'ForensicReportGenerator', 'CaseInfo', 'DetectionResult',
    'create_report_generator'
]