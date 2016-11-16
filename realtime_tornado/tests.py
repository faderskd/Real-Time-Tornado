import os
import time
import unittest
import multiprocessing

import websocket

from . import websocket_handler


class WebsocketHandlerNoAuthenticationTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ['REDIS_HOST'] = 'localhost'
        os.environ['REDIS_PORT'] = '6379'
        os.environ['REDIS_DB'] = '0'

        cls.server_process = multiprocessing.Process(target=websocket_handler.run)
        cls.server_process.start()

        # wait for server to start
        time.sleep(0.01)

    @classmethod
    def tearDownClass(cls):
        cls.server_process.terminate()

    def test_open_connection(self):
        ws = websocket.create_connection('ws://localhost:8888/handler/1')
        self.assertTrue(ws.connected)
        ws.close()

    def test_subscribe(self):
        ws1 = websocket.create_connection('ws://localhost:8888/handler/1')
        ws2 = websocket.create_connection('ws://localhost:8888/handler/1')
        ws1.send('test msg from ws1')
        ws2.send('test msg from ws2')
        self.assertEqual(ws1.recv(), 'test msg from ws2')
        self.assertEqual(ws2.recv(), 'test msg from ws1')


if __name__ == '__main__':
    unittest.main()