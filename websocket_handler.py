import logging
from urllib.parse import urlparse


import tornado.websocket
import tornado.ioloop
import tornado.web
from tornado.options import define, options


logger = logging.getLogger(__name__)


class CommunicationHandler(tornado.websocket.WebSocketHandler):
    """
    Handler class for websocket communication.
    """
    def initialize(self, on_message_callback, authentication_handler=None, domains=None):
        """
        Performs handler initialization. Params will be given when instantiating handler during urls defining.

        :param authentication_handler: should be callable which gets cookie as a parameter and
        returns user object or None respectively to success/failure.

        :param domains: array if allowed domains (origins)

        :param on_message_callback: function which takes message as parameter
        """
        logger.info("Initializing %s" % self.__class__.__name__)
        self._on_message_callback = on_message_callback
        self._authentication_handler = authentication_handler
        self._domains = domains if domains else ['localhost']

    def open(self, *args, **kwargs):
        """
        Called when client (e.g. js client) initiate connection.
        """
        self._user = None
        logger.info("Opening new connection")
        if self._authentication_handler:
            user = self._authentication_handler.authenticate(self.cookies)
            if not user:
                logger.error("Authentication failed")
                self.close()
                return
            self._user = user
        logger.info("Connection estabilished for user: " % self._user)

    def check_origin(self, origin):
        domain = urlparse(origin).hostname
        logger.error("Domain %s not allowed" % domain)
        return domain in self._domains

    def on_message(self, message):
        """
        Called when handler receives new messsage from client.
        """

        self._on_message_callback(message)

    def on_close(self):
        """
        Called when client disconnects from socket.
        """
        logger.log("Connection for user: %s closed" % self._user)


app = tornado.web.Application([
    (r"/handler", CommunicationHandler, dict(on_message_handler_dict=lambda f:f)),
])


define('port', default='8000', help='Tcp port')
define('host', default='127.0.0.1', help='Ip address of host')


def run():
    """
    Method for managing starting server and setting necessary configuration options.
    """
    tornado.options.parse_command_line()
    app.listen(options.port, address=options.host)
    tornado.ioloop.IOLoop.instance().start()

if __name__=='__main__':
    run()