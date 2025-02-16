import os
import sys
import unittest
import datetime
import numpy

import unittest

print(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../src"))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../src"))
from CalcTool.sdk.tdx_data_agent import TdxDataAgent
from CalcTool.sdk.logger import Logger
from CalcTool.sdk.data_online import TdxOnlineHqAgent
from pytdx.hq import TdxHq_API 


class TestAdjFun(unittest.TestCase):
    def test_adj_online1311(self):        
        self.assertEqual(1, 1)

        agent = TdxDataAgent()
        cur_tick = "001311"
        code = str(int(cur_tick)).zfill(6)
        df_kdata = None
        self._kdata_src = 0
        date_t0 = datetime.date(year=2024, month=6, day=3)
        date_t2 = datetime.date(year=2024, month=6, day=5)
        date_tn = datetime.date(year=2024, month=6, day=23)
        t0_date_f1 = f"{date_t0.strftime("%Y-%m-%d")}"  
        t2_date_f1 = f"{date_t2.strftime("%Y-%m-%d")}"  
        tn_date_f1 = f"{date_tn.strftime("%Y-%m-%d")}"  

        t0_date_f2 = f"{date_t0.strftime("%Y%m%d")}"  
        t2_date_f2 = f"{date_t2.strftime("%Y%m%d")}"  
        tn_date_f2 = f"{date_tn.strftime("%Y%m%d")}"  
        Logger.log().info(f"{t2_date_f1} {tn_date_f1} {t2_date_f2} {tn_date_f2}")

        Logger.log().info(f"self._kdata_src = {self._kdata_src}")
        
        if self._kdata_src == 0:
            df_kdata = agent.read_online_kdata(code, t0_date_f1, tn_date_f1)
        else:
            df_kdata = agent.read_kdata_cache(code, t0_date_f2, tn_date_f2)

        t0_price_origin = agent.get_price_by_date(df_kdata, int(t0_date_f2))
        self.assertEqual(37.49, t0_price_origin)

        xdxr = TdxOnlineHqAgent().get_xdxr_info(str(cur_tick))

        # 前复权
        preadj_df = df_kdata.copy()
        agent.pre_adj(preadj_df, xdxr, int(t0_date_f2), int(tn_date_f2))

        # 后复权
        postadj_df = df_kdata.copy()
        agent.post_adj(postadj_df, xdxr, int(t0_date_f2), int(tn_date_f2))

        # Logger.log().info(f"str(cur_tick) = {str(cur_tick)} df_kdata = {df_kdata}") 
        self.assertEqual(False, df_kdata.empty)
        xdxr = TdxOnlineHqAgent().get_xdxr_info(str(cur_tick))
        self.assertEqual(False, xdxr is None)
        self.assertGreaterEqual(len(xdxr), 1)
        origin = agent.get_extreme_value(df_kdata, int(t2_date_f2), int(tn_date_f2))
        pre = agent.get_extreme_value(preadj_df, int(t2_date_f2), int(tn_date_f2))
        post = agent.get_extreme_value(postadj_df, int(t2_date_f2), int(tn_date_f2))

        # Logger.log().info(f"{origin}, {pre}, {post}")
        self.assertEqual(37.8, origin[0])
        self.assertEqual(20240605, origin[1])
        self.assertEqual(24.94, origin[2])
        self.assertEqual(20240621, origin[3])

        self.assertGreaterEqual(1e-2, abs(28.45 - pre[0]))
        self.assertEqual(20240605, pre[1])
        self.assertGreaterEqual(1e-2, abs(24.94 - pre[2]))
        self.assertEqual(20240621, pre[3])

        self.assertGreaterEqual(1e-2, abs(37.8 - post[0]))
        self.assertEqual(20240605, post[1])
        self.assertGreaterEqual(1e-2, abs(33.24 - post[2]))
        self.assertEqual(20240621, post[3])

    def test_adj_cache1311(self):
        agent = TdxDataAgent()
        cur_tick = "001311"
        code = str(int(cur_tick)).zfill(6)
        df_kdata = None
        self._kdata_src = 1
        date_t0 = datetime.date(year=2024, month=6, day=3)
        date_t2 = datetime.date(year=2024, month=6, day=5)
        date_tn = datetime.date(year=2024, month=6, day=23)
        t0_date_f1 = f"{date_t0.strftime("%Y-%m-%d")}"  
        t2_date_f1 = f"{date_t2.strftime("%Y-%m-%d")}"  
        tn_date_f1 = f"{date_tn.strftime("%Y-%m-%d")}"  

        t0_date_f2 = f"{date_t0.strftime("%Y%m%d")}"  
        t2_date_f2 = f"{date_t2.strftime("%Y%m%d")}"  
        tn_date_f2 = f"{date_tn.strftime("%Y%m%d")}"  
        Logger.log().info(f"{t2_date_f1} {tn_date_f1} {t2_date_f2} {tn_date_f2}")

        Logger.log().info(f"self._kdata_src = {self._kdata_src}")
        
        if self._kdata_src == 0:
            df_kdata = agent.read_online_kdata(code, t0_date_f1, tn_date_f1)
        else:
            df_kdata = agent.read_kdata_cache(code, t0_date_f2, tn_date_f2)

        t0_price_origin = agent.get_price_by_date(df_kdata, int(t0_date_f2))
        self.assertEqual(37.49, t0_price_origin)

        xdxr = TdxOnlineHqAgent().get_xdxr_info(str(cur_tick))

        # 前复权
        preadj_df = df_kdata.copy()
        agent.pre_adj(preadj_df, xdxr, int(t0_date_f2), int(tn_date_f2))

        # 后复权
        postadj_df = df_kdata.copy()
        agent.post_adj(postadj_df, xdxr, int(t0_date_f2), int(tn_date_f2))

        # Logger.log().info(f"str(cur_tick) = {str(cur_tick)} df_kdata = {df_kdata}") 
        self.assertEqual(False, df_kdata.empty)
        xdxr = TdxOnlineHqAgent().get_xdxr_info(str(cur_tick))
        self.assertEqual(False, xdxr is None)
        self.assertGreaterEqual(len(xdxr), 1)
        origin = agent.get_extreme_value(df_kdata, int(t2_date_f2), int(tn_date_f2))
        pre = agent.get_extreme_value(preadj_df, int(t2_date_f2), int(tn_date_f2))
        post = agent.get_extreme_value(postadj_df, int(t2_date_f2), int(tn_date_f2))

        # Logger.log().info(f"{origin}, {pre}, {post}")
        self.assertEqual(37.8, origin[0])
        self.assertEqual(20240605, origin[1])
        self.assertEqual(24.94, origin[2])
        self.assertEqual(20240621, origin[3])

        self.assertGreaterEqual(1e-2, abs(28.45 - pre[0]))
        self.assertEqual(20240605, pre[1])
        self.assertGreaterEqual(1e-2, abs(24.94 - pre[2]))
        self.assertEqual(20240621, pre[3])

        self.assertGreaterEqual(1e-2, abs(37.8 - post[0]))
        self.assertEqual(20240605, post[1])
        self.assertGreaterEqual(1e-2, abs(33.24 - post[2]))
        self.assertEqual(20240621, post[3])


    def test_add1(self):
        # tdx = TdxOnlineHqAgent()
        # # print(tdx.get_xdxr_info("000001"))
        # self.assertGreaterEqual(len(tdx.get_xdxr_info("000001")), 10)
        # # print(tdx.get_xdxr_info("601816"))
        # self.assertGreaterEqual(len(tdx.get_xdxr_info("601816")), 10)
        self.assertEqual(1, 1)


if __name__ == '__main__':
    unittest.main()
    get_finance_info



        