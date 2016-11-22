import os
import json
import datetime
import logging
from urllib.parse import urlparse

import redis
import tornado.gen
import tornado.web
import tornado.ioloop
import tornado.websocket
from tornado.options import define, options

logger = logging.getLogger(__name__)


class WebsocketCommunicationHandler(tornado.websocket.WebSocketHandler):
    """
    Handler class for websocket communication.
    """
    def initialize(self, authentication_handler=None, domains=None, additional_subscribe_handler=None):
        """
        Performs handler initialization. Params will be given when instantiating handler during urls defining.

        :param authentication_handler: should be coroutine which gets cookie as a parameter and
        returns username or None respectively to success/failure.

        :param domains: array of allowed domains (origins)

        :param additional_subscribe_handler: function that takes message as parameter to perform additional operations
        when it appears on channel
        """
        logger.info("Initializing %s" % self.__class__.__name__)
        self._authentication_handler = authentication_handler
        self._domains = domains if domains else ['localhost']
        self._additional_subscribe_handler = additional_subscribe_handler

        self._redis_connection = self._get_redis_connection()
        self._pubsub = self._redis_connection.pubsub(ignore_subscribe_messages=True)
        self._user = None
        self._subscribe = False

    def _get_redis_connection(self):
        host = os.getenv('REDIS_HOST', 'localhost')
        port = int(os.getenv('REDIS_PORT', '6379'))
        db = int(os.getenv('REDIS_DB', '0'))
        return redis.StrictRedis(host, port, db)

    @tornado.gen.coroutine
    def open(self, channel):
        """
        Called when client initiate connection. Performs authentication if any authentication handler is
        given during initialization.

        :param channel: redis subscription channel given in ws url
        """
        self._channel = channel

        logger.info("Opening new connection")
        if self._authentication_handler:
            user = yield self._authentication_handler(self.cookies)
            if not user:
                logger.error("Authentication failed")
                self.close()
                self.on_close()
                return
            self._user = user

        msg = "Connection estabilished"
        if self._user:
            msg = "Connection estabilished for user: %s" % self._user
        logger.info(msg)

        tornado.ioloop.IOLoop.current().spawn_callback(self.listen)

    @tornado.gen.coroutine
    def listen(self):
        """
        Coroutine for listening on new messages from redis. Whenever message is received, it calls subscribe handler.
        """
        self._pubsub.subscribe(self._channel)
        self._subscribe = True
        while self._subscribe:
            redis_message = self._pubsub.get_message()
            if redis_message:
                json_msg = redis_message['data'].decode()
                data = json.loads(json_msg)
                if id(self) != data['id']:
                    self.subscribe_handler(data['message'])
            yield tornado.gen.Task(
                tornado.ioloop.IOLoop.current().add_timeout,
                datetime.timedelta(milliseconds=100)
            )

    def subscribe_handler(self, message):
        """
        Called when new message is going from redis (somebody write new message on socket).

        :param redis_message: Redis message object
        """
        self.write_message(message)
        if self._additional_subscribe_handler:
            self._additional_subscribe_handler(message)

    def on_message(self, message):
        """
        Called when handler receives new message from client.

        :param message: String representing message to be published by redis
        """
        json_msg = json.dumps({'id': id(self), 'message': message})
        self._redis_connection.publish(self._channel, json_msg)

    def on_close(self):
        """
        Called when client disconnects from socket.
        """
        self._subscribe = False
        self._pubsub.unsubscribe()
        self._pubsub.close()
        msg = "Connection closed"
        if self._user:
            msg = "Connection for user: %s closed" % self._user
        logger.info(msg)

    def check_origin(self, origin):
        """
        Checks if request was made from known domains.

        :param origin: Url of server from which request ws request was made
        """
        domain = urlparse(origin).hostname
        domain_allowed = domain in self._domains
        if not domain_allowed:
            logger.error("Domain %s not allowed" % domain)
        return domain_allowed


define('port', default='8888', help='Tcp port')
define('host', default='127.0.0.1', help='Ip address of host')


def run(authentication_handler=None, allowed_domains=None, additional_subscribe_handler=None,
        additional_routes=None):
    """
    Function for managing starting server and setting necessary configuration options.

    :param authentication_handler: should be coroutine which gets cookie as a parameter and
    returns username or None respectively to success/failure

    :param domains: array of allowed domains (origins)

    :param additional_subscribe_handler: function that takes message as parameter to peform additional operations
    when it appears on channel

    :param additional_routes: array of user's custom Tornado routes
    """
    if not additional_routes:
        additional_routes = []

    app = tornado.web.Application([
        (r"/handler/([0-9]+)", WebsocketCommunicationHandler, dict(authentication_handler=authentication_handler,
                                                          domains=allowed_domains,
                                                          additional_subscribe_handler=additional_subscribe_handler)),
    ] + additional_routes)

    tornado.options.parse_command_line()
    app.listen(options.port, address=options.host)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    run()
