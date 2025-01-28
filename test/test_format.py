#!/usr/bin/python#

#-*-coding:UTF-8-*-

import os
import sys
import unittest
import datetime
import numpy

print(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../src"))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../src"))
from CalcTool.sdk.tool_main import CalcLast1YearCount
from CalcTool.sdk.logger import Logger

import unittest

def add(a, b):
    return a + b

def sub(a, b):
    return a - b

class TestFun(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(1, 2), 3)
        self.assertEqual(add(-1, 1), 0)
        self.assertEqual(add(0, 0), 0)

    def test_sub(self):
        self.assertEqual(sub(3, 4), -1)

class TestDateTime(unittest.TestCase):
    def test_date(self):
        cnt = CalcLast1YearCount()
        date = datetime.datetime(2025, 1, 5, hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        self.assertEqual(cnt._FormatDate2Str(date), "20250105")
        date = date + datetime.timedelta(days=1)
        self.assertEqual(cnt._FormatDate2Str(date), "20250106")
        self.assertEqual(cnt._FormatDate2Str(None), "")
        self.assertEqual(cnt._FormatDate2Str(1), "")
        self.assertEqual(cnt._FormatDate2Str(""), "")
    
    def test_time(self):
        cnt = CalcLast1YearCount()
        date = datetime.datetime(2025, 1, 5, hour=1, minute=2, second=5, microsecond=0, tzinfo=None)
        # self.assertEqual(cnt._FormatTime2Str(date), "2025-01-05 01:02:05")
        date = date + datetime.timedelta(days=1, hours=10)
        # self.assertEqual(cnt._FormatTime2Str(date), "2025-01-06 11:02:05")
        self.assertEqual(cnt._FormatTime2Str(None), "")
        self.assertEqual(cnt._FormatTime2Str(1), "")
        self.assertEqual(cnt._FormatTime2Str(""), "")

    def test_tick(self):
        cnt = CalcLast1YearCount()
        tick = numpy.float64(600326)
        self.assertEqual(cnt._IsTickRight(tick, 111), True)
        tick1 = numpy.float64(1)
        self.assertEqual(cnt._IsTickRight(tick1, 111), True)
        print(f"{cnt.FormatDate(20241231)}")
        self.assertEqual(0, cnt.FormatDate(20241231))
        

if __name__ == '__main__':
    unittest.main()
    