import os
import time
import unittest
import multiprocessing

import websocket
import tornado.gen

from realtime_tornado import websocket_handler

os.environ['REDIS_HOST'] = 'localhost'
os.environ['REDIS_PORT'] = '6379'
os.environ['REDIS_DB'] = '0'


class WebsocketHandlerNoAuthenticationTest(unittest.TestCase):

    def setUp(self):
        self.server_process = multiprocessing.Process(target=websocket_handler.run)
        self.server_process.start()

        # wait for server to start
        time.sleep(0.01)

        self.ws1 = websocket.create_connection('ws://localhost:8888/handler/1')
        self.ws2 = websocket.create_connection('ws://localhost:8888/handler/1')

    def tearDown(self):
        self.ws1.close()
        self.ws2.close()
        self.server_process.terminate()

    def test_subscribe(self):
        self.ws1.send('test msg from ws1')
        self.ws2.send('test msg from ws2')
        resp1 = self.ws1.recv()
        resp2 = self.ws2.recv()

        self.assertEqual(resp1, 'test msg from ws2')
        self.assertEqual(resp2, 'test msg from ws1')


class WebsocketHandlerWithAuthenticationTest(unittest.TestCase):

    def setUp(self):
        @tornado.gen.coroutine
        def success_authentication_coroutine_handler(cookie):
            return "test user"

        @tornado.gen.coroutine
        def failure_authentication_coroutine_handler(cookie):
            return None

        self.authentication_handler_mock = success_authentication_coroutine_handler
        if self._testMethodName == 'test_subscribe_denied_connection':
            self.authentication_handler_mock = failure_authentication_coroutine_handler

        self.server_process = multiprocessing.Process(target=websocket_handler.run, args=(self.authentication_handler_mock,))
        self.server_process.start()

        # wait for server to start
        time.sleep(0.01)

        self.ws1 = websocket.create_connection('ws://localhost:8888/handler/1')
        self.ws2 = websocket.create_connection('ws://localhost:8888/handler/1')

    def tearDown(self):
        self.ws1.close()
        self.ws2.close()
        self.server_process.terminate()

    def test_subscribe_allowed_connection(self):
        self.ws1.send('test msg from ws1')
        self.ws2.send('test msg from ws2')
        resp1 = self.ws1.recv()
        resp2 = self.ws2.recv()

        self.assertEqual(resp1, 'test msg from ws2')
        self.assertEqual(resp2, 'test msg from ws1')

    def test_subscribe_denied_connection(self):
        self.ws1.send('test msg from ws1')
        self.ws2.send('test msg from ws2')
        resp1 = self.ws1.recv()
        resp2 = self.ws2.recv()
        self.assertEqual(resp1, '')
        self.assertEqual(resp2, '')


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite1 = loader.loadTestsFromTestCase(WebsocketHandlerNoAuthenticationTest)
    suite2 = loader.loadTestsFromTestCase(WebsocketHandlerWithAuthenticationTest)
    suite = unittest.TestSuite([suite1, suite2])
    runner = unittest.TextTestRunner()
    runner.run(suite)
