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
        # agent = TdxDataAgent()
        # agent1 = TdxOnlineHqAgent()
        # agent2 = TdxOnlineHqAgent()

        # api = TdxHq_API(heartbeat=True, auto_retry=True)
        # with api.connect('121.36.81.195', 7709):
        #     print(api.get_k_data('601398','2024-12-31','2025-01-18'))
        
        self.assertEqual(1, 1)

        agent = TdxDataAgent()
        cur_tick = "001311"
        code = str(int(cur_tick)).zfill(6)
        df_kdata = None
        self._kdata_src = 0
        t2_datetime = datetime.date(year=2024, month=6, day=5)
        target_datetime = datetime.date(year=2024, month=6, day=23)
        t2_date_f1 =  f"{t2_datetime.strftime("%Y-%m-%d")}"  
        target_date_f1 = f"{target_datetime.strftime("%Y-%m-%d")}"  

        t2_date_f2 =  f"{t2_datetime.strftime("%Y%m%d")}"  
        target_date_f2 = f"{target_datetime.strftime("%Y%m%d")}"  
        Logger.log().info(f"{t2_date_f1} {target_date_f1} {t2_date_f2} {target_date_f2}")

        Logger.log().info(f"self._kdata_src = {self._kdata_src}")
        if self._kdata_src == 0:

            df_kdata = agent.read_online_kdata(code, t2_date_f1, target_date_f1)
        else:
            df_kdata = agent.read_kdata(code)

        # Logger.log().info(f"str(cur_tick) = {str(cur_tick)} df_kdata = {df_kdata}") 
        self.assertEqual(False, df_kdata.empty)
        xdxr = TdxOnlineHqAgent().get_xdxr_info(str(cur_tick))
        self.assertEqual(False, xdxr is None)
        self.assertGreaterEqual(len(xdxr), 1)
        origin = agent.get_extreme_between_days(str(cur_tick), df_kdata, int(t2_date_f2), int(target_date_f2), xdxr)
        pre = agent.get_pre_extreme_between_days(str(cur_tick), df_kdata, int(t2_date_f2), int(target_date_f2), xdxr)
        post = agent.get_post_extreme_between_days(str(cur_tick), df_kdata, int(t2_date_f2), int(target_date_f2), xdxr)

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
        # agent = TdxDataAgent()
        # agent1 = TdxOnlineHqAgent()
        # agent2 = TdxOnlineHqAgent()

        # api = TdxHq_API(heartbeat=True, auto_retry=True)
        # with api.connect('121.36.81.195', 7709):
        #     print(api.get_k_data('601398','2024-12-31','2025-01-18'))
        
        self.assertEqual(1, 1)

        agent = TdxDataAgent()
        cur_tick = "001311"
        code = str(int(cur_tick)).zfill(6)
        df_kdata = None
        self._kdata_src = 1
        t2_datetime = datetime.date(year=2024, month=6, day=5)
        target_datetime = datetime.date(year=2024, month=6, day=23)
        t2_date_f1 =  f"{t2_datetime.strftime("%Y-%m-%d")}"  
        target_date_f1 = f"{target_datetime.strftime("%Y-%m-%d")}"  

        t2_date_f2 =  f"{t2_datetime.strftime("%Y%m%d")}"  
        target_date_f2 = f"{target_datetime.strftime("%Y%m%d")}"  
        Logger.log().info(f"{t2_date_f1} {target_date_f1} {t2_date_f2} {target_date_f2}")

        Logger.log().info(f"self._kdata_src = {self._kdata_src}")
        if self._kdata_src == 0:

            df_kdata = agent.read_online_kdata(code, t2_date_f1, target_date_f1)
        else:
            df_kdata = agent.read_kdata(code)

        # Logger.log().info(f"str(cur_tick) = {str(cur_tick)} df_kdata = {df_kdata}") 
        self.assertEqual(False, df_kdata.empty)
        xdxr = TdxOnlineHqAgent().get_xdxr_info(str(cur_tick))
        self.assertEqual(False, xdxr is None)
        self.assertGreaterEqual(len(xdxr), 1)
        origin = agent.get_extreme_between_days(str(cur_tick), df_kdata, int(t2_date_f2), int(target_date_f2), xdxr)
        pre = agent.get_pre_extreme_between_days(str(cur_tick), df_kdata, int(t2_date_f2), int(target_date_f2), xdxr)
        post = agent.get_post_extreme_between_days(str(cur_tick), df_kdata, int(t2_date_f2), int(target_date_f2), xdxr)

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



        